# Xray Log Ingestion & Analytics Pipeline

This project provides a robust ingestion pipeline for xray-core access logs into PostgreSQL with:

- Daily range-partitioned `logs` table by timestamp
- Online and offline processing modes
- Automatic partition creation
- Reference tables for users, protocols, endpoints, and tags
- Persistent per-run statistics in JSONL or CSV
- Config-driven behavior and CLI overrides
- Modern logging via [`loguru`](https://github.com/Delgan/loguru)

The goal is to reliably parse xray-core logs, normalize them into a relational model, and keep the system operational even when the database is temporarily unavailable.

---

## Features

- **PostgreSQL-backed log storage**
  - `logs` table partitioned by `timestamp` (daily partitions)
  - Reference tables: `users`, `protocols`, `endpoints`, `tags`
- **Automatic partition management**
  - Creates daily partitions `logs_YYYY_MM_DD` on demand
  - Supports historical migration from a non-partitioned `logs` table
- **Online / Offline ingestion**
  - **Online mode**: logs are inserted directly into PostgreSQL
  - **Offline mode**: when DB is unavailable, logs are buffered into a JSONL file
  - On the next successful online run, offline buffer is imported into the DB
- **Per-run statistics**
  - Stored in JSONL or CSV with:
    - run timestamp, mode (`online` / `offline`)
    - processed/failed line counts
    - ingestion rate (lines/sec)
    - counts of new users/endpoints/protocols/tags
- **Config-driven**
  - Single `config.ini` controls DB credentials, file paths, batch size, and stats output
  - CLI parameter `--logfile` can override the logfile defined in the config
- **Modern logging**
  - Uses `loguru` for rich and readable logging output

---

## Requirements

- Python 3.10+ (3.12 recommended)
- PostgreSQL 10+ (partitioned tables support)
- Python packages:
  - `psycopg` (psycopg3)
  - `loguru`

Install dependencies (example):

```bash
pip install psycopg[binary] loguru
```

---

## Configuration

The application is configured via `config.ini`. A typical configuration:

```ini
[postgresql]
host=localhost
port=5432
dbname=mydb
user=myuser
password=mypassword

[parser]
; Default logfile path (can be overridden by CLI --logfile)
logfile=/var/log/xray/xray.log

; JSONL buffer for offline mode
offline_file=/var/log/xray/pending_logs.jsonl

; Batch size for INSERTs into PostgreSQL
batch_size=1000

[stats]
; json or csv (leave empty/omit to disable file-based stats)
format=json

; Path to stats output file. If omitted, stats are printed to stdout.
output=/var/log/xray/parser_stats.jsonl

[migration]
; Whether to drop logs_old after a successful migration
drop_old=false
```

### Sections

- **[postgresql]** – DB connection parameters.
- **[parser]**
  - `logfile` – default path to the xray-core log file.
  - `offline_file` – JSONL file used as a buffer when DB is unavailable.
  - `batch_size` – number of rows per batch insert.
- **[stats]**
  - `format` – `json` (JSONL) or `csv`.
  - `output` – file where stats are appended; if omitted, stats go to stdout.
- **[migration]**
  - `drop_old` – `true/false`, whether to drop `logs_old` after migration.

---

## Database Schema

The core schema consists of:

- `users` – unique emails
- `protocols` – protocol names (e.g., tcp, udp)
- `endpoints` – destination hostnames/IPs
- `tags` – logical routing tags (e.g., inbound, direct, api)
- `logs` – main partitioned table with references to the above

See **Schema.md** in this repository for a detailed description and DDL.

---

## Migration to a Partitioned `logs` Table

If you already have a non-partitioned `logs` table with data, use the migration script to convert it into a partitioned structure:

```bash
python migrate_logs_to_partitioned.py --config config.ini
# or, to drop the old table after success:
python migrate_logs_to_partitioned.py --config config.ini --drop-old
```

The migration script will:

1. Rename `logs` → `logs_old`.
2. Create a new `logs` table partitioned by `timestamp` (RANGE).
3. Compute `[MIN(timestamp), MAX(timestamp)]` from `logs_old`.
4. Create daily partitions for this range.
5. Copy all rows from `logs_old` into the new `logs` table.
6. Recreate indexes on `logs` (which propagate to partitions).
7. Adjust the `logs.id` sequence.
8. Optionally drop `logs_old`.

> **Note:** Make sure your application is not writing to `logs` during the migration.

---

## Log Format

The parser expects xray-core-like log lines, for example:

```text
2025/11/17 10:15:23.123 from tcp:192.168.0.10 : 54321 accepted tcp:example.com : 443 [inbound >> direct] email:user@example.com
```

Or special API lines:

```text
2025/11/17 10:16:00.000 api from 10.0.0.1:12345 api -> api
```

The main pattern (simplified):

- Date and time with microseconds: `YYYY/MM/DD HH:MM:SS.ffffff`
- `from` section: `from [tcp|udp]:SRC_IP : SRC_PORT`
- Action: `accepted`
- Destination:
  - `tcp:HOST : PORT`
  - `udp:HOST : PORT`
  - or `//HOST : PORT` (no explicit protocol)
- Optional route: `[inbound >> direct]` or `[inbound -> direct]`
- Optional email: `email:user@example.com`

All recognized fields are normalized and inserted into the database.

---

## Online vs Offline Modes

### Online Mode

If the DB connection succeeds:

- Any pending offline buffer (`pending_logs.jsonl`) is imported first.
- The current logfile is parsed and inserted directly into PostgreSQL.
- Daily partitions are created automatically as needed.
- On success:
  - the logfile is truncated,
  - the offline buffer is cleared.

### Offline Mode

If the DB connection fails:

- The logfile is parsed.
- Parsed records are appended to the JSONL buffer (`offline_file`).
- The logfile is truncated (so the same lines are not reprocessed).
- No database writes are attempted.
- On the next successful online run, all buffered records are imported.

---

## Statistics

Each run (online or offline) produces a statistics record with:

- `run_started_at` – ISO timestamp of when the run started
- `mode` – `"online"` or `"offline"`
- `duration_seconds`
- `processed` – number of successfully processed lines
- `failed` – number of lines that failed to parse
- `rate_lines_per_second`
- `new_users`
- `new_endpoints`
- `new_protocols`
- `new_tags`

### JSONL Example

```json
{"run_started_at": "2025-11-17T13:10:01.234567", "mode": "online", "duration_seconds": 1.23, "processed": 1024, "failed": 3, "rate_lines_per_second": 832.52, "new_users": 2, "new_endpoints": 5, "new_protocols": 0, "new_tags": 1}
{"run_started_at": "2025-11-17T13:20:05.987654", "mode": "offline", "duration_seconds": 0.87, "processed": 512, "failed": 0, "rate_lines_per_second": 588.51, "new_users": 0, "new_endpoints": 1, "new_protocols": 0, "new_tags": 0}
```

### CSV Example

```csv
run_started_at,mode,duration_seconds,processed,failed,rate_lines_per_second,new_users,new_endpoints,new_protocols,new_tags
2025-11-17T13:10:01.234567,online,1.23,1024,3,832.52,2,5,0,1
2025-11-17T13:20:05.987654,offline,0.87,512,0,588.51,0,1,0,0
```

---

## Running the Parser

Basic usage:

```bash
python parse_logs.py --config config.ini
```

Override logfile from the command line (ignores `[parser].logfile`):

```bash
python parse_logs.py --config config.ini --logfile /tmp/custom_xray.log
```

The script will:

1. Check if the logfile exists and is non-empty.
2. Attempt to connect to PostgreSQL.
3. Choose **online** or **offline** mode depending on DB availability.
4. Process logs accordingly and update statistics.

---

## Notes & Tips

- Make sure PostgreSQL has the required types (`INET`, `TIMESTAMPTZ` are built-ins).
- Keep an eye on partition growth; you may want to archive or drop old partitions if the dataset becomes very large.
- For heavy analytical workloads, consider additional indexes (e.g. `(user_id, timestamp)`).
- You can use the statistics output to build dashboards (Grafana, Prometheus exporters, or simple pandas notebooks).
