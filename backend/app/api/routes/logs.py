from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_session
from ...db.models import Log
from ...schemas.logs import LogListResponse, LogOut, LogStats

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("", response_model=LogListResponse)
async def list_logs(
    *,
    search: Optional[str] = Query(default=None, description="Search by destination host, email, or source IP"),
    protocol: Optional[str] = Query(default=None, description="Filter by protocol"),
    tag: Optional[str] = Query(default=None, description="Filter by inbound/outbound tag"),
    limit: int = Query(default=50, ge=1, le=200, description="Number of records per page"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_session),
) -> LogListResponse:
    filters = []
    if search:
        pattern = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(Log.destination_host).like(pattern),
                func.lower(Log.email).like(pattern),
                func.lower(Log.source_ip).like(pattern),
            )
        )
    if protocol:
        filters.append(func.lower(Log.protocol) == protocol.lower())
    if tag:
        tag_lower = tag.lower()
        filters.append(
            or_(func.lower(Log.inbound_tag) == tag_lower, func.lower(Log.outbound_tag) == tag_lower)
        )

    base_query = select(Log).where(*filters).order_by(Log.timestamp.desc())

    total_stmt = select(func.count()).select_from(Log).where(*filters)
    total_result = await session.execute(total_stmt)
    total = total_result.scalar_one()

    page_stmt = base_query.offset(offset).limit(limit)
    result = await session.execute(page_stmt)
    logs = result.scalars().all()

    return LogListResponse(total=total, items=[LogOut.model_validate(log) for log in logs])


@router.get("/stats", response_model=LogStats)
async def get_stats(session: AsyncSession = Depends(get_session)) -> LogStats:
    protocol_stmt = select(func.lower(Log.protocol), func.count()).group_by(func.lower(Log.protocol))
    protocol_rows = await session.execute(protocol_stmt)
    protocol_counts = {row[0]: row[1] for row in protocol_rows.all() if row[0]}

    inbound_stmt = select(func.lower(Log.inbound_tag), func.count()).where(Log.inbound_tag.is_not(None)).group_by(
        func.lower(Log.inbound_tag)
    )
    outbound_stmt = select(func.lower(Log.outbound_tag), func.count()).where(Log.outbound_tag.is_not(None)).group_by(
        func.lower(Log.outbound_tag)
    )
    inbound_rows = await session.execute(inbound_stmt)
    outbound_rows = await session.execute(outbound_stmt)

    tag_counts: dict[str, int] = {}
    for tag_value, count in [*inbound_rows.all(), *outbound_rows.all()]:
        if tag_value:
            tag_counts[tag_value] = tag_counts.get(tag_value, 0) + count

    unique_stmt = select(func.count(func.distinct(func.lower(Log.email)))).where(Log.email.is_not(None))
    unique_result = await session.execute(unique_stmt)
    unique_users = unique_result.scalar_one()

    total_stmt = select(func.count()).select_from(Log)
    total_result = await session.execute(total_stmt)
    total = total_result.scalar_one()

    return LogStats(
        total=total,
        protocol_counts=protocol_counts,
        tag_counts=tag_counts,
        unique_users=unique_users,
        available_protocols=sorted(protocol_counts.keys()),
        available_tags=sorted(tag_counts.keys()),
    )
