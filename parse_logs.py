# parse_logs.py
import re
import psycopg
from psycopg import sql
import configparser
import argparse
import logging
import os
import time
import json
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, Set

BATCH_SIZE = 1000 # Will be overridden by config if set

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

LINE_RE = re.compile(
    r"""^
    (?P<date>\d{4}/\d{2}/\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2}\.\d+)\s+
    from\s+
    (?:(?P<src_proto>tcp|udp):)?
    (?P<src_ip>\d{1,3}(?:\.\d{1,3}){3}) : (?P<src_port>\d+)\s+
    (?P<action>accepted)\s+
    (?:(?P<dst_proto>tcp|udp):|(?:\/\/))?
    (?P<dst_host>[\w\.\-]+) : (?P<dst_port>\d+)
    (?:\s+\[(?P<route_raw>[^\]]+)\])? 
    (?:\s+email:\s*(?P<user>\S+))?
    \s*$
    """,
    re.X,
)

LOG_INSERT_SQL = """
    INSERT INTO logs (
        timestamp, source_ip, source_port, action, protocol_id,
        destination_id, destination_port, inbound_tag_id,
        outbound_tag_id, user_id
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def load_config(config_path: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    read_files = config.read(config_path)
    if not read_files:
        logging.error(f"Failed to read config file: {config_path}")
        raise SystemExit(1)
    return config


def get_db_connection(config: configparser.ConfigParser) -> Optional[psycopg.Connection]:
    """Read DB connection settings from config."""
    if "postgresql" not in config:
        logging.error("Config section [postgresql] is missing")
        return None

    try:
        conn_str = " ".join([f"{key}='{value}'" for key, value in config["postgresql"].items()])
        return psycopg.connect(conn_str)
    except psycopg.OperationalError as e:
        logging.error(f"Failed to connect to database: {e}")
        return None


def parse_line(line: str) -> Optional[Dict[str, Optional[str]]]:
    """Parse a single log line and adapt the result for DB or offline storage."""
    m = LINE_RE.match(line.strip())
    if not m:
        if "api -> api" in line:
            parts = line.split()
            return {
                "timestamp": f"{parts[0]} {parts[1]}",
                "source_ip": parts[3].split(":")[0],
                "source_port": parts[3].split(":")[1],
                "dest_protocol": None,
                "dest_host": None,
                "dest_port": None,
                "inbound_tag": "api",
                "outbound_tag": "api",
                "email": None,
            }
        return None

    d = m.groupdict()
    inbound_tag, outbound_tag = None, None
    route_raw = d.get("route_raw")
    if route_raw:
        separator = ">>" if ">>" in route_raw else "->"
        parts = [p.strip() for p in route_raw.split(separator)]
        if len(parts) == 2:
            inbound_tag, outbound_tag = parts

    timestamp_str = f"{d.get('date')} {d.get('time')}" if d.get("date") else None
    dst_proto = d.get("dst_proto") or d.get("src_proto")

    return {
        "timestamp": timestamp_str,
        "source_ip": d.get("src_ip"),
        "source_port": d.get("src_port"),
        "dest_protocol": dst_proto,
        "dest_host": d.get("dst_host"),
        "dest_port": d.get("dst_port"),
        "inbound_tag": inbound_tag,
        "outbound_tag": outbound_tag,
        "email": d.get("user"),
    }


def resolve_id(
    cursor: Any,
    cache: Dict[str, int],
    stats: Dict[str, int],
    table: str,
    column: str,
    value: Optional[str],
) -> Optional[int]:
    """
    Optimized ID resolver.
    Checks cache, then DB. If not found, inserts and caches.
    """
    if not value:
        return None

    if value in cache:
        return cache[value]

    cursor.execute(f"SELECT id FROM {table} WHERE {column} = %s", (value,))
    result = cursor.fetchone()
    if result:
        cache[value] = result[0]
        return result[0]

    cursor.execute(
        f"INSERT INTO {table} ({column}) VALUES (%s) ON CONFLICT ({column}) DO NOTHING RETURNING id",
        (value,),
    )
    result = cursor.fetchone()
    if not result:
        cursor.execute(f"SELECT id FROM {table} WHERE {column} = %s", (value,))
        result = cursor.fetchone()

    new_id = result[0]
    cache[value] = new_id
    stats[table] += 1
    return new_id


def is_logs_partitioned(cursor) -> bool:
    """Check if logs table is defined as a partitioned table."""
    cursor.execute(
        "SELECT EXISTS (SELECT 1 FROM pg_partitioned_table WHERE partrelid = 'logs'::regclass)"
    )
    return bool(cursor.fetchone()[0])


def ensure_partition_for_datetime(
    cursor,
    ts: datetime,
    partition_cache: Set[date],
    enabled: bool = True,
) -> None:
    """
    Ensure a daily partition exists for a given timestamp.
    Uses an in-memory cache to avoid repeated CREATE calls for the same date.
    Uses sql.Literal instead of parameters in FOR VALUES FROM / TO.
    """
    if not enabled or ts is None:
        return

    d = ts.date()
    if d in partition_cache:
        return

    part_name = f"logs_{d.year:04d}_{d.month:02d}_{d.day:02d}"
    day_start = datetime(d.year, d.month, d.day)
    next_day = day_start + timedelta(days=1)

    stmt = sql.SQL(
        """
        CREATE TABLE IF NOT EXISTS {part}
        PARTITION OF logs
        FOR VALUES FROM ({start}) TO ({end});
        """
    ).format(
        part=sql.Identifier(part_name),
        start=sql.Literal(day_start),
        end=sql.Literal(next_day),
    )

    logging.info("Ensuring partition %s (%s -> %s)", part_name, day_start, next_day)
    cursor.execute(stmt)
    partition_cache.add(d)


def write_offline(logfile: str, offline_file: str):
    """
    Parse log file and save parsed records to JSONL for later DB import.
    Returns (stats, duration, rate).
    """
    start_time = time.time()
    processed = 0
    failed = 0

    logging.info(f"Offline mode: parsing {logfile} and writing to {offline_file}")

    with open(logfile, "r", encoding="utf-8") as f_in, open(
        offline_file, "a", encoding="utf-8"
    ) as f_out:
        for line in f_in:
            data = parse_line(line)
            if not data:
                failed += 1
                logging.warning(f"Line does not match pattern (offline): {line.strip()}")
                continue

            record = {
                "timestamp": data["timestamp"],
                "source_ip": data["source_ip"],
                "source_port": data["source_port"],
                "dest_protocol": data["dest_protocol"],
                "dest_host": data["dest_host"],
                "dest_port": data["dest_port"],
                "inbound_tag": data["inbound_tag"],
                "outbound_tag": data["outbound_tag"],
                "email": data["email"],
                "action": "accepted",
            }
            json.dump(record, f_out, ensure_ascii=False)
            f_out.write("\n")
            processed += 1

    # clear original log file
    with open(logfile, "w", encoding="utf-8") as f:
        f.truncate(0)

    duration = time.time() - start_time
    rate = processed / duration if duration > 0 else 0
    logging.info(
        f"Offline mode finished: {processed} lines, failed to parse: {failed}, "
        f"speed: {rate:.2f} lines/sec."
    )

    stats = {
        "users": 0,
        "protocols": 0,
        "endpoints": 0,
        "tags": 0,
        "processed": processed,
        "failed": failed,
    }
    return stats, duration, rate


def import_offline_buffer(
    cursor,
    caches: Dict[str, Dict[str, int]],
    stats: Dict[str, int],
    offline_file: str,
    partitioned: bool,
    partition_cache: Set[date],
) -> None:
    """Import previously saved JSONL logs into DB."""
    if not os.path.exists(offline_file) or os.path.getsize(offline_file) == 0:
        return

    logging.info(f"Found offline buffer {offline_file}, importing into DB")
    batch = []

    with open(offline_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                logging.warning(f"Failed to parse JSON from offline file: {e}")
                stats["failed"] += 1
                continue

            try:
                log_time = datetime.strptime(rec["timestamp"], "%Y/%m/%d %H:%M:%S.%f")
            except (KeyError, ValueError) as e:
                logging.warning(f"Invalid timestamp in offline file: {e}")
                stats["failed"] += 1
                continue

            ensure_partition_for_datetime(cursor, log_time, partition_cache, enabled=partitioned)

            user_id = resolve_id(
                cursor, caches["users"], stats, "users", "email", rec.get("email")
            )
            protocol_id = resolve_id(
                cursor,
                caches["protocols"],
                stats,
                "protocols",
                "name",
                rec.get("dest_protocol"),
            )
            endpoint_id = resolve_id(
                cursor,
                caches["endpoints"],
                stats,
                "endpoints",
                "address",
                rec.get("dest_host"),
            )
            inbound_tag_id = resolve_id(
                cursor,
                caches["tags"],
                stats,
                "tags",
                "name",
                rec.get("inbound_tag"),
            )
            outbound_tag_id = resolve_id(
                cursor,
                caches["tags"],
                stats,
                "tags",
                "name",
                rec.get("outbound_tag"),
            )

            batch.append(
                (
                    log_time,
                    rec["source_ip"],
                    int(rec["source_port"]),
                    rec.get("action", "accepted"),
                    protocol_id,
                    endpoint_id,
                    int(rec["dest_port"]) if rec.get("dest_port") else None,
                    inbound_tag_id,
                    outbound_tag_id,
                    user_id,
                )
            )

            if len(batch) >= BATCH_SIZE:
                cursor.executemany(LOG_INSERT_SQL, batch)
                stats["processed"] += len(batch)
                logging.info(
                    f"Inserted batch of {len(batch)} offline records. "
                    f"Total processed (including offline): {stats['processed']}"
                )
                batch.clear()

    if batch:
        cursor.executemany(LOG_INSERT_SQL, batch)
        stats["processed"] += len(batch)
        logging.info(
            f"Inserted final batch of {len(batch)} offline records. "
            f"Total processed (including offline): {stats['processed']}"
        )


def export_stats(
    stats: Dict[str, int],
    duration: float,
    rate: float,
    stats_format: Optional[str],
    stats_output: Optional[str],
) -> None:
    """Export summary stats to JSON or CSV, to file or stdout."""
    if not stats_format:
        return

    payload = {
        "duration_seconds": round(duration, 2),
        "processed": stats.get("processed", 0),
        "failed": stats.get("failed", 0),
        "rate_lines_per_second": round(rate, 2),
        "new_users": stats.get("users", 0),
        "new_endpoints": stats.get("endpoints", 0),
        "new_protocols": stats.get("protocols", 0),
        "new_tags": stats.get("tags", 0),
    }

    if stats_format == "json":
        content = json.dumps(payload, ensure_ascii=False, indent=2)
    elif stats_format == "csv":
        header = ",".join(payload.keys())
        values = ",".join(str(v) for v in payload.values())
        content = header + "\n" + values
    else:
        logging.warning(f"Unknown stats format: {stats_format}, skipping stats export.")
        return

    if stats_output:
        with open(stats_output, "w", encoding="utf-8") as f:
            f.write(content)
        logging.info(f"Stats written to {stats_output} ({stats_format}).")
    else:
        print(content)


def process_log_file(config_path: str) -> None:
    """
    Process log file:
    * if DB is available — insert into DB (including previously saved offline logs),
    * if DB is not available — save parsed logs to JSONL.
    All paths and parameters are taken from config.ini.
    """
    config = load_config(config_path)

    if not config.has_section("parser") or not config.has_option("parser", "logfile"):
        logging.error(
            "Section [parser] with option 'logfile' is required in config to run parser."
        )
        raise SystemExit(1)

    logfile = config.get("parser", "logfile")
    offline_file = config.get("parser", "offline_file", fallback="pending_logs.jsonl")

    global BATCH_SIZE
    BATCH_SIZE = int(config.get("parser", "batch_size", fallback=str(BATCH_SIZE)))

    stats_format = None
    stats_output = None
    if config.has_section("stats"):
        stats_format = config.get("stats", "format", fallback=None)
        stats_output = config.get("stats", "output", fallback=None)

    start_time = time.time()
    logging.info(f"Starting processing file: {logfile}")

    if not os.path.exists(logfile) or os.path.getsize(logfile) == 0:
        logging.info("Log file not found or empty. Exiting.")
        return

    conn = get_db_connection(config)
    if not conn:
        # offline mode: parse and write to JSONL
        stats, duration, rate = write_offline(logfile, offline_file)
        export_stats(stats, duration, rate, stats_format, stats_output)
        return

    caches: Dict[str, Dict[str, int]] = {
        "users": {},
        "protocols": {},
        "endpoints": {},
        "tags": {},
    }
    stats: Dict[str, int] = {
        "users": 0,
        "protocols": 0,
        "endpoints": 0,
        "tags": 0,
        "processed": 0,
        "failed": 0,
    }
    log_batch = []

    try:
        with conn.cursor() as cur:
            partitioned = is_logs_partitioned(cur)
            partition_cache: Set[date] = set()

            # first, import offline logs if any
            import_offline_buffer(
                cur, caches, stats, offline_file, partitioned, partition_cache
            )

            # then process current log file
            with open(logfile, "r", encoding="utf-8") as f:
                for line in f:
                    data = parse_line(line)
                    if not data:
                        stats["failed"] += 1
                        logging.warning(f"Line does not match pattern: {line.strip()}")
                        continue

                    try:
                        log_time = datetime.strptime(
                            data["timestamp"], "%Y/%m/%d %H:%M:%S.%f"
                        )
                    except (KeyError, ValueError) as e:
                        stats["failed"] += 1
                        logging.warning(
                            f"Invalid timestamp in log line, skipping: {e} | {line.strip()}"
                        )
                        continue

                    ensure_partition_for_datetime(
                        cur, log_time, partition_cache, enabled=partitioned
                    )

                    user_id = resolve_id(
                        cur, caches["users"], stats, "users", "email", data.get("email")
                    )
                    protocol_id = resolve_id(
                        cur,
                        caches["protocols"],
                        stats,
                        "protocols",
                        "name",
                        data.get("dest_protocol"),
                    )
                    endpoint_id = resolve_id(
                        cur,
                        caches["endpoints"],
                        stats,
                        "endpoints",
                        "address",
                        data.get("dest_host"),
                    )
                    inbound_tag_id = resolve_id(
                        cur,
                        caches["tags"],
                        stats,
                        "tags",
                        "name",
                        data.get("inbound_tag"),
                    )
                    outbound_tag_id = resolve_id(
                        cur,
                        caches["tags"],
                        stats,
                        "tags",
                        "name",
                        data.get("outbound_tag"),
                    )

                    log_batch.append(
                        (
                            log_time,
                            data["source_ip"],
                            int(data["source_port"]),
                            "accepted",
                            protocol_id,
                            endpoint_id,
                            int(data["dest_port"]) if data.get("dest_port") else None,
                            inbound_tag_id,
                            outbound_tag_id,
                            user_id,
                        )
                    )

                    if len(log_batch) >= BATCH_SIZE:
                        cur.executemany(LOG_INSERT_SQL, log_batch)
                        stats["processed"] += len(log_batch)
                        logging.info(
                            f"Inserted batch of {len(log_batch)} records. "
                            f"Total processed: {stats['processed']}"
                        )
                        log_batch.clear()

            if log_batch:
                cur.executemany(LOG_INSERT_SQL, log_batch)
                stats["processed"] += len(log_batch)

            conn.commit()

            # clear log file only after successful commit
            with open(logfile, "w", encoding="utf-8") as f:
                f.truncate(0)

            # clear offline buffer only after successful commit
            if os.path.exists(offline_file):
                with open(offline_file, "w", encoding="utf-8") as f:
                    f.truncate(0)

            logging.info("Transaction committed successfully. Log file and offline buffer cleaned.")

    except (Exception, psycopg.Error) as error:
        logging.error(f"Error occurred, transaction rolled back: {error}")
        conn.rollback()
    finally:
        conn.close()

    end_time = time.time()
    duration = end_time - start_time
    rate = stats["processed"] / duration if duration > 0 else 0

    logging.info("=" * 50)
    logging.info("Execution statistics:")
    logging.info(f"  Total time: {duration:.2f} sec.")
    logging.info(f"  Total lines processed: {stats['processed']}")
    logging.info(f"  Lines failed to parse: {stats['failed']}")
    logging.info(f"  Processing speed: {rate:.2f} lines/sec.")
    logging.info("  New reference records created:")
    logging.info(f"    - Users: {stats['users']}")
    logging.info(f"    - Endpoints: {stats['endpoints']}")
    logging.info(f"    - Protocols: {stats['protocols']}")
    logging.info(f"    - Tags: {stats['tags']}")
    logging.info("=" * 50)

    export_stats(stats, duration, rate, stats_format, stats_output)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "xray-core log parser with PostgreSQL loading, offline buffering, "
            "automatic partition creation and config-driven parameters."
        )
    )
    parser.add_argument(
        "--config",
        default="config.ini",
        help="Path to config.ini with [postgresql], [parser], [stats] sections.",
    )
    args = parser.parse_args()

    process_log_file(args.config)


if __name__ == "__main__":
    main()
