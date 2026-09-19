"""交换伙伴管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.exchange_partner import PartnerCreate, PartnerStatusUpdate, PartnerUpdate
from app.services.exchange_partner import PartnerService

router = APIRouter(prefix="/api/exchange/partners", tags=["exchange-partners"])


@router.get("")
async def list_partners(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None, max_length=128),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await PartnerService.list_partners(
        session, limit=limit, offset=offset, status_filter=status_filter, keyword=keyword
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_partner(
    payload: PartnerCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await PartnerService.create_partner(session, payload, request)


@router.get("/{partner_id}")
async def get_partner(
    partner_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await PartnerService.get_partner(session, partner_id)


@router.patch("/{partner_id}")
async def update_partner(
    partner_id: str, payload: PartnerUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await PartnerService.update_partner(session, partner_id, payload, request)


@router.patch("/{partner_id}/status")
async def update_partner_status(
    partner_id: str, payload: PartnerStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await PartnerService.update_status(session, partner_id, payload.status, request)


@router.delete("/{partner_id}", status_code=status.HTTP_200_OK)
async def delete_partner(
    partner_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await PartnerService.delete_partner(session, partner_id, request)
