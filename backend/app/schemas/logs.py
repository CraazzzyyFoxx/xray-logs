from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LogRecord(BaseModel):
    id: int
    timestamp: datetime = Field(serialization_alias="ts")
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
