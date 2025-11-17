import argparse
import configparser
import logging
from datetime import datetime, date, timedelta

import psycopg
from psycopg import sql

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def load_config(config_path: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    read_files = config.read(config_path)
    if not read_files:
        raise RuntimeError(f"Failed to read config file: {config_path}")
    return config


def get_db_connection(config: configparser.ConfigParser) -> psycopg.Connection:
    if "postgresql" not in config:
        raise RuntimeError("Config section [postgresql] is missing")

    conn_str = " ".join([f"{key}='{value}'" for key, value in config["postgresql"].items()])
    return psycopg.connect(conn_str)


def is_logs_partitioned(cur) -> bool:
    cur.execute(
        "SELECT EXISTS (SELECT 1 FROM pg_partitioned_table WHERE partrelid = 'logs'::regclass)"
    )
    return bool(cur.fetchone()[0])


def create_partition_for_date(cur, d: date) -> None:
    """
    Создаёт дневную партицию logs_YYYY_MM_DD.
    ВАЖНО: границы партиций задаём через sql.Literal, а не параметры (%s),
    т.к. Postgres не допускает параметров в FOR VALUES FROM ... TO ...
    """
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
    cur.execute(stmt)


def migrate_logs_to_partitioned(config_path: str) -> None:
    config = load_config(config_path)
    drop_old = config.getboolean("migration", "drop_old", fallback=False)

    conn = get_db_connection(config)
    try:
        with conn:
            with conn.cursor() as cur:
                if is_logs_partitioned(cur):
                    logging.info("Table 'logs' is already partitioned. Nothing to do.")
                    return

                logging.info("Renaming existing logs table to logs_old")
                cur.execute("ALTER TABLE logs RENAME TO logs_old;")

                logging.info("Creating new partitioned logs table")
                cur.execute(
                    """
                    CREATE TABLE logs (
                        id BIGSERIAL,
                        timestamp TIMESTAMPTZ NOT NULL,
                        source_ip INET NOT NULL,
                        source_port INTEGER NOT NULL,
                        action VARCHAR(50),
                        protocol_id INTEGER REFERENCES protocols(id),
                        destination_id INTEGER REFERENCES endpoints(id),
                        destination_port INTEGER,
                        inbound_tag_id INTEGER REFERENCES tags(id),
                        outbound_tag_id INTEGER REFERENCES tags(id),
                        user_id INTEGER REFERENCES users(id)
                    ) PARTITION BY RANGE (timestamp);
                    """
                )

                logging.info("Calculating date range in logs_old")
                cur.execute(
                    "SELECT MIN(timestamp)::date, MAX(timestamp)::date FROM logs_old;"
                )
                min_date, max_date = cur.fetchone()

                if min_date is None or max_date is None:
                    logging.info("logs_old is empty. No data to migrate.")
                else:
                    logging.info("Creating partitions from %s to %s", min_date, max_date)
                    d = min_date
                    while d <= max_date:
                        create_partition_for_date(cur, d)
                        d += timedelta(days=1)

                    logging.info("Copying data from logs_old to partitioned logs")
                    cur.execute(
                        """
                        INSERT INTO logs (
                            id, timestamp, source_ip, source_port, action,
                            protocol_id, destination_id, destination_port,
                            inbound_tag_id, outbound_tag_id, user_id
                        )
                        SELECT
                            id, timestamp, source_ip, source_port, action,
                            protocol_id, destination_id, destination_port,
                            inbound_tag_id, outbound_tag_id, user_id
                        FROM logs_old
                        ORDER BY timestamp;
                        """
                    )

                logging.info("Creating indexes on new logs table")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs (timestamp);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs (user_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_source_ip ON logs (source_ip);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_destination_id ON logs (destination_id);")

                logging.info("Adjusting sequence for logs.id")
                cur.execute("SELECT pg_get_serial_sequence('logs', 'id');")
                seq_row = cur.fetchone()
                if seq_row and seq_row[0]:
                    seq_name = seq_row[0]
                    cur.execute("SELECT COALESCE(MAX(id), 0) FROM logs;")
                    max_id = cur.fetchone()[0] or 0
                    new_val = max_id + 1
                    cur.execute("SELECT setval(%s, %s, false);", (seq_name, new_val))
                    logging.info("Sequence %s set to %s", seq_name, new_val)
                else:
                    logging.warning("Could not determine sequence for logs.id")

                if drop_old:
                    logging.info("Dropping logs_old table as requested by config")
                    cur.execute("DROP TABLE IF EXISTS logs_old;")

                logging.info("Migration to partitioned logs table completed successfully.")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Migrate logs table to a partitioned table with daily partitions (config-driven)."
    )
    parser.add_argument(
        "--config",
        default="config.ini",
        help="Path to config.ini with [postgresql] and [migration] sections.",
    )
    args = parser.parse_args()
    migrate_logs_to_partitioned(args.config)


if __name__ == "__main__":
    main()
