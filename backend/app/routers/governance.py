import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.events import (
    EventCollectionCreate,
    EventCollectionResponse,
    EventCreate,
    EventProductGapCreate,
    EventProductGapResponse,
    EventResponse,
    EventUpdate,
)
from app.schemas.governance import (
    ApprovalCreate,
    ApprovalResponse,
    ApprovalUpdate,
    AuditLogCreate,
    AuditLogResponse,
    AutomationRuleCreate,
    AutomationRuleResponse,
    AutomationRuleUpdate,
    ConsentRecordCreate,
    ConsentRecordResponse,
    ConsentRecordUpdate,
)
from app.services import platform_service
from app.services.orchestrator import Orchestrator, _coerce_uuid
from app.services.rules_engine import RulesEngine
from app.services.webhook_service import is_whatsapp_enabled, send_whatsapp_message

router = APIRouter(prefix="/api", tags=["governance & events"])


def _page_result(result, schema):
    return {
        "items": [schema.model_validate(item).model_dump() for item in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


# ---- Approvals ----


@router.get("/approvals")
async def list_approvals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_approvals(db, current_user.id, page, page_size, status)
    return _page_result(result, ApprovalResponse)


@router.post("/approvals", response_model=ApprovalResponse, status_code=201)
async def create_approval(
    data: ApprovalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await platform_service.create_approval(db, current_user.id, data)


@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_approval(db, approval_id)
    if not record:
        raise HTTPException(status_code=404, detail="Approval not found")
    return record


@router.put("/approvals/{approval_id}", response_model=ApprovalResponse)
async def update_approval(
    approval_id: uuid.UUID,
    data: ApprovalUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_approval(db, approval_id)
    if not record:
        raise HTTPException(status_code=404, detail="Approval not found")

    if data.status in ("approved", "rejected") and not data.approver_id:
        data.approver_id = current_user.id

    updated = await platform_service.update_approval(db, record, data)

    # Dispatch governance approval actions
    if data.status in ("approved", "rejected"):
        # 1. Audit log entry via rules_engine.log_audit()
        rules_engine = RulesEngine(db)
        await rules_engine.log_audit(
            user_id=current_user.id,
            action=f"approval.{updated.status}",
            entity_type="approval",
            entity_id=str(updated.id),
            details={
                "status": updated.status,
                "approval_type": updated.approval_type,
                "rejection_reason": updated.rejection_reason,
                "meta_data": updated.meta_data,
            },
        )

        # 2. Dispatch follow-up buyer message to active AI session and/or WhatsApp
        meta = updated.meta_data or {}
        session_id_str = meta.get("session_id")
        buyer_phone = meta.get("buyer_phone")
        discount = meta.get("proposed_discount_percent")
        prod_name = meta.get("product_name")

        if updated.status == "approved":
            buyer_msg = (
                f"Bonne nouvelle ! Le commerçant a validé votre demande de réduction"
                + (f" de {discount:.0f}%" if discount else "")
                + (f" sur {prod_name}" if prod_name else "")
                + ". Votre commande peut désormais être confirmée avec ce tarif préférentiel."
            )
        else:
            rejection = updated.rejection_reason or (meta.get("reason") if meta else None) or "Non spécifiée"
            buyer_msg = (
                f"Le commerçant a examiné votre proposition de réduction mais n'a pas pu l'accepter"
                + f" (motif : {rejection})"
                + ". N'hésitez pas si vous avez d'autres questions !"
            )

        # Log outbound AIMessage in buyer's active session if session_id is recorded
        if session_id_str:
            sess_uuid = _coerce_uuid(session_id_str)
            if sess_uuid:
                orchestrator = Orchestrator(db)
                await orchestrator.add_message(
                    session_id=sess_uuid,
                    role="assistant",
                    content=buyer_msg,
                )

        # Trigger WhatsApp outbound sender if buyer_phone is known and integration is enabled
        if buyer_phone and is_whatsapp_enabled():
            background_tasks.add_task(
                send_whatsapp_message,
                to=buyer_phone,
                text=buyer_msg,
                phone_number_id=None,
                access_token=None,
            )

        await db.commit()

    return updated


# ---- Automation rules ----


@router.get("/automation-rules")
async def list_automation_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_automation_rules(
        db, current_user.id, page, page_size, active_only
    )
    return _page_result(result, AutomationRuleResponse)


@router.post("/automation-rules", response_model=AutomationRuleResponse, status_code=201)
async def create_automation_rule(
    data: AutomationRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.create_automation_rule(db, current_user.id, data)
    if not record:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return record


@router.put("/automation-rules/{rule_id}", response_model=AutomationRuleResponse)
async def update_automation_rule(
    rule_id: uuid.UUID,
    data: AutomationRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_automation_rule(db, rule_id)
    if not record:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    return await platform_service.update_automation_rule(db, record, data)


@router.delete("/automation-rules/{rule_id}", status_code=204)
async def delete_automation_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_automation_rule(db, rule_id)
    if not record:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    await platform_service.delete_automation_rule(db, record)


# ---- Consent records ----


@router.get("/buyers/{buyer_id}/consent-records")
async def list_consent_records(
    buyer_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_consent_records(db, buyer_id, page, page_size)
    return _page_result(result, ConsentRecordResponse)


@router.post("/consent-records", response_model=ConsentRecordResponse, status_code=201)
async def create_consent_record(
    data: ConsentRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await platform_service.create_consent_record(db, data)


@router.put("/consent-records/{record_id}", response_model=ConsentRecordResponse)
async def update_consent_record(
    record_id: uuid.UUID,
    data: ConsentRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_consent_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Consent record not found")
    return await platform_service.update_consent_record(db, record, data)


# ---- Audit logs ----


@router.get("/audit-logs")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_audit_logs(db, current_user.id, page, page_size)
    return _page_result(result, AuditLogResponse)


@router.post("/audit-logs", response_model=AuditLogResponse, status_code=201)
async def create_audit_log(
    data: AuditLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await platform_service.create_audit_log(db, current_user.id, data)


# ---- Events ----


@router.get("/events")
async def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    event_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_events(db, page, page_size, event_type)
    return _page_result(result, EventResponse)


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_event(db, event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Event not found")
    return record


@router.post("/events", response_model=EventResponse, status_code=201)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await platform_service.create_event(db, data)


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: uuid.UUID,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_event(db, event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Event not found")
    return await platform_service.update_event(db, record, data)


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_event(db, event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Event not found")
    await platform_service.delete_event(db, record)


@router.get("/events/{event_id}/collections")
async def list_event_collections(
    event_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_event_collections(db, event_id, page, page_size)
    return _page_result(result, EventCollectionResponse)


@router.post("/events/{event_id}/collections", response_model=EventCollectionResponse, status_code=201)
async def create_event_collection(
    event_id: uuid.UUID,
    data: EventCollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await platform_service.create_event_collection(db, event_id, data)


@router.get("/event-collections/{collection_id}/gaps")
async def list_event_product_gaps(
    collection_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_event_product_gaps(db, collection_id, page, page_size)
    return _page_result(result, EventProductGapResponse)


@router.post("/event-collections/{collection_id}/gaps", response_model=EventProductGapResponse, status_code=201)
async def create_event_product_gap(
    collection_id: uuid.UUID,
    data: EventProductGapCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await platform_service.create_event_product_gap(db, collection_id, data)
