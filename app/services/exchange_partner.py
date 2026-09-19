"""交换伙伴服务层：全生命周期管理。"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.exchange_partner import ExchangePartner
from app.repositories import exchange_partner as repo
from app.repositories import exchange_task as task_repo
from app.schemas.exchange_partner import PartnerCreate, PartnerUpdate
from app.services.audit import record_audit


def _partner_to_dict(p: ExchangePartner) -> dict:
    return {
        "id": p.id, "code": p.code, "name": p.name,
        "partner_type": p.partner_type, "endpoint": p.endpoint or "",
        "auth_type": p.auth_type, "contact_email": p.contact_email or "",
        "status": p.status, "description": p.description or "",
        "created_at": p.created_at.isoformat() if p.created_at else "",
        "updated_at": p.updated_at.isoformat() if p.updated_at else "",
    }


class PartnerService:
    @staticmethod
    async def list_partners(
        session: AsyncSession, limit: int = 100, offset: int = 0,
        status_filter: str | None = None, keyword: str | None = None,
    ) -> dict:
        partners = await repo.list_partners(
            session, limit=limit, offset=offset, status=status_filter, keyword=keyword
        )
        total = await repo.count_partners(session, status=status_filter, keyword=keyword)
        return {"total": total, "items": [_partner_to_dict(p) for p in partners]}

    @staticmethod
    async def get_partner(session: AsyncSession, partner_id: str) -> dict:
        partner = await repo.get_partner(session, partner_id)
        if not partner:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换伙伴不存在")
        return _partner_to_dict(partner)

    @staticmethod
    async def create_partner(session: AsyncSession, payload: PartnerCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if await repo.get_partner_by_code(session, payload.code):
            raise HTTPException(status.HTTP_409_CONFLICT, "伙伴编码已存在")
        partner = ExchangePartner(
            id=str(uuid.uuid4()), code=payload.code, name=payload.name,
            partner_type=payload.partner_type, endpoint=payload.endpoint or "",
            auth_type=payload.auth_type, contact_email=payload.contact_email or "",
            description=payload.description or "", status="active",
        )
        partner = await repo.create_partner(session, partner)
        await record_audit(session, "exchange.partner_created", "internal",
                           f"code={payload.code}", request)
        return _partner_to_dict(partner)

    @staticmethod
    async def update_partner(
        session: AsyncSession, partner_id: str, payload: PartnerUpdate, request: Request
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        partner = await repo.get_partner(session, partner_id)
        if not partner:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换伙伴不存在")
        if payload.name is not None:
            partner.name = payload.name
        if payload.endpoint is not None:
            partner.endpoint = payload.endpoint
        if payload.auth_type is not None:
            partner.auth_type = payload.auth_type
        if payload.contact_email is not None:
            partner.contact_email = payload.contact_email
        if payload.description is not None:
            partner.description = payload.description
        partner = await repo.update_partner(session, partner)
        await record_audit(session, "exchange.partner_updated", "internal",
                           f"partner_id={partner_id}", request)
        return _partner_to_dict(partner)

    @staticmethod
    async def update_status(
        session: AsyncSession, partner_id: str, new_status: str, request: Request
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        partner = await repo.get_partner(session, partner_id)
        if not partner:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换伙伴不存在")
        partner.status = new_status
        partner = await repo.update_partner(session, partner)
        await record_audit(session, "exchange.partner_status_changed", "internal",
                           f"partner_id={partner_id} status={new_status}", request)
        return _partner_to_dict(partner)

    @staticmethod
    async def delete_partner(session: AsyncSession, partner_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        partner = await repo.get_partner(session, partner_id)
        if not partner:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换伙伴不存在")
        # 引用完整性：存在关联交换任务时禁止删除
        used = await task_repo.count_tasks_by_partner(session, partner_id)
        if used > 0:
            raise HTTPException(status.HTTP_409_CONFLICT, f"该伙伴被 {used} 个交换任务引用，禁止删除")
        code = partner.code
        await repo.delete_partner(session, partner)
        await record_audit(session, "exchange.partner_deleted", "internal",
                           f"partner_id={partner_id} code={code}", request)
        return {"deleted": True, "id": partner_id, "deleted_at": datetime.now(UTC).isoformat()}
