# Xray Log Ingestion & Analytics

This repository ingests xray-core access logs into PostgreSQL and ships a modern analytics UI built with **FastAPI**, **Next.js**, and **shadcn/ui**.

- Normalized PostgreSQL schema (`logs`, `users`, `protocols`, `endpoints`, `tags`) with daily range partitioning (see [`SCHEMA.md`](SCHEMA.md)).
- FastAPI backend that queries PostgreSQL for live log listings and aggregates.
- Next.js 15 frontend with shadcn/ui components for filtering, search, and at-a-glance stats.

## Quickstart: Analytics Stack

### Backend (FastAPI + PostgreSQL)

1. Export database settings (or place them in `.env` with `XRAY_DATABASE_URL`).

   ```bash
   export XRAY_DATABASE_URL="postgresql+asyncpg://xray_logs:xray_logs@localhost:5432/xray_logs"
   export XRAY_CORS_ALLOW_ORIGINS='["http://localhost:3000"]'
   ```

2. Install backend dependencies and start the API:

   ```bash
   uv run uvicorn backend.main:app --reload --port 8000
   ```

   Endpoints:
   - `GET /health` — readiness probe.
   - `GET /api/logs` — paginated list with `search`, `protocol`, `tag`, `limit`, `offset` filters.
   - `GET /api/logs/stats` — totals, unique users, and top protocols/tags.

### Frontend (Next.js + shadcn/ui)

1. Install Node dependencies inside `frontend/` (Node 18+):

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

2. Open http://localhost:3000. The app fetches directly from the FastAPI API (configure via `NEXT_PUBLIC_API_BASE_URL`).

Features:
- Live counters for total events, unique users, protocol/tag top lists.
- Log table with search by email/IP/hostname, protocol filter, and tag filter.
- UI components taken from shadcn/ui (Button, Card, Badge, Table, Input).

## Legacy ingestion pipeline

The original log ingestion scripts remain available:

- Partitioned schema and DDL are documented in [`SCHEMA.md`](SCHEMA.md).
- `parse_logs.py` ingests xray-core logs into PostgreSQL with automatic partition creation and offline buffering.
- `migrate_logs_to_partitioned.py` converts an existing non-partitioned `logs` table into the partitioned layout.

Use these scripts to populate the database that powers the FastAPI analytics API.
