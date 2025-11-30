# Xray Log Ingestion & Analytics Pipeline

This project ingests xray-core access logs into PostgreSQL and ships a lightweight analytics stack built with FastAPI (backend) and Next.js + shadcn/ui (frontend) for browsing activity in near real time.

---

## Core ingestion features

- PostgreSQL-backed log storage with optional daily range partitioning.
- Online (direct DB inserts) and offline (JSONL buffering) parsing modes.
- Automatic partition creation for `logs_YYYY_MM_DD` partitions.
- Reference tables for users, protocols, endpoints, and tags.
- Per-run statistics exported to JSONL or CSV.
- Config-driven behavior with CLI overrides and rich logging via [`loguru`](https://github.com/Delgan/loguru).

See [`SCHEMA.md`](SCHEMA.md) for DDL details, and the CLI scripts `parse_logs.py` / `migrate_logs_to_partitioned.py` for ingestion and migration tooling.

---

## Web analytics stack (FastAPI + Next.js + shadcn/ui)

The new dashboard reads data directly from PostgreSQL and exposes it via a modern API/UI pair:

- **Backend:** `backend/app/main.py` – FastAPI with async SQLAlchemy + asyncpg. Endpoints:
  - `GET /api/logs` – paginated list with filters: `search` (destination host/email/IP), `protocol`, `tag`, `limit`, `offset`.
  - `GET /api/logs/stats` – totals, unique users, and protocol/tag distributions.
  - `GET /health` – basic readiness probe.
- **Frontend:** `frontend/` Next.js (App Router) with shadcn-style UI components. Provides live filters, pagination, and summary cards.
- **Source of truth:** PostgreSQL connection configured via `DATABASE_URL`.

### Running the stack locally

1. **Prepare PostgreSQL** with a `logs` table that matches the columns in `backend/app/db/models.py`. Set a connection string, for example:

   ```env
   # backend/.env
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/xraylogs
   ```

2. **Start the FastAPI service** (from repo root):

   ```bash
   uv run uvicorn backend.main:app --reload --port 8000 --app-dir backend
   ```

3. **Start the Next.js frontend**:

   ```bash
   cd frontend
   npm install
   NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
   ```

4. Open `http://localhost:3000` to interact with the dashboard. Filters and pagination are executed against live PostgreSQL data.

---

## Configuration for the parser CLI

The ingestion scripts remain configurable via `config.ini`:

```ini
[postgresql]
host=localhost
port=5432
dbname=mydb
user=myuser
password=mypassword

[parser]
logfile=/var/log/xray/xray.log
offline_file=/var/log/xray/pending_logs.jsonl
batch_size=1000

[stats]
format=json
output=/var/log/xray/parser_stats.jsonl

[migration]
drop_old=false
```

- `logfile` can be overridden with `--logfile`.
- `offline_file` is used while DB is unreachable; contents are imported once connectivity returns.
- `drop_old` drops the legacy `logs` table after a successful migration.

---

## Example log line

```
2025/11/17 10:15:23.123 from tcp:192.168.0.10 : 54321 accepted tcp:example.com : 443 [inbound >> direct] email:user@example.com
```

The parser normalizes timestamps, source/destination, routing tags, and optional email for storage in PostgreSQL.
