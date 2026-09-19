"""交换伙伴 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PartnerCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=128)
    partner_type: Literal["peer", "supplier", "receiver"] = "peer"
    endpoint: str = Field(default="", max_length=512)
    auth_type: Literal["none", "token", "mtls", "basic"] = "none"
    contact_email: str = Field(default="", max_length=256)
    description: str = Field(default="", max_length=2000)


class PartnerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    endpoint: str | None = Field(default=None, max_length=512)
    auth_type: Literal["none", "token", "mtls", "basic"] | None = None
    contact_email: str | None = Field(default=None, max_length=256)
    description: str | None = Field(default=None, max_length=2000)


class PartnerStatusUpdate(BaseModel):
    status: Literal["active", "disabled"]


class PartnerResponse(BaseModel):
    id: str
    code: str
    name: str
    partner_type: str
    endpoint: str
    auth_type: str
    contact_email: str
    status: str
    description: str
    created_at: datetime | str
    updated_at: datetime | str


class PartnerListResponse(BaseModel):
    total: int
    items: list[PartnerResponse]
