from __future__ import annotations

from sqlalchemy import BigInteger, Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Log(Base):
    __tablename__ = "logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    source_ip = Column(String(64), nullable=False)
    source_port = Column(Integer, nullable=True)
    destination_host = Column(String(255), nullable=True)
    destination_port = Column(Integer, nullable=True)
    protocol = Column(String(32), nullable=False)
    action = Column(String(32), nullable=True)
    inbound_tag = Column(String(64), nullable=True)
    outbound_tag = Column(String(64), nullable=True)
    email = Column(String(255), nullable=True, index=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Log id={self.id} {self.protocol} {self.source_ip}->{self.destination_host}>"
