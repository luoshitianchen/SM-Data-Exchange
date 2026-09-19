"""数据交换伙伴模型。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class ExchangePartner(Base):
    """交换伙伴：对接外部数据提供方/接收方。"""

    __tablename__ = "exchange_partners"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    partner_type: Mapped[str] = mapped_column(String(16), default="peer", index=True)
    endpoint: Mapped[str] = mapped_column(String(512), default="")
    auth_type: Mapped[str] = mapped_column(String(16), default="none")
    contact_email: Mapped[str] = mapped_column(String(256), default="")
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
