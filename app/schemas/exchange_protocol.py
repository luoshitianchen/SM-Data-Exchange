"""交换协议 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ProtocolCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=128)
    protocol_type: Literal["sftp", "ftp", "http", "jdbc", "kafka", "api"] = "sftp"
    partner_id: str | None = Field(default=None, max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)
    description: str = Field(default="", max_length=2000)


class ProtocolUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    partner_id: str | None = Field(default=None, max_length=64)
    config: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=2000)


class ProtocolStatusUpdate(BaseModel):
    status: Literal["enabled", "disabled"]


class ProtocolResponse(BaseModel):
    id: str
    code: str
    name: str
    protocol_type: str
    partner_id: str | None
    config: dict[str, Any]
    status: str
    description: str
    created_at: datetime | str
    updated_at: datetime | str


class ProtocolListResponse(BaseModel):
    total: int
    items: list[ProtocolResponse]
