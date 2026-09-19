"""交换协议管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.exchange_protocol import ProtocolCreate, ProtocolStatusUpdate, ProtocolUpdate
from app.services.exchange_protocol import ProtocolService

router = APIRouter(prefix="/api/exchange/protocols", tags=["exchange-protocols"])


@router.get("")
async def list_protocols(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None, max_length=128),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ProtocolService.list_protocols(
        session, limit=limit, offset=offset, status_filter=status_filter, keyword=keyword
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_protocol(
    payload: ProtocolCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ProtocolService.create_protocol(session, payload, request)


@router.get("/{protocol_id}")
async def get_protocol(
    protocol_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ProtocolService.get_protocol(session, protocol_id)


@router.patch("/{protocol_id}")
async def update_protocol(
    protocol_id: str, payload: ProtocolUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ProtocolService.update_protocol(session, protocol_id, payload, request)


@router.patch("/{protocol_id}/status")
async def update_protocol_status(
    protocol_id: str, payload: ProtocolStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ProtocolService.update_status(session, protocol_id, payload.status, request)


@router.delete("/{protocol_id}", status_code=status.HTTP_200_OK)
async def delete_protocol(
    protocol_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await ProtocolService.delete_protocol(session, protocol_id, request)
