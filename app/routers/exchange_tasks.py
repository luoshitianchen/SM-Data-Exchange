"""交换任务管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.exchange_task import TaskCreate, TaskStatusUpdate, TaskUpdate
from app.services.exchange_task import TaskService

router = APIRouter(prefix="/api/exchange/tasks", tags=["exchange-tasks"])


@router.get("")
async def list_tasks(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None, max_length=128),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TaskService.list_tasks(
        session, limit=limit, offset=offset, status_filter=status_filter, keyword=keyword
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TaskService.create_task(session, payload, request)


@router.get("/{task_id}")
async def get_task(
    task_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TaskService.get_task(session, task_id)


@router.patch("/{task_id}")
async def update_task(
    task_id: str, payload: TaskUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TaskService.update_task(session, task_id, payload, request)


@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: str, payload: TaskStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TaskService.change_status(session, task_id, payload.status, request)


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await TaskService.delete_task(session, task_id, request)
