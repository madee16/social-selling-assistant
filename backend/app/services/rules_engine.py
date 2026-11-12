import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.audit_log import AuditLog
from app.models.automation_rule import AutomationRule
from app.models.consent_record import ConsentRecord
from app.models.event import Event
from app.models.event_collection import EventCollection
from app.models.event_product_gap import EventProductGap
from app.models.inventory import Inventory
from app.models.marketplace_listing import MarketplaceListing
from app.models.notification import Notification
from app.models.product import Product
from app.models.product_score import ProductScore
from app.models.seller_trust_score import SellerTrustScore
from app.models.seo_data import SeoData
from app.models.seo_score import SeoScore

logger = logging.getLogger(__name__)


def _coerce_uuid(val: Any) -> uuid.UUID | None:
    if val is None:
        return None
    if isinstance(val, uuid.UUID):
        return val
    if isinstance(val, int):
        return uuid.UUID(int=val)
    if isinstance(val, str):
        val_str = val.strip()
        try:
            return uuid.UUID(val_str)
        except ValueError:
            if val_str.isdigit():
                return uuid.UUID(int=int(val_str))
            return uuid.uuid5(uuid.NAMESPACE_DNS, val_str)
    return None


class RulesEngine:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def evaluate_rule(
        self,
        rule: AutomationRule,
        event_payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        conditions = rule.conditions or {}
        if not self._match_conditions(conditions, event_payload):
            return []
        actions = rule.actions or {}
        return [{
            "rule_id": str(rule.id),
            "rule_name": rule.name,
            "event_type": rule.event_type,
            "actions": actions,
            "triggered_at": datetime.now(UTC).isoformat(),
        }]

    def _match_conditions(
        self,
        conditions: dict[str, Any],
        event_payload: dict[str, Any],
    ) -> bool:
        for key, expected in conditions.items():
            if key not in event_payload:
                return False
            actual = event_payload[key]
            if isinstance(expected, dict) and "operator" in expected:
                op = expected["operator"]
                val = expected["value"]
                if op == "gt":
                    if not (actual > val):
                        return False
                elif op == "gte":
                    if not (actual >= val):
                        return False
                elif op == "lt":
                    if not (actual < val):
                        return False
                elif op == "lte":
                    if not (actual <= val):
                        return False
                elif op == "contains":
                    if val not in str(actual):
                        return False
                elif op == "in":
                    if actual not in val:
                        return False
                else:
                    if actual != val:
                        return False
            elif actual != expected:
                return False
        return True

    async def process_event(
        self,
        event_type: str,
        event_payload: dict[str, Any],
        merchant_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(AutomationRule).where(
                AutomationRule.merchant_id == merchant_id,
                AutomationRule.is_active,
            )
        )
        rules = list(result.scalars().all())
        triggered = []
        for rule in rules:
            if rule.event_type == event_type:
                actions = await self.evaluate_rule(rule, event_payload)
                triggered.extend(actions)
        return triggered

    async def pause_marketplace_listings_for_product(self, product_id: uuid.UUID) -> int:
        """Pause any active/published marketplace listing for this product due to low stock."""
        result = await self.session.execute(
            select(MarketplaceListing).where(
                MarketplaceListing.product_id == product_id,
                MarketplaceListing.listing_status.in_(["active", "published", "syncing", "draft"]),
            )
        )
        listings = list(result.scalars().all())
        for listing in listings:
            listing.listing_status = "paused"
        if listings:
            await self.session.flush()
        return len(listings)

    async def create_low_stock_notification(
        self,
        user_id: uuid.UUID,
        product_name: str,
        quantity: int,
        threshold: int,
    ) -> Notification:
        """Create a notification alerting the merchant of low stock."""
        notif = Notification(
            user_id=user_id,
            type="low_stock",
            title=f"Alerte stock faible : {product_name}",
            message=f"Le stock restant pour {product_name} est de {quantity} (seuil : {threshold}). Les annonces de la marketplace ont été mises en pause.",
            link="/inventory",
        )
        self.session.add(notif)
        await self.session.flush()
        return notif

    async def trigger_low_stock_actions(
        self,
        product_id: uuid.UUID,
        store_id: uuid.UUID | None,
        merchant_user_id: uuid.UUID | None,
        quantity: int,
        threshold: int,
    ) -> dict[str, Any]:
        """Trigger low stock pause of marketplace listings and merchant notification."""
        paused_count = await self.pause_marketplace_listings_for_product(product_id)

        user_id = merchant_user_id
        product_name = str(product_id)
        prod = await self.session.get(Product, product_id)
        if prod:
            product_name = prod.name
            if not user_id:
                user_id = prod.user_id

        notif = None
        if user_id:
            notif = await self.create_low_stock_notification(user_id, product_name, quantity, threshold)

        return {
            "product_id": str(product_id),
            "paused_listings": paused_count,
            "notification_created": notif is not None,
            "quantity": quantity,
            "threshold": threshold,
        }

    async def check_inventory_alerts(self, product_id: uuid.UUID, store_id: uuid.UUID) -> dict[str, Any] | None:
        result = await self.session.execute(
            select(
                Inventory,
            ).where(
                Inventory.product_id == product_id,
                Inventory.store_id == store_id,
            )
        )
        inventory = result.scalar_one_or_none()
        if inventory and inventory.quantity <= inventory.low_stock_threshold:
            # 1. Update any active MarketplaceListing to paused
            # 2. Create a low-stock notification for the merchant
            prod = await self.session.get(Product, product_id)
            user_id = prod.user_id if prod else None
            p_name = prod.name if prod else str(product_id)

            await self.pause_marketplace_listings_for_product(product_id)
            if user_id:
                await self.create_low_stock_notification(
                    user_id=user_id,
                    product_name=p_name,
                    quantity=inventory.quantity,
                    threshold=inventory.low_stock_threshold,
                )

            return {
                "alert_type": "low_stock",
                "product_id": str(product_id),
                "store_id": str(store_id),
                "quantity": inventory.quantity,
                "threshold": inventory.low_stock_threshold,
                "triggered_at": datetime.now(UTC).isoformat(),
            }
        return None

    async def compute_product_scores(
        self,
        product_id: uuid.UUID,
        store_id: uuid.UUID,
    ) -> dict[str, float]:
        scores = {}
        result = await self.session.execute(
            select(SeoData).where(
                SeoData.entity_type == "product",
                SeoData.entity_id == product_id,
            )
        )
        seo = result.scalar_one_or_none()
        if seo:
            sr = await self.session.execute(
                select(SeoScore).where(SeoScore.seo_data_id == seo.id)
            )
            ss = sr.scalar_one_or_none()
            if ss and ss.overall_score is not None:
                scores["seo"] = ss.overall_score
        inv_result = await self.session.execute(
            select(Inventory).where(
                Inventory.product_id == product_id,
                Inventory.store_id == store_id,
            )
        )
        inv = inv_result.scalar_one_or_none()
        if inv:
            scores["stock_availability"] = min(1.0, inv.quantity / 100) if inv.quantity else 0.0
        return scores

    async def compute_seller_trust(self, seller_id: uuid.UUID) -> float:
        result = await self.session.execute(
            select(SellerTrustScore).where(
                SellerTrustScore.seller_id == seller_id
            ).order_by(SellerTrustScore.calculated_at.desc())
        )
        latest = result.scalar_one_or_none()
        return latest.score if latest else 0.0

    async def check_consent(self, buyer_id: uuid.UUID, consent_type: str) -> bool:
        result = await self.session.execute(
            select(ConsentRecord).where(
                ConsentRecord.buyer_id == buyer_id,
                ConsentRecord.consent_type == consent_type,
            ).order_by(ConsentRecord.created_at.desc())
        )
        record = result.scalar_one_or_none()
        return record.granted if record else False

    async def log_audit(
        self,
        user_id: uuid.UUID | None,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def create_event(
        self,
        event_type: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        event = Event(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def create_event_collection(
        self,
        event_id: uuid.UUID,
        collection_type: str,
        collection_id: str,
    ) -> EventCollection:
        ec = EventCollection(
            event_id=event_id,
            collection_type=collection_type,
            collection_id=collection_id,
        )
        self.session.add(ec)
        await self.session.flush()
        return ec

    async def create_product_gap(
        self,
        event_collection_id: uuid.UUID,
        product_id: uuid.UUID,
        gap_type: str,
    ) -> EventProductGap:
        gap = EventProductGap(
            event_collection_id=event_collection_id,
            product_id=product_id,
            gap_type=gap_type,
        )
        self.session.add(gap)
        await self.session.flush()
        return gap

    async def create_pending_approval(
        self,
        approval_type: str,
        entity_type: str,
        entity_id: str,
        title: str | None = None,
        description: str | None = None,
        requester_id: uuid.UUID | None = None,
    ) -> Approval:
        approval = Approval(
            approval_type=approval_type,
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            description=description,
            requester_id=requester_id or uuid.uuid4(),
        )
        self.session.add(approval)
        await self.session.flush()
        return approval

    async def respond_approval(
        self,
        approval_id: uuid.UUID,
        approved: bool,
        approver_id: uuid.UUID,
        rejection_reason: str | None = None,
    ) -> Approval:
        result = await self.session.execute(select(Approval).where(Approval.id == approval_id))
        approval = result.scalar_one_or_none()
        if approval:
            approval.status = "approved" if approved else "rejected"
            approval.approver_id = approver_id
            approval.rejection_reason = rejection_reason
            await self.session.flush()
        return approval

    async def get_pending_approvals(self, merchant_id: uuid.UUID) -> list[Approval]:
        result = await self.session.execute(
            select(Approval).where(
                Approval.entity_type == "merchant",
                Approval.entity_id == str(merchant_id),
                Approval.status == "pending",
            )
        )
        return list(result.scalars().all())

    async def get_active_rules(self, merchant_id: uuid.UUID) -> list[AutomationRule]:
        result = await self.session.execute(
            select(AutomationRule).where(
                AutomationRule.merchant_id == merchant_id,
                AutomationRule.is_active,
            )
        )
        return list(result.scalars().all())

    async def execute_automation(
        self,
        rule: AutomationRule,
        event_payload: dict[str, Any],
    ) -> dict[str, Any]:
        actions = rule.actions or {}
        rule.execution_count += 1
        rule.last_executed_at = datetime.now(UTC).replace(tzinfo=None)

        dispatched = []

        # 1. Action: pause_listings / pause_listing
        if actions.get("pause_listings") or actions.get("pause_listing"):
            prod_id_ref = event_payload.get("product_id") or actions.get("product_id")
            p_uuid = _coerce_uuid(prod_id_ref) if prod_id_ref else None
            if p_uuid:
                count = await self.pause_marketplace_listings_for_product(p_uuid)
                dispatched.append({"action": "pause_listings", "product_id": str(p_uuid), "count": count})

        # 2. Action: notify_merchant / notification / create_notification
        if actions.get("notify_merchant") or actions.get("notification") or actions.get("create_notification"):
            user_id = _coerce_uuid(event_payload.get("user_id") or event_payload.get("merchant_id") or rule.merchant_id)
            notif_data = actions.get("notification") or actions.get("create_notification") or {}
            if not isinstance(notif_data, dict):
                notif_data = {}
            title = notif_data.get("title") or f"Règle automatique déclenchée : {rule.name}"
            msg = notif_data.get("message") or f"La règle '{rule.name}' a été exécutée pour l'événement '{rule.event_type}'."
            notif_type = notif_data.get("type") or "automation"
            if user_id:
                notif = Notification(
                    user_id=user_id,
                    type=notif_type,
                    title=title,
                    message=msg,
                    link=notif_data.get("link", "/automations"),
                )
                self.session.add(notif)
                dispatched.append({"action": "notify_merchant", "title": title})

        # 3. Action: log_audit
        if actions.get("log_audit", True):
            await self.log_audit(
                user_id=_coerce_uuid(event_payload.get("user_id")),
                action=f"automation.{rule.event_type}",
                entity_type=event_payload.get("entity_type", "rule"),
                entity_id=event_payload.get("entity_id", str(rule.id)),
                details={"rule_id": str(rule.id), "rule_name": rule.name, "actions": actions},
            )
            dispatched.append({"action": "log_audit"})

        await self.session.flush()
        return {
            "rule_id": str(rule.id),
            "rule_name": rule.name,
            "executed": True,
            "actions": actions,
            "dispatched": dispatched,
            "executed_at": datetime.now(UTC).isoformat(),
        }

    async def get_scores_overview(
        self,
        store_id: uuid.UUID,
    ) -> dict[str, Any]:
        result = await self.session.execute(
            select(ProductScore).where(ProductScore.store_id == store_id)
        )
        scores = list(result.scalars().all())
        return {
            "store_id": str(store_id),
            "total_scores": len(scores),
            "average_score": sum(s.score for s in scores) / len(scores) if scores else 0.0,
            "scores": [{"product_id": str(s.product_id), "score": s.score, "type": s.score_type} for s in scores],
        }
