"""交换任务服务层：编排与状态机管理。"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.exchange_task import ExchangeTask
from app.repositories import exchange_partner as partner_repo
from app.repositories import exchange_protocol as protocol_repo
from app.repositories import exchange_task as repo
from app.schemas.exchange_task import TaskCreate, TaskUpdate
from app.services.audit import record_audit

# 任务状态机：允许的合法迁移
_TASK_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"running"},
    "running": {"paused", "completed", "failed"},
    "paused": {"running", "failed"},
    "completed": set(),
    "failed": {"running"},
}


def _task_to_dict(t: ExchangeTask) -> dict:
    try:
        stats = json.loads(t.stats or "{}")
    except (json.JSONDecodeError, TypeError):
        stats = {}
    return {
        "id": t.id, "code": t.code, "name": t.name,
        "partner_id": t.partner_id, "protocol_id": t.protocol_id,
        "direction": t.direction, "schedule_cron": t.schedule_cron or "",
        "status": t.status,
        "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
        "stats": stats,
        "created_at": t.created_at.isoformat() if t.created_at else "",
        "updated_at": t.updated_at.isoformat() if t.updated_at else "",
    }


class TaskService:
    @staticmethod
    async def list_tasks(
        session: AsyncSession, limit: int = 100, offset: int = 0,
        status_filter: str | None = None, keyword: str | None = None,
    ) -> dict:
        tasks = await repo.list_tasks(
            session, limit=limit, offset=offset, status=status_filter, keyword=keyword
        )
        total = await repo.count_tasks(session, status=status_filter, keyword=keyword)
        return {"total": total, "items": [_task_to_dict(t) for t in tasks]}

    @staticmethod
    async def get_task(session: AsyncSession, task_id: str) -> dict:
        task = await repo.get_task(session, task_id)
        if not task:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换任务不存在")
        return _task_to_dict(task)

    @staticmethod
    async def create_task(session: AsyncSession, payload: TaskCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if await repo.get_task_by_code(session, payload.code):
            raise HTTPException(status.HTTP_409_CONFLICT, "任务编码已存在")
        # 引用完整性：伙伴与协议必须存在
        if not await partner_repo.get_partner(session, payload.partner_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "交换伙伴不存在")
        if not await protocol_repo.get_protocol(session, payload.protocol_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "交换协议不存在")
        task = ExchangeTask(
            id=str(uuid.uuid4()), code=payload.code, name=payload.name,
            partner_id=payload.partner_id, protocol_id=payload.protocol_id,
            direction=payload.direction, schedule_cron=payload.schedule_cron or "",
            status="draft", stats="{}",
        )
        task = await repo.create_task(session, task)
        await record_audit(session, "exchange.task_created", "internal",
                           f"code={payload.code}", request)
        return _task_to_dict(task)

    @staticmethod
    async def update_task(
        session: AsyncSession, task_id: str, payload: TaskUpdate, request: Request
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        task = await repo.get_task(session, task_id)
        if not task:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换任务不存在")
        if task.status not in {"draft", "paused"}:
            raise HTTPException(status.HTTP_409_CONFLICT, "仅草稿或暂停状态任务允许编辑")
        if payload.name is not None:
            task.name = payload.name
        if payload.schedule_cron is not None:
            task.schedule_cron = payload.schedule_cron
        task = await repo.update_task(session, task)
        await record_audit(session, "exchange.task_updated", "internal",
                           f"task_id={task_id}", request)
        return _task_to_dict(task)

    @staticmethod
    async def change_status(
        session: AsyncSession, task_id: str, new_status: str, request: Request
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        task = await repo.get_task(session, task_id)
        if not task:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换任务不存在")
        allowed = _TASK_TRANSITIONS.get(task.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"状态不允许从 {task.status} 迁移到 {new_status}",
            )
        task.status = new_status
        if new_status in {"running", "completed", "failed"}:
            task.last_run_at = datetime.now(UTC)
        if new_status in {"completed", "failed"}:
            stats = json.loads(task.stats or "{}")
            stats["last_finish"] = new_status
            task.stats = json.dumps(stats, ensure_ascii=False)
        task = await repo.update_task(session, task)
        await record_audit(session, "exchange.task_status_changed", "internal",
                           f"task_id={task_id} status={task.status}", request)
        return _task_to_dict(task)

    @staticmethod
    async def delete_task(session: AsyncSession, task_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        task = await repo.get_task(session, task_id)
        if not task:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换任务不存在")
        if task.status == "running":
            raise HTTPException(status.HTTP_409_CONFLICT, "运行中任务禁止删除，请先暂停或结束")
        code = task.code
        await repo.delete_task(session, task)
        await record_audit(session, "exchange.task_deleted", "internal",
                           f"task_id={task_id} code={code}", request)
        return {"deleted": True, "id": task_id}
