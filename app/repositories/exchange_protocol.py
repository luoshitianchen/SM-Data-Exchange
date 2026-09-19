"""交换协议仓储层。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange_protocol import ExchangeProtocol


async def get_protocol(session: AsyncSession, protocol_id: str) -> ExchangeProtocol | None:
    result = await session.execute(select(ExchangeProtocol).where(ExchangeProtocol.id == protocol_id))
    return result.scalar_one_or_none()


async def get_protocol_by_code(session: AsyncSession, code: str) -> ExchangeProtocol | None:
    result = await session.execute(select(ExchangeProtocol).where(ExchangeProtocol.code == code))
    return result.scalar_one_or_none()


async def list_protocols(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    status: str | None = None, keyword: str | None = None,
) -> list[ExchangeProtocol]:
    stmt = select(ExchangeProtocol).order_by(ExchangeProtocol.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(ExchangeProtocol.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(ExchangeProtocol.code.like(like), ExchangeProtocol.name.like(like)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_protocols(
    session: AsyncSession, status: str | None = None, keyword: str | None = None,
) -> int:
    stmt = select(func.count(ExchangeProtocol.id))
    if status:
        stmt = stmt.where(ExchangeProtocol.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(ExchangeProtocol.code.like(like), ExchangeProtocol.name.like(like)))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_protocol(session: AsyncSession, protocol: ExchangeProtocol) -> ExchangeProtocol:
    session.add(protocol)
    await session.commit()
    await session.refresh(protocol)
    return protocol


async def update_protocol(session: AsyncSession, protocol: ExchangeProtocol) -> ExchangeProtocol:
    await session.commit()
    await session.refresh(protocol)
    return protocol


async def delete_protocol(session: AsyncSession, protocol: ExchangeProtocol) -> None:
    await session.delete(protocol)
    await session.commit()
