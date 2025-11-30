from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.db import get_session
from ..schemas.logs import SessionEvent, SessionSummary, SiteVisit, UserProfile

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/users/{user_id}/profile", response_model=UserProfile)
async def get_user_profile(
    user_id: int,
    *,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    params: dict[str, object] = {"user_id": user_id, "limit": limit, "offset": offset}

    sessions_stmt = text(
        """
        WITH session_data AS (
            SELECT
                l.id AS log_id,
                l.user_id,
                l."timestamp",
                LAG(l."timestamp", 1) OVER (
                    PARTITION BY l.user_id
                    ORDER BY l."timestamp"
                ) AS prev_timestamp
            FROM logs l
            WHERE
                l.user_id IS NOT NULL
                AND l."timestamp" BETWEEN now() - interval '3 days' AND now()
                AND l.user_id = :user_id
        ),
        session_starts AS (
            SELECT
                log_id,
                user_id,
                "timestamp",
                CASE
                    WHEN prev_timestamp IS NULL
                         OR "timestamp" - prev_timestamp > INTERVAL '10 minutes'
                    THEN 1
                    ELSE 0
                END AS is_new_session
            FROM session_data
        ),
        session_ids AS (
            SELECT
                log_id,
                user_id,
                "timestamp",
                SUM(is_new_session) OVER (
                    PARTITION BY user_id
                    ORDER BY "timestamp"
                ) AS session_group_id
            FROM session_starts
        ),
        session_bounds AS (
            SELECT
                user_id,
                session_group_id,
                MIN("timestamp") AS started_at,
                MAX("timestamp") AS ended_at,
                COUNT(*) AS events
            FROM session_ids
            GROUP BY user_id, session_group_id
        )
        SELECT
            sb.user_id,
            u.email,
            sb.session_group_id,
            sb.started_at + interval '3 hours' AS started_at,
            sb.ended_at + interval '3 hours' AS ended_at,
            sb.events
        FROM session_bounds sb
        JOIN users u ON u.id = sb.user_id
        ORDER BY sb.ended_at DESC
        LIMIT :limit OFFSET :offset
        """
    )

    sessions_result = await session.execute(sessions_stmt, params)
    sessions = [SessionSummary.model_validate(dict(row._mapping)) for row in sessions_result]

    if not sessions:
        exists_stmt = text("SELECT id, email FROM users WHERE id = :user_id")
        user_row = (await session.execute(exists_stmt, {"user_id": user_id})).first()
        if user_row is None:
            raise HTTPException(status_code=404, detail="User not found")
        email: Optional[str] = user_row.email
    else:
        email = sessions[0].email

    sites_stmt = text(
        """
        SELECT
            e.address AS site,
            MIN(l."timestamp") + interval '3 hours' AS first_visit,
            MAX(l."timestamp") + interval '3 hours' AS last_visit,
            COUNT(*) AS hits_count
        FROM logs l
        JOIN endpoints e ON l.destination_id = e.id
        WHERE
            l.user_id = :user_id
        GROUP BY e.address
        ORDER BY last_visit DESC
        LIMIT 20
        """
    )
    sites_result = await session.execute(sites_stmt, {"user_id": user_id})
    sites = [SiteVisit.model_validate(dict(row._mapping)) for row in sites_result]

    return UserProfile(user_id=user_id, email=email, sessions=sessions, top_sites=sites)


@router.get("/users/{user_id}/sessions/{session_group_id}", response_model=list[SessionEvent])
async def get_session_events(
    user_id: int,
    session_group_id: int,
    *,
    session: AsyncSession = Depends(get_session),
):
    params = {"user_id": user_id, "session_group_id": session_group_id}

    events_stmt = text(
        """
        WITH session_data AS (
            SELECT
                l.id AS log_id,
                l.user_id,
                l."timestamp",
                LAG(l."timestamp", 1) OVER (
                    PARTITION BY l.user_id
                    ORDER BY l."timestamp"
                ) AS prev_timestamp
            FROM logs l
            WHERE
                l.user_id IS NOT NULL
                AND l."timestamp" BETWEEN now() - interval '3 days' AND now()
                AND l.user_id = :user_id
        ),
        session_starts AS (
            SELECT
                log_id,
                user_id,
                "timestamp",
                CASE
                    WHEN prev_timestamp IS NULL
                         OR "timestamp" - prev_timestamp > INTERVAL '10 minutes'
                    THEN 1
                    ELSE 0
                END AS is_new_session
            FROM session_data
        ),
        session_ids AS (
            SELECT
                log_id,
                user_id,
                "timestamp",
                SUM(is_new_session) OVER (
                    PARTITION BY user_id
                    ORDER BY "timestamp"
                ) AS session_group_id
            FROM session_starts
        )
        SELECT
            l.id,
            u.email,
            l."timestamp" + interval '3 hours' AS event_time,
            l.source_ip,
            l.source_port,
            p.name AS protocol,
            e.address AS destination,
            l.destination_port,
            ti.name  AS inbound_tag,
            to_.name AS outbound_tag,
            l.action,
            s.session_group_id
        FROM session_ids s
        JOIN logs      l   ON l.id = s.log_id
        JOIN users     u   ON s.user_id = u.id
        LEFT JOIN protocols p ON l.protocol_id      = p.id
        LEFT JOIN endpoints e ON l.destination_id   = e.id
        LEFT JOIN tags ti     ON l.inbound_tag_id   = ti.id
        LEFT JOIN tags to_    ON l.outbound_tag_id  = to_.id
        WHERE
            s.user_id = :user_id
            AND s.session_group_id = :session_group_id
        ORDER BY
            event_time DESC
        LIMIT 200
        """
    )

    results = await session.execute(events_stmt, params)
    events = [SessionEvent.model_validate(dict(row._mapping)) for row in results]
    if not events:
        raise HTTPException(status_code=404, detail="Session not found")
    return events
