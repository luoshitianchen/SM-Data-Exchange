"""交换协议服务层：全生命周期管理。"""
from __future__ import annotations

import json
import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.exchange_protocol import ExchangeProtocol
from app.repositories import exchange_partner as partner_repo
from app.repositories import exchange_protocol as repo
from app.repositories import exchange_task as task_repo
from app.schemas.exchange_protocol import ProtocolCreate, ProtocolUpdate
from app.services.audit import record_audit


def _protocol_to_dict(p: ExchangeProtocol) -> dict:
    try:
        config = json.loads(p.config or "{}")
    except (json.JSONDecodeError, TypeError):
        config = {}
    return {
        "id": p.id, "code": p.code, "name": p.name,
        "protocol_type": p.protocol_type, "partner_id": p.partner_id,
        "config": config, "status": p.status, "description": p.description or "",
        "created_at": p.created_at.isoformat() if p.created_at else "",
        "updated_at": p.updated_at.isoformat() if p.updated_at else "",
    }


class ProtocolService:
    @staticmethod
    async def list_protocols(
        session: AsyncSession, limit: int = 100, offset: int = 0,
        status_filter: str | None = None, keyword: str | None = None,
    ) -> dict:
        protocols = await repo.list_protocols(
            session, limit=limit, offset=offset, status=status_filter, keyword=keyword
        )
        total = await repo.count_protocols(session, status=status_filter, keyword=keyword)
        return {"total": total, "items": [_protocol_to_dict(p) for p in protocols]}

    @staticmethod
    async def get_protocol(session: AsyncSession, protocol_id: str) -> dict:
        protocol = await repo.get_protocol(session, protocol_id)
        if not protocol:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换协议不存在")
        return _protocol_to_dict(protocol)

    @staticmethod
    async def create_protocol(
        session: AsyncSession, payload: ProtocolCreate, request: Request
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if await repo.get_protocol_by_code(session, payload.code):
            raise HTTPException(status.HTTP_409_CONFLICT, "协议编码已存在")
        # 引用完整性：若绑定伙伴则必须存在
        if payload.partner_id is not None:
            partner = await partner_repo.get_partner(session, payload.partner_id)
            if not partner:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "绑定的交换伙伴不存在")
        protocol = ExchangeProtocol(
            id=str(uuid.uuid4()), code=payload.code, name=payload.name,
            protocol_type=payload.protocol_type, partner_id=payload.partner_id,
            config=json.dumps(payload.config or {}, ensure_ascii=False),
            description=payload.description or "", status="enabled",
        )
        protocol = await repo.create_protocol(session, protocol)
        await record_audit(session, "exchange.protocol_created", "internal",
                           f"code={payload.code}", request)
        return _protocol_to_dict(protocol)

    @staticmethod
    async def update_protocol(
        session: AsyncSession, protocol_id: str, payload: ProtocolUpdate, request: Request
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        protocol = await repo.get_protocol(session, protocol_id)
        if not protocol:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换协议不存在")
        if payload.partner_id is not None:
            partner = await partner_repo.get_partner(session, payload.partner_id)
            if not partner:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "绑定的交换伙伴不存在")
            protocol.partner_id = payload.partner_id
        if payload.name is not None:
            protocol.name = payload.name
        if payload.config is not None:
            protocol.config = json.dumps(payload.config, ensure_ascii=False)
        if payload.description is not None:
            protocol.description = payload.description
        protocol = await repo.update_protocol(session, protocol)
        await record_audit(session, "exchange.protocol_updated", "internal",
                           f"protocol_id={protocol_id}", request)
        return _protocol_to_dict(protocol)

    @staticmethod
    async def update_status(
        session: AsyncSession, protocol_id: str, new_status: str, request: Request
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        protocol = await repo.get_protocol(session, protocol_id)
        if not protocol:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换协议不存在")
        protocol.status = new_status
        protocol = await repo.update_protocol(session, protocol)
        await record_audit(session, "exchange.protocol_status_changed", "internal",
                           f"protocol_id={protocol_id} status={new_status}", request)
        return _protocol_to_dict(protocol)

    @staticmethod
    async def delete_protocol(session: AsyncSession, protocol_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        protocol = await repo.get_protocol(session, protocol_id)
        if not protocol:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换协议不存在")
        used = await task_repo.count_tasks_by_protocol(session, protocol_id)
        if used > 0:
            raise HTTPException(status.HTTP_409_CONFLICT, f"该协议被 {used} 个交换任务引用，禁止删除")
        code = protocol.code
        await repo.delete_protocol(session, protocol)
        await record_audit(session, "exchange.protocol_deleted", "internal",
                           f"protocol_id={protocol_id} code={code}", request)
        return {"deleted": True, "id": protocol_id}
