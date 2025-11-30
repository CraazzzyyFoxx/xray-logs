from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.db import get_session
from ..schemas.logs import LogRecord, LogStats, LogsResponse

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/logs", response_model=LogsResponse)
async def list_logs(
    *,
    search: Optional[str] = Query(default=None, description="Search by destination host, email, or source IP"),
    protocol: Optional[str] = Query(default=None, description="Filter by protocol"),
    tag: Optional[str] = Query(default=None, description="Filter by inbound/outbound tag"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    filters = ["1=1"]
    params: dict[str, object] = {"limit": limit, "offset": offset}

    if search:
        filters.append(
            "(e.address ILIKE :search OR u.email ILIKE :search OR l.source_ip::text ILIKE :search)"
        )
        params["search"] = f"%{search}%"

    if protocol:
        filters.append("p.name = :protocol")
        params["protocol"] = protocol.lower()

    if tag:
        filters.append("(it.name = :tag OR ot.name = :tag)")
        params["tag"] = tag.lower()

    base_query = f"""
        FROM logs l
        LEFT JOIN protocols p ON p.id = l.protocol_id
        LEFT JOIN endpoints e ON e.id = l.destination_id
        LEFT JOIN tags it ON it.id = l.inbound_tag_id
        LEFT JOIN tags ot ON ot.id = l.outbound_tag_id
        LEFT JOIN users u ON u.id = l.user_id
        WHERE {' AND '.join(filters)}
    """

    count_stmt = text(f"SELECT count(*) {base_query}")
    total_result = await session.execute(count_stmt, params)
    total = int(total_result.scalar_one())

    rows_stmt = text(
        """
        SELECT
            l.id,
            l."timestamp" as timestamp,
            l.source_ip,
            l.source_port,
            e.address as destination_host,
            l.destination_port,
            p.name as protocol,
            l.action,
            it.name as inbound_tag,
            ot.name as outbound_tag,
            u.email
        """
        + base_query
        + " ORDER BY l.\"timestamp\" DESC LIMIT :limit OFFSET :offset"
    )
    results = await session.execute(rows_stmt, params)
    items = [LogRecord.model_validate(dict(row._mapping)) for row in results]
    return LogsResponse(total=total, items=items)


@router.get("/logs/stats", response_model=LogStats)
async def log_stats(session: AsyncSession = Depends(get_session)):
    total_stmt = text("SELECT count(*) FROM logs")
    total = int((await session.execute(total_stmt)).scalar_one())

    unique_users_stmt = text("SELECT count(DISTINCT user_id) FROM logs WHERE user_id IS NOT NULL")
    unique_users = int((await session.execute(unique_users_stmt)).scalar_one())

    protocol_stmt = text(
        """
        SELECT COALESCE(p.name, 'unknown') as protocol, count(*)
        FROM logs l
        LEFT JOIN protocols p ON p.id = l.protocol_id
        GROUP BY protocol
        ORDER BY count(*) DESC
        LIMIT 10
        """
    )
    protocol_counts = {row.protocol: row.count for row in (await session.execute(protocol_stmt))}

    tag_stmt = text(
        """
        SELECT COALESCE(t.name, 'untagged') as tag, count(*)
        FROM (
            SELECT inbound_tag_id as tag_id FROM logs
            UNION ALL
            SELECT outbound_tag_id as tag_id FROM logs
        ) tags_join
        LEFT JOIN tags t ON t.id = tags_join.tag_id
        GROUP BY tag
        ORDER BY count(*) DESC
        LIMIT 10
        """
    )
    tag_counts = {row.tag: row.count for row in (await session.execute(tag_stmt))}

    return LogStats(total=total, unique_users=unique_users, protocols=protocol_counts, tags=tag_counts)
