"""交换任务仓储层。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange_task import ExchangeTask


async def get_task(session: AsyncSession, task_id: str) -> ExchangeTask | None:
    result = await session.execute(select(ExchangeTask).where(ExchangeTask.id == task_id))
    return result.scalar_one_or_none()


async def get_task_by_code(session: AsyncSession, code: str) -> ExchangeTask | None:
    result = await session.execute(select(ExchangeTask).where(ExchangeTask.code == code))
    return result.scalar_one_or_none()


async def count_tasks_by_partner(session: AsyncSession, partner_id: str) -> int:
    result = await session.execute(
        select(func.count(ExchangeTask.id)).where(ExchangeTask.partner_id == partner_id)
    )
    return result.scalar_one()


async def count_tasks_by_protocol(session: AsyncSession, protocol_id: str) -> int:
    result = await session.execute(
        select(func.count(ExchangeTask.id)).where(ExchangeTask.protocol_id == protocol_id)
    )
    return result.scalar_one()


async def list_tasks(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    status: str | None = None, keyword: str | None = None,
) -> list[ExchangeTask]:
    stmt = select(ExchangeTask).order_by(ExchangeTask.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(ExchangeTask.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(ExchangeTask.code.like(like), ExchangeTask.name.like(like)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_tasks(
    session: AsyncSession, status: str | None = None, keyword: str | None = None,
) -> int:
    stmt = select(func.count(ExchangeTask.id))
    if status:
        stmt = stmt.where(ExchangeTask.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(ExchangeTask.code.like(like), ExchangeTask.name.like(like)))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_task(session: AsyncSession, task: ExchangeTask) -> ExchangeTask:
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def update_task(session: AsyncSession, task: ExchangeTask) -> ExchangeTask:
    await session.commit()
    await session.refresh(task)
    return task


async def delete_task(session: AsyncSession, task: ExchangeTask) -> None:
    await session.delete(task)
    await session.commit()
