"""交换任务 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=128)
    partner_id: str = Field(min_length=1, max_length=64)
    protocol_id: str = Field(min_length=1, max_length=64)
    direction: Literal["import", "export"] = "import"
    schedule_cron: str = Field(default="", max_length=128)


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    schedule_cron: str | None = Field(default=None, max_length=128)


class TaskStatusUpdate(BaseModel):
    """任务状态机迁移请求：目标状态。"""

    status: Literal["running", "paused", "completed", "failed"]


class TaskResponse(BaseModel):
    id: str
    code: str
    name: str
    partner_id: str
    protocol_id: str
    direction: str
    schedule_cron: str
    status: str
    last_run_at: datetime | None = None
    stats: dict[str, Any]
    created_at: datetime | str
    updated_at: datetime | str


class TaskListResponse(BaseModel):
    total: int
    items: list[TaskResponse]
