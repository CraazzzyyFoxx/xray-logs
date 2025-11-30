from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LogRecord(BaseModel):
    id: int
    timestamp: datetime = Field(serialization_alias="ts")
    user_id: Optional[int]
    source_ip: str
    source_port: int
    destination_host: str
    destination_port: Optional[int]
    protocol: Optional[str]
    action: Optional[str]
    inbound_tag: Optional[str]
    outbound_tag: Optional[str]
    email: Optional[str]


class LogsResponse(BaseModel):
    total: int
    items: list[LogRecord]


class LogStats(BaseModel):
    total: int
    unique_users: int
    protocols: dict[str, int]
    tags: dict[str, int]


class SessionSummary(BaseModel):
    user_id: int
    email: Optional[str]
    session_group_id: int
    started_at: datetime
    ended_at: datetime
    events: int


class SessionEvent(BaseModel):
    id: int
    email: Optional[str]
    event_time: datetime
    source_ip: str
    source_port: int
    protocol: Optional[str]
    destination: Optional[str]
    destination_port: Optional[int]
    inbound_tag: Optional[str]
    outbound_tag: Optional[str]
    action: Optional[str]
    session_group_id: int


class SiteVisit(BaseModel):
    site: str
    first_visit: datetime
    last_visit: datetime
    hits_count: int


class UserProfile(BaseModel):
    user_id: int
    email: Optional[str]
    sessions: list[SessionSummary]
    top_sites: list[SiteVisit]
