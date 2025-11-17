# Database Schema

This document describes the relational schema used by the xray log ingestion pipeline.

The schema is designed for:

- Normalized storage of log metadata (users, endpoints, protocols, tags)
- Efficient time-based queries via a partitioned `logs` table
- Easy extension for additional analytics

---

## Requirements

- PostgreSQL 10+ (native table partitioning)
- Built-in types:
  - `TIMESTAMPTZ` – timestamp with time zone
  - `INET` – IP address

---

## Overview

The schema consists of:

- `users` – unique email identities
- `protocols` – network protocols (e.g. `tcp`, `udp`)
- `endpoints` – destination hosts (domain names or IPs)
- `tags` – logical routing labels
- `logs` – main partitioned fact table referencing the above

---

## Table: `users`

Stores user identities extracted from the `email:` field in logs.

```sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL
);
```

- **id** – internal numeric identifier.
- **email** – user email address, must be unique and non-null.

Typical usage:

- Joining from `logs.user_id` to get the email.
- Tracking per-user activity and sessions.

---

## Table: `protocols`

Stores network protocol names.

```sql
CREATE TABLE IF NOT EXISTS protocols (
    id SERIAL PRIMARY KEY,
    name VARCHAR(10) UNIQUE NOT NULL
);
```

- **id** – internal numeric identifier.
- **name** – protocol name (e.g., `tcp`, `udp`).

`logs.protocol_id` references this table. New protocols are inserted on-the-fly when first seen.

---

## Table: `endpoints`

Stores destination addresses (domain names or IP addresses).

```sql
CREATE TABLE IF NOT EXISTS endpoints (
    id SERIAL PRIMARY KEY,
    address VARCHAR(255) UNIQUE NOT NULL
);
```

- **id** – internal numeric identifier.
- **address** – destination hostname or IP address (e.g., `example.com`, `1.2.3.4`).

`logs.destination_id` references this table. New endpoints are automatically created as new addresses appear in logs.

---

## Table: `tags`

Stores logical routing tags, such as inbound/outbound markers or special route labels.

```sql
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);
```

- **id** – internal numeric identifier.
- **name** – tag name (e.g., `inbound`, `direct`, `api`).

`logs.inbound_tag_id` and `logs.outbound_tag_id` reference this table. Tags are extracted from the optional "route" part of log lines, for example `[inbound >> direct]`.

---

## Table: `logs` (Partitioned)

Main fact table storing normalized log records. Implemented as a **partitioned table by timestamp** (daily range partitions).

### Parent Table Definition

```sql
CREATE TABLE IF NOT EXISTS logs (
    id BIGSERIAL,
    "timestamp" TIMESTAMPTZ NOT NULL,
    source_ip INET NOT NULL,
    source_port INTEGER NOT NULL,
    action VARCHAR(50),
    protocol_id INTEGER REFERENCES protocols(id),
    destination_id INTEGER REFERENCES endpoints(id),
    destination_port INTEGER,
    inbound_tag_id INTEGER REFERENCES tags(id),
    outbound_tag_id INTEGER REFERENCES tags(id),
    user_id INTEGER REFERENCES users(id)
) PARTITION BY RANGE ("timestamp");
```

Fields:

- **id** – surrogate key (`BIGSERIAL`). Not globally enforced as a primary key to avoid complexity with partitioning.
- **timestamp** – UTC timestamp (with time zone) of the log event.
- **source_ip** – client IP, `INET` type.
- **source_port** – client source port.
- **action** – textual description of the action (e.g., `accepted`).
- **protocol_id** – FK → `protocols.id`.
- **destination_id** – FK → `endpoints.id`.
- **destination_port** – destination port as integer.
- **inbound_tag_id** – FK → `tags.id` (incoming route tag).
- **outbound_tag_id** – FK → `tags.id` (outgoing route tag).
- **user_id** – FK → `users.id` (can be `NULL` when email is missing).

> **Note:** The column name `timestamp` is quoted as `"timestamp"` because `timestamp` is a SQL type name; quoting avoids ambiguity.

### Daily Partitions

The table is partitioned by daily ranges of `timestamp`. Each partition stores data for one day in UTC:

```sql
CREATE TABLE IF NOT EXISTS logs_2025_11_17
    PARTITION OF logs
    FOR VALUES FROM ('2025-11-17 00:00:00+00') TO ('2025-11-18 00:00:00+00');

CREATE TABLE IF NOT EXISTS logs_2025_11_18
    PARTITION OF logs
    FOR VALUES FROM ('2025-11-18 00:00:00+00') TO ('2025-11-19 00:00:00+00');
```

Partitions are:

- Created automatically by the ingestion code when new timestamps are encountered (on demand).
- Also created in bulk by the migration script for historical ranges.

You can further create partitions in advance using a simple PL/pgSQL loop if you want strict control.

---

## Indexes

Indexes are created on the parent `logs` table; PostgreSQL propagates them to all partitions.

Recommended indexes:

```sql
-- Time-based index (BTREE)
CREATE INDEX IF NOT EXISTS idx_logs_timestamp
    ON logs ("timestamp");

-- Foreign keys / frequent filters
CREATE INDEX IF NOT EXISTS idx_logs_user_id
    ON logs (user_id);

CREATE INDEX IF NOT EXISTS idx_logs_source_ip
    ON logs (source_ip);

CREATE INDEX IF NOT EXISTS idx_logs_destination_id
    ON logs (destination_id);
```

### Optional: Composite and BRIN Indexes

For analytics heavy on user/timestamp queries:

```sql
-- Composite index for per-user time-ordered analytics
CREATE INDEX IF NOT EXISTS idx_logs_user_ts
    ON logs (user_id, "timestamp");
```

For very large datasets with mostly time-ordered inserts, a BRIN index can be used:

```sql
CREATE INDEX IF NOT EXISTS idx_logs_timestamp_brin
    ON logs USING brin ("timestamp")
    WITH (pages_per_range = 256);
```

BRIN indexes are compact and work very well for range queries on time-series data.

---

## Relationships Summary

- `logs.user_id` → `users.id`
- `logs.protocol_id` → `protocols.id`
- `logs.destination_id` → `endpoints.id`
- `logs.inbound_tag_id` → `tags.id`
- `logs.outbound_tag_id` → `tags.id`

The ingestion pipeline:

1. Parses raw log lines and extracts normalized fields.
2. Resolves or inserts:
   - `users.email`
   - `protocols.name`
   - `endpoints.address`
   - `tags.name`
3. Inserts a record into `logs` with foreign keys to the above.

This model allows you to run rich analytical queries, such as:

- per-user sessions and activity timelines,
- per-endpoint or per-protocol traffic analysis,
- route/tag-based aggregations (inbound vs outbound paths),
- time-based slicing and dicing thanks to partitioning.
