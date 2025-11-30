from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class LogOut(BaseModel):
    id: int
    timestamp: datetime
    source_ip: str
    source_port: Optional[int] = None
    destination_host: Optional[str] = None
    destination_port: Optional[int] = None
    protocol: str
    action: Optional[str] = None
    inbound_tag: Optional[str] = None
    outbound_tag: Optional[str] = None
    email: Optional[str] = None

    model_config = {"from_attributes": True}


class LogListResponse(BaseModel):
    total: int
    items: list[LogOut]


class LogStats(BaseModel):
    total: int = Field(..., description="Total logs available")
    protocol_counts: Dict[str, int]
    tag_counts: Dict[str, int]
    unique_users: int
    available_protocols: list[str]
    available_tags: list[str]
