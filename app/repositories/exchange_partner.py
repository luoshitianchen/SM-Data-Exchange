"""交换伙伴仓储层。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange_partner import ExchangePartner


async def get_partner(session: AsyncSession, partner_id: str) -> ExchangePartner | None:
    result = await session.execute(select(ExchangePartner).where(ExchangePartner.id == partner_id))
    return result.scalar_one_or_none()


async def get_partner_by_code(session: AsyncSession, code: str) -> ExchangePartner | None:
    result = await session.execute(select(ExchangePartner).where(ExchangePartner.code == code))
    return result.scalar_one_or_none()


async def list_partners(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    status: str | None = None, keyword: str | None = None,
) -> list[ExchangePartner]:
    stmt = select(ExchangePartner).order_by(ExchangePartner.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(ExchangePartner.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(ExchangePartner.code.like(like), ExchangePartner.name.like(like)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_partners(
    session: AsyncSession, status: str | None = None, keyword: str | None = None,
) -> int:
    stmt = select(func.count(ExchangePartner.id))
    if status:
        stmt = stmt.where(ExchangePartner.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(ExchangePartner.code.like(like), ExchangePartner.name.like(like)))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_partner(session: AsyncSession, partner: ExchangePartner) -> ExchangePartner:
    session.add(partner)
    await session.commit()
    await session.refresh(partner)
    return partner


async def update_partner(session: AsyncSession, partner: ExchangePartner) -> ExchangePartner:
    await session.commit()
    await session.refresh(partner)
    return partner


async def delete_partner(session: AsyncSession, partner: ExchangePartner) -> None:
    await session.delete(partner)
    await session.commit()
