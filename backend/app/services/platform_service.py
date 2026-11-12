import uuid

from sqlalchemy import select

from app.models.ai_message import AIMessage
from app.models.ai_session import AISession
from app.models.ai_tool_call import AIToolCall
from app.models.approval import Approval
from app.models.audit_log import AuditLog
from app.models.automation_rule import AutomationRule
from app.models.collection import Collection
from app.models.consent_record import ConsentRecord
from app.models.event import Event
from app.models.event_collection import EventCollection
from app.models.event_product_gap import EventProductGap
from app.models.marketplace_listing import MarketplaceListing
from app.models.product_score import ProductScore
from app.models.seller_trust_score import SellerTrustScore
from app.models.seo_data import SeoData
from app.models.seo_score import SeoScore
from app.models.store import Store
from app.schemas.ai import (
    AIMessageCreate,
    AISessionCreate,
    AISessionUpdate,
    AIToolCallCreate,
)
from app.schemas.collection import CollectionCreate, CollectionUpdate
from app.schemas.events import (
    EventCollectionCreate,
    EventCreate,
    EventProductGapCreate,
    EventUpdate,
)
from app.schemas.governance import (
    ApprovalCreate,
    ApprovalUpdate,
    AuditLogCreate,
    AutomationRuleCreate,
    AutomationRuleUpdate,
    ConsentRecordCreate,
    ConsentRecordUpdate,
)
from app.schemas.marketplace import MarketplaceListingCreate, MarketplaceListingUpdate
from app.schemas.scoring import (
    ProductScoreCreate,
    ProductScoreUpdate,
    SellerTrustScoreCreate,
    SellerTrustScoreUpdate,
)
from app.schemas.seo import SeoDataCreate, SeoDataUpdate, SeoScoreCreate, SeoScoreUpdate
from app.services import crud


def _merchant_of(db, user_id):
    return crud.get_merchant_for_user(db, user_id)


async def merchant_id_of(db, user_id) -> uuid.UUID | None:
    merchant = await _merchant_of(db, user_id)
    return merchant.id if merchant else None


async def list_collections(db, user_id, page=1, page_size=20):
    merchant = await _merchant_of(db, user_id)
    where = Collection.merchant_id == merchant.id if merchant else None
    return await crud.list_records(db, Collection, where=where, page=page, page_size=page_size)


async def get_collection(db, collection_id, user_id):
    merchant = await _merchant_of(db, user_id)
    where = (
        (Collection.id == collection_id) & (Collection.merchant_id == merchant.id)
        if merchant
        else Collection.id == collection_id
    )
    return await crud.get_record(db, Collection, where)


async def create_collection(db, user_id, data: CollectionCreate) -> Collection | None:
    merchant_id = await merchant_id_of(db, user_id)
    if not merchant_id:
        return None
    return await crud.create_record(db, Collection, {"merchant_id": merchant_id, **data.model_dump()})


async def update_collection(db, record, data: CollectionUpdate):
    return await crud.update_record(db, record, data.model_dump(exclude_unset=True))


async def delete_collection(db, record):
    await crud.delete_record(db, record)


async def list_seo_data(db, page=1, page_size=20, entity_type: str | None = None):
    where = SeoData.entity_type == entity_type if entity_type else None
    return await crud.list_records(db, SeoData, where=where, page=page, page_size=page_size)


async def get_seo_data(db, seo_id):
    return await crud.get_record(db, SeoData, SeoData.id == seo_id)


async def create_seo_data(db, data: SeoDataCreate):
    return await crud.create_record(db, SeoData, data.model_dump())


async def update_seo_data(db, record, data: SeoDataUpdate):
    return await crud.update_record(db, record, data.model_dump(exclude_unset=True))


async def delete_seo_data(db, record):
    await crud.delete_record(db, record)


async def list_seo_scores(db, seo_data_id: uuid.UUID, page=1, page_size=20):
    return await crud.list_records(
        db, SeoScore, where=SeoScore.seo_data_id == seo_data_id, page=page, page_size=page_size
    )


async def get_seo_score(db, score_id):
    return await crud.get_record(db, SeoScore, SeoScore.id == score_id)


async def create_seo_score(db, seo_data_id, data: SeoScoreCreate):
    return await crud.create_record(
        db, SeoScore, {"seo_data_id": seo_data_id, "calculated_at": None, **data.model_dump()}
    )


async def update_seo_score(db, record, data: SeoScoreUpdate):
    return await crud.update_record(db, record, data.model_dump(exclude_unset=True))


async def delete_seo_score(db, record):
    await crud.delete_record(db, record)


async def list_marketplace_listings(db, product_id, user_id, page=1, page_size=20):
    from app.models.product import Product

    owned = await crud.get_record(db, Product, (Product.id == product_id) & (Product.user_id == user_id))
    if not owned:
        return None
    return await crud.list_records(
        db, MarketplaceListing, where=MarketplaceListing.product_id == product_id, page=page, page_size=page_size
    )


async def get_marketplace_listing(db, listing_id):
    return await crud.get_record(db, MarketplaceListing, MarketplaceListing.id == listing_id)


async def create_marketplace_listing(db, product_id, user_id, data: MarketplaceListingCreate):
    from app.models.product import Product

    owned = await crud.get_record(db, Product, (Product.id == product_id) & (Product.user_id == user_id))
    if not owned:
        return None
    return await crud.create_record(
        db, MarketplaceListing, {"product_id": product_id, **data.model_dump()}
    )


async def update_marketplace_listing(db, record, data: MarketplaceListingUpdate):
    return await crud.update_record(db, record, data.model_dump(exclude_unset=True))


async def delete_marketplace_listing(db, record):
    await crud.delete_record(db, record)


async def list_product_scores(db, product_id, page=1, page_size=20):
    return await crud.list_records(
        db, ProductScore, where=ProductScore.product_id == product_id, page=page, page_size=page_size
    )


async def get_product_score(db, score_id):
    return await crud.get_record(db, ProductScore, ProductScore.id == score_id)


async def create_product_score(db, product_id, data: ProductScoreCreate):
    return await crud.create_record(
        db, ProductScore, {"product_id": product_id, "calculated_at": None, **data.model_dump()}
    )


async def update_product_score(db, record, data: ProductScoreUpdate):
    return await crud.update_record(db, record, data.model_dump(exclude_unset=True))


async def delete_product_score(db, record):
    await crud.delete_record(db, record)


async def list_seller_trust(db, user_id, page=1, page_size=20):
    merchant = await _merchant_of(db, user_id)
    where = SellerTrustScore.seller_id == merchant.id if merchant else None
    return await crud.list_records(db, SellerTrustScore, where=where, page=page, page_size=page_size)


async def get_seller_trust(db, trust_id):
    return await crud.get_record(db, SellerTrustScore, SellerTrustScore.id == trust_id)


async def create_seller_trust(db, user_id, data: SellerTrustScoreCreate):
    merchant_id = await merchant_id_of(db, user_id)
    if not merchant_id:
        return None
    return await crud.create_record(
        db, SellerTrustScore, {"seller_id": merchant_id, "calculated_at": None, **data.model_dump()}
    )


async def update_seller_trust(db, record, data: SellerTrustScoreUpdate):
    return await crud.update_record(db, record, data.model_dump(exclude_unset=True))


async def delete_seller_trust(db, record):
    await crud.delete_record(db, record)


async def user_store_ids(db, user_id) -> list[uuid.UUID]:
    merchant = await _merchant_of(db, user_id)
    if not merchant:
        return []
    result = await db.execute(select(Store.id).where(Store.merchant_id == merchant.id))
    return list(result.scalars().all())


async def list_ai_sessions(db, user_id, page=1, page_size=20, status: str | None = None):
    store_ids = await user_store_ids(db, user_id)
    where = AISession.store_id.in_(store_ids) if store_ids else AISession.store_id.is_(None)
    if status:
        where = where & (AISession.status == status)
    return await crud.list_records(db, AISession, where=where, page=page, page_size=page_size)


async def get_ai_session(db, session_id, user_id):
    store_ids = await user_store_ids(db, user_id)
    if not store_ids:
        return None
    return await crud.get_record(
        db, AISession, (AISession.id == session_id) & (AISession.store_id.in_(store_ids))
    )


async def create_ai_session(db, user_id, data: AISessionCreate):
    return await crud.create_record(db, AISession, {**data.model_dump(), "total_messages": 0})


async def update_ai_session(db, record, data: AISessionUpdate):
    return await crud.update_record(db, record, data.model_dump(exclude_unset=True))


async def delete_ai_session(db, record):
    await crud.delete_record(db, record)


async def list_ai_messages(db, session_id, page=1, page_size=20):
    return await crud.list_records(
        db, AIMessage, where=AIMessage.session_id == session_id, page=page, page_size=page_size
    )


async def get_ai_message(db, message_id):
    return await crud.get_record(db, AIMessage, AIMessage.id == message_id)


async def create_ai_message(db, session_id, data: AIMessageCreate):
    message = await crud.create_record(
        db, AIMessage, {"session_id": session_id, **data.model_dump()}
    )
    session = await crud.get_record(db, AISession, AISession.id == session_id)
    if session:
        session.total_messages = (session.total_messages or 0) + 1
        await db.commit()
    return message


async def list_ai_tool_calls(db, session_id, page=1, page_size=20):
    return await crud.list_records(
        db, AIToolCall, where=AIToolCall.session_id == session_id, page=page, page_size=page_size
    )


async def get_ai_tool_call(db, call_id):
    return await crud.get_record(db, AIToolCall, AIToolCall.id == call_id)


async def create_ai_tool_call(db, session_id, message_id, data: AIToolCallCreate):
    return await crud.create_record(
        db, AIToolCall, {"session_id": session_id, "message_id": message_id, **data.model_dump()}
    )


async def list_approvals(db, user_id, page=1, page_size=20, status: str | None = None):
    where = (Approval.requester_id == user_id) | (Approval.approver_id == user_id)
    if status:
        where = where & (Approval.status == status)
    return await crud.list_records(db, Approval, where=where, page=page, page_size=page_size)


async def get_approval(db, approval_id):
    return await crud.get_record(db, Approval, Approval.id == approval_id)


async def create_approval(db, user_id, data: ApprovalCreate):
    return await crud.create_record(
        db, Approval, {"requester_id": user_id, **data.model_dump()}
    )


async def update_approval(db, record, data: ApprovalUpdate):
    return await crud.update_record(db, record, data.model_dump(exclude_unset=True))


async def list_automation_rules(db, user_id, page=1, page_size=20, active_only: bool = False):
    merchant = await _merchant_of(db, user_id)
    where = AutomationRule.merchant_id == merchant.id if merchant else None
    if where is not None and active_only:
        where = where & (AutomationRule.is_active.is_(True))
    return await crud.list_records(db, AutomationRule, where=where, page=page, page_size=page_size)


async def get_automation_rule(db, rule_id):
    return await crud.get_record(db, AutomationRule, AutomationRule.id == rule_id)


async def create_automation_rule(db, user_id, data: AutomationRuleCreate):
    merchant_id = await merchant_id_of(db, user_id)
    if not merchant_id:
        return None
    return await crud.create_record(db, AutomationRule, {"merchant_id": merchant_id, **data.model_dump()})


async def update_automation_rule(db, record, data: AutomationRuleUpdate):
    return await crud.update_record(db, record, data.model_dump(exclude_unset=True))


async def delete_automation_rule(db, record):
    await crud.delete_record(db, record)


async def list_consent_records(db, buyer_id, page=1, page_size=20):
    return await crud.list_records(
        db, ConsentRecord, where=ConsentRecord.buyer_id == buyer_id, page=page, page_size=page_size
    )


async def get_consent_record(db, record_id):
    return await crud.get_record(db, ConsentRecord, ConsentRecord.id == record_id)


async def create_consent_record(db, data: ConsentRecordCreate):
    return await crud.create_record(db, ConsentRecord, data.model_dump())


async def update_consent_record(db, record, data: ConsentRecordUpdate):
    return await crud.update_record(db, record, data.model_dump(exclude_unset=True))


async def list_audit_logs(db, user_id, page=1, page_size=20):
    return await crud.list_records(db, AuditLog, where=AuditLog.user_id == user_id, page=page, page_size=page_size)


async def create_audit_log(db, user_id, data: AuditLogCreate):
    return await crud.create_record(db, AuditLog, {"user_id": user_id, **data.model_dump()})


async def list_events(db, page=1, page_size=20, event_type: str | None = None):
    where = Event.event_type == event_type if event_type else None
    return await crud.list_records(db, Event, where=where, page=page, page_size=page_size)


async def get_event(db, event_id):
    return await crud.get_record(db, Event, Event.id == event_id)


async def create_event(db, data: EventCreate):
    return await crud.create_record(db, Event, data.model_dump())


async def update_event(db, record, data: EventUpdate):
    return await crud.update_record(db, record, data.model_dump(exclude_unset=True))


async def delete_event(db, record):
    await crud.delete_record(db, record)


async def list_event_collections(db, event_id, page=1, page_size=20):
    return await crud.list_records(
        db, EventCollection, where=EventCollection.event_id == event_id, page=page, page_size=page_size
    )


async def create_event_collection(db, event_id, data: EventCollectionCreate):
    return await crud.create_record(db, EventCollection, {"event_id": event_id, **data.model_dump()})


async def list_event_product_gaps(db, collection_id, page=1, page_size=20):
    return await crud.list_records(
        db, EventProductGap, where=EventProductGap.event_collection_id == collection_id, page=page, page_size=page_size
    )


async def create_event_product_gap(db, collection_id, data: EventProductGapCreate):
    return await crud.create_record(
        db, EventProductGap, {"event_collection_id": collection_id, **data.model_dump()}
    )
