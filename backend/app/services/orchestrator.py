import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_message import AIMessage
from app.models.ai_session import AISession
from app.models.ai_tool_call import AIToolCall
from app.models.approval import Approval
from app.models.automation_rule import AutomationRule
from app.models.buyer import Buyer
from app.models.inventory import Inventory
from app.models.merchant import Merchant
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.product_score import ProductScore
from app.models.product_variant import ProductVariant
from app.models.seller_trust_score import SellerTrustScore
from app.models.user import User

logger = logging.getLogger(__name__)


def _coerce_uuid(val: Any) -> uuid.UUID | None:
    """Safely coerce int, string or UUID to a valid UUID object."""
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


TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "check_inventory",
            "description": "Checks real-time stock quantity and availability for a product before promising it to a buyer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "Unique identifier of the product to check.",
                    },
                    "variant": {
                        "type": "string",
                        "description": "Optional product variant name or SKU (e.g. 'Red', 'XL').",
                    },
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Validates stock and creates the Order and OrderItem records in PostgreSQL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "buyer_phone": {
                        "type": "string",
                        "description": "Buyer's phone number for order tracking and confirmation.",
                    },
                    "items": {
                        "type": "array",
                        "description": "List of items to order, each containing product_id (or product_name) and quantity.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_id": {
                                    "type": "integer",
                                    "description": "ID of the product.",
                                },
                                "product_name": {
                                    "type": "string",
                                    "description": "Optional name of the product.",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "Quantity to order.",
                                    "default": 1,
                                },
                            },
                            "required": ["quantity"],
                        },
                    },
                    "delivery_address": {
                        "type": "string",
                        "description": "Physical shipping/delivery address for the order.",
                    },
                    "payment_method": {
                        "type": "string",
                        "description": "Payment method, defaults to COD (Cash on Delivery).",
                        "default": "COD",
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Optional full name of the customer.",
                    },
                },
                "required": ["buyer_phone", "items", "delivery_address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_merchant_approval",
            "description": "Triggers the Governance Flow by creating a pending Approval record in the database when a buyer negotiates/haggles for a discount or bulk deal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for the discount or deal approval request.",
                    },
                    "proposed_discount_percent": {
                        "type": "number",
                        "description": "Proposed discount percentage requested by the buyer (e.g., 10.0 for 10%).",
                    },
                    "product_id": {
                        "type": "integer",
                        "description": "ID of the product the discount applies to.",
                    },
                    "buyer_phone": {
                        "type": "string",
                        "description": "Phone number of the buyer negotiating the deal.",
                    },
                },
                "required": ["reason", "proposed_discount_percent", "product_id", "buyer_phone"],
            },
        },
    },
]


class Orchestrator:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_ai_session(
        self,
        store_id: uuid.UUID | None = None,
        buyer_id: uuid.UUID | None = None,
        intent: str | None = None,
    ) -> AISession:
        session = AISession(
            store_id=store_id,
            buyer_id=buyer_id,
            intent=intent,
        )
        self.session.add(session)
        await self.session.flush()
        logger.info("AI session created: %s", session.id)
        return session

    async def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        confidence: float | None = None,
    ) -> AIMessage:
        message = AIMessage(
            session_id=session_id,
            role=role,
            content=content,
            confidence=confidence,
            sequence=await self._get_next_sequence(session_id),
        )
        self.session.add(message)
        await self.session.flush()
        await self._update_session_total_messages(session_id)
        return message

    async def record_tool_call(
        self,
        session_id: uuid.UUID,
        message_id: uuid.UUID,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> AIToolCall:
        tool_call = AIToolCall(
            session_id=session_id,
            message_id=message_id,
            tool_name=tool_name,
            arguments=arguments,
        )
        self.session.add(tool_call)
        await self.session.flush()
        return tool_call

    async def complete_tool_call(
        self,
        tool_call_id: uuid.UUID,
        result: dict[str, Any] | None = None,
        status: str = "completed",
    ) -> AIToolCall:
        tool_call = await self.session.get(AIToolCall, tool_call_id)
        if tool_call:
            tool_call.result = result
            tool_call.status = status
            await self.session.flush()
        return tool_call

    async def create_approval(
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
        approval = await self.session.get(Approval, approval_id)
        if approval:
            approval.status = "approved" if approved else "rejected"
            approval.approver_id = approver_id
            approval.rejection_reason = rejection_reason
            await self.session.flush()
        return approval

    async def create_automation_rule(
        self,
        merchant_id: uuid.UUID,
        name: str,
        event_type: str,
        conditions: dict[str, Any] | None = None,
        actions: dict[str, Any] | None = None,
        priority: int = 0,
    ) -> AutomationRule:
        rule = AutomationRule(
            merchant_id=merchant_id,
            name=name,
            event_type=event_type,
            conditions=conditions,
            actions=actions,
            priority=priority,
        )
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def update_product_score(
        self,
        product_id: uuid.UUID,
        store_id: uuid.UUID,
        score: float,
        score_type: str,
        detail: dict[str, Any] | None = None,
    ) -> ProductScore:
        ps = ProductScore(
            product_id=product_id,
            store_id=store_id,
            score=score,
            score_type=score_type,
            detail=detail,
        )
        self.session.add(ps)
        await self.session.flush()
        return ps

    async def update_seller_trust_score(
        self,
        seller_id: uuid.UUID,
        score: float,
        components: dict[str, Any] | None = None,
        level: str = "bronze",
    ) -> SellerTrustScore:
        st = SellerTrustScore(
            seller_id=seller_id,
            score=score,
            components=components,
            level=level,
        )
        self.session.add(st)
        await self.session.flush()
        return st

    async def check_inventory(
        self,
        product_id: uuid.UUID,
        store_id: uuid.UUID,
    ) -> Inventory | None:
        result = await self.session.execute(
            select(Inventory).where(
                Inventory.product_id == product_id,
                Inventory.store_id == store_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_rules(self, merchant_id: uuid.UUID) -> list[AutomationRule]:
        result = await self.session.execute(
            select(AutomationRule).where(
                AutomationRule.merchant_id == merchant_id,
                AutomationRule.is_active,
            )
        )
        return list(result.scalars().all())

    async def _get_next_sequence(self, session_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.max(AIMessage.sequence)).where(
                AIMessage.session_id == session_id
            )
        )
        max_seq = result.scalar()
        return (max_seq or 0) + 1

    async def _update_session_total_messages(self, session_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(func.count(AIMessage.id)).where(
                AIMessage.session_id == session_id
            )
        )
        total = result.scalar()
        session = await self.session.get(AISession, session_id)
        if session:
            session.total_messages = total
            await self.session.flush()

    async def get_session(self, session_id: uuid.UUID) -> AISession | None:
        return await self.session.get(AISession, session_id)

    async def get_messages(self, session_id: uuid.UUID) -> list[AIMessage]:
        result = await self.session.execute(
            select(AIMessage).where(
                AIMessage.session_id == session_id
            ).order_by(AIMessage.sequence)
        )
        return list(result.scalars().all())

    # ---------------------------------------------------------------------------
    # Product Resolution Helper
    # ---------------------------------------------------------------------------

    async def _resolve_product(
        self,
        product_ref: Any,
        merchant_id: uuid.UUID | None = None,
        store_id: uuid.UUID | None = None,
    ) -> Product | None:
        if product_ref is None:
            return None

        # 1. Match by coerced UUID
        p_uuid = _coerce_uuid(product_ref)
        if p_uuid:
            prod = await self.session.get(Product, p_uuid)
            if prod:
                return prod

        # 2. Match by exact or partial name if string
        if isinstance(product_ref, str) and not product_ref.isdigit():
            stmt = select(Product).where(Product.name.ilike(product_ref))
            if store_id:
                stmt = stmt.where(Product.store_id == store_id)
            res = await self.session.execute(stmt)
            prod = res.scalars().first()
            if prod:
                return prod

            stmt_fuzzy = select(Product).where(Product.name.ilike(f"%{product_ref}%"))
            if store_id:
                stmt_fuzzy = stmt_fuzzy.where(Product.store_id == store_id)
            res_fuzzy = await self.session.execute(stmt_fuzzy)
            prod = res_fuzzy.scalars().first()
            if prod:
                return prod

        # 3. Match by position if integer or digit string
        stmt_all = select(Product)
        if store_id:
            stmt_all = stmt_all.where(Product.store_id == store_id)
        stmt_all = stmt_all.order_by(Product.created_at.asc())
        res_all = await self.session.execute(stmt_all)
        prods = list(res_all.scalars().all())

        try:
            idx = int(product_ref)
            if 1 <= idx <= len(prods):
                return prods[idx - 1]
            if 0 <= idx < len(prods):
                return prods[idx]
        except (ValueError, TypeError):
            pass

        return None

    # ---------------------------------------------------------------------------
    # Tool Handlers
    # ---------------------------------------------------------------------------

    async def _handle_check_inventory(
        self,
        arguments: dict[str, Any],
        merchant_id: uuid.UUID | None,
        store_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        product_ref = arguments.get("product_id")
        variant = arguments.get("variant")

        if product_ref is None:
            return {
                "error": "Missing required argument 'product_id'",
                "available": False,
                "quantity": 0,
                "success": False,
            }

        product = await self._resolve_product(product_ref, merchant_id, store_id)
        if not product:
            return {
                "error": f"Product '{product_ref}' not found",
                "product_id": str(product_ref),
                "available": False,
                "quantity": 0,
                "success": False,
            }

        # Check variant if provided
        if variant:
            var_stmt = select(ProductVariant).where(
                ProductVariant.product_id == product.id,
                (ProductVariant.name.ilike(variant) | (ProductVariant.sku == variant)),
            )
            var_res = await self.session.execute(var_stmt)
            pv = var_res.scalar_one_or_none()
            if pv:
                available_qty = max(0, pv.quantity)
                return {
                    "product_id": str(product.id),
                    "product_name": product.name,
                    "variant": pv.name or variant,
                    "sku": pv.sku,
                    "available": available_qty > 0,
                    "quantity": available_qty,
                    "price": float(product.price),
                    "low_stock": available_qty <= 5,
                    "success": True,
                }

        # Check Inventory table
        inv_stmt = select(Inventory).where(Inventory.product_id == product.id)
        if store_id:
            inv_stmt = inv_stmt.where(Inventory.store_id == store_id)
        inv_res = await self.session.execute(inv_stmt)
        inv = inv_res.scalars().first()

        if inv is not None:
            available_qty = max(0, inv.quantity - (inv.reserved_quantity or 0))
            is_low_stock = inv.quantity <= inv.low_stock_threshold
        else:
            available_qty = max(0, product.stock_quantity)
            is_low_stock = product.stock_quantity <= 5

        return {
            "product_id": str(product.id),
            "product_name": product.name,
            "available": available_qty > 0,
            "quantity": available_qty,
            "price": float(product.price),
            "low_stock": is_low_stock,
            "variant": variant,
            "success": True,
        }

    async def _handle_create_order(
        self,
        arguments: dict[str, Any],
        merchant_id: uuid.UUID | None,
        store_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        buyer_phone = arguments.get("buyer_phone")
        items = arguments.get("items", [])
        delivery_address = arguments.get("delivery_address")
        payment_method = arguments.get("payment_method", "COD")
        customer_name = arguments.get("customer_name")

        if not buyer_phone:
            return {"error": "Missing required field 'buyer_phone'", "success": False}
        if not items or not isinstance(items, list):
            return {"error": "Missing or invalid 'items' list", "success": False}
        if not delivery_address:
            return {"error": "Missing required field 'delivery_address'", "success": False}

        # 1. Validate all items and stock
        resolved_items = []
        total_amount = 0.0

        for item in items:
            prod_ref = item.get("product_id") or item.get("product_name")
            try:
                qty = int(item.get("quantity", 1))
            except (ValueError, TypeError):
                qty = 1

            if qty <= 0:
                return {"error": f"Quantity must be greater than 0 for item {item}", "success": False}

            prod = await self._resolve_product(prod_ref, merchant_id, store_id)
            if not prod:
                return {"error": f"Product '{prod_ref}' not found", "success": False}

            # Check stock
            inv_stmt = select(Inventory).where(Inventory.product_id == prod.id)
            if store_id:
                inv_stmt = inv_stmt.where(Inventory.store_id == store_id)
            inv_res = await self.session.execute(inv_stmt)
            inv = inv_res.scalars().first()

            available = (inv.quantity - (inv.reserved_quantity or 0)) if inv else prod.stock_quantity
            if available < qty:
                return {
                    "error": f"Insufficient stock for '{prod.name}'. Requested: {qty}, Available: {available}",
                    "success": False,
                }

            unit_price = float(prod.price)
            subtotal = round(unit_price * qty, 2)
            total_amount += subtotal
            resolved_items.append((prod, inv, qty, unit_price, subtotal))

        # 2. Resolve merchant user_id
        user_id = None
        if merchant_id:
            m_res = await self.session.execute(
                select(Merchant).where((Merchant.id == merchant_id) | (Merchant.user_id == merchant_id))
            )
            merch = m_res.scalar_one_or_none()
            if merch:
                user_id = merch.user_id
            else:
                u_res = await self.session.execute(select(User).where(User.id == merchant_id))
                u = u_res.scalar_one_or_none()
                if u:
                    user_id = u.id

        if not user_id and resolved_items:
            user_id = resolved_items[0][0].user_id

        if not user_id:
            user_id = uuid.uuid4()

        # 3. Find or create Buyer
        b_res = await self.session.execute(select(Buyer).where(Buyer.phone == buyer_phone))
        buyer = b_res.scalars().first()
        if not buyer:
            buyer = Buyer(
                phone=buyer_phone,
                name=customer_name or f"Client {buyer_phone}",
            )
            self.session.add(buyer)
            await self.session.flush()

        # 4. Create Order
        order = Order(
            user_id=user_id,
            buyer_id=buyer.id,
            store_id=store_id,
            customer_name=customer_name or buyer.name or f"Client {buyer_phone}",
            customer_phone=buyer_phone,
            customer_address=delivery_address,
            status="pending",
            total_amount=round(total_amount, 2),
        )
        self.session.add(order)
        await self.session.flush()

        # 5. Add OrderItems and deduct stock
        low_stock_alerts = []
        for prod, inv, qty, unit_price, subtotal in resolved_items:
            oi = OrderItem(
                order_id=order.id,
                product_id=prod.id,
                quantity=qty,
                unit_price=unit_price,
                subtotal=subtotal,
            )
            self.session.add(oi)

            # Deduct stock
            prod.stock_quantity = max(0, prod.stock_quantity - qty)
            threshold = 5
            cur_qty = prod.stock_quantity
            if inv:
                inv.quantity = max(0, inv.quantity - qty)
                threshold = inv.low_stock_threshold
                cur_qty = inv.quantity

            if cur_qty <= threshold:
                low_stock_alerts.append((prod, cur_qty, threshold))

        await self.session.flush()

        # 6. Low stock action dispatching
        from app.services.rules_engine import RulesEngine
        rules_engine = RulesEngine(self.session)
        for prod, cur_qty, threshold in low_stock_alerts:
            await rules_engine.trigger_low_stock_actions(
                product_id=prod.id,
                store_id=store_id,
                merchant_user_id=user_id,
                quantity=cur_qty,
                threshold=threshold,
            )

        return {
            "order_id": str(order.id),
            "status": order.status,
            "total_amount": float(order.total_amount),
            "items_count": len(resolved_items),
            "customer_phone": buyer_phone,
            "delivery_address": delivery_address,
            "payment_method": payment_method,
            "success": True,
        }

    async def _handle_request_merchant_approval(
        self,
        arguments: dict[str, Any],
        merchant_id: uuid.UUID | None,
        store_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        reason = arguments.get("reason", "")
        try:
            proposed_discount_percent = float(arguments.get("proposed_discount_percent", 0.0))
        except (ValueError, TypeError):
            proposed_discount_percent = 0.0

        product_ref = arguments.get("product_id")
        buyer_phone = arguments.get("buyer_phone", "")

        if product_ref is None:
            return {"error": "Missing required field 'product_id'", "success": False}

        product = await self._resolve_product(product_ref, merchant_id, store_id)
        prod_id_str = str(product.id) if product else str(product_ref)
        prod_name = product.name if product else f"Product {product_ref}"

        requester_id = merchant_id or uuid.uuid4()

        approval = Approval(
            approval_type="discount",
            entity_type="product",
            entity_id=prod_id_str,
            title=f"Discount Request: {proposed_discount_percent:.1f}% for {prod_name}",
            description=reason or f"Buyer with phone {buyer_phone} requested {proposed_discount_percent}% discount",
            requester_id=requester_id,
            status="pending",
            meta_data={
                "product_id": prod_id_str,
                "product_name": prod_name,
                "proposed_discount_percent": proposed_discount_percent,
                "buyer_phone": buyer_phone,
                "reason": reason,
                "session_id": str(session_id) if session_id else None,
                "store_id": str(store_id) if store_id else None,
                "merchant_id": str(merchant_id) if merchant_id else None,
            },
        )
        self.session.add(approval)
        await self.session.flush()

        return {
            "approval_id": str(approval.id),
            "status": "pending",
            "approval_type": approval.approval_type,
            "product_id": prod_id_str,
            "proposed_discount_percent": proposed_discount_percent,
            "buyer_phone": buyer_phone,
            "message": f"Demande d'approbation transmise au commerçant ({proposed_discount_percent}% de remise demandée).",
            "success": True,
        }

    # ---------------------------------------------------------------------------
    # Main Tool Execution Dispatcher
    # ---------------------------------------------------------------------------

    async def execute_tool_call(
        self,
        session_id: int | str | uuid.UUID,
        tool_name: str,
        arguments: dict[str, Any],
        merchant_id: int | str | uuid.UUID,
        store_id: int | str | uuid.UUID | None = None,
        message_id: uuid.UUID | str | None = None,
    ) -> dict[str, Any]:
        s_uuid = _coerce_uuid(session_id) or uuid.uuid4()
        m_uuid = _coerce_uuid(merchant_id) or uuid.uuid4()
        store_uuid = _coerce_uuid(store_id)

        # 1. Ensure AISession exists to prevent foreign key errors
        ai_session = await self.session.get(AISession, s_uuid)
        if not ai_session:
            ai_session = AISession(id=s_uuid, store_id=store_uuid, status="active")
            self.session.add(ai_session)
            await self.session.flush()

        # 2. Ensure AIMessage exists for FK
        msg_uuid = _coerce_uuid(message_id)
        msg = await self.session.get(AIMessage, msg_uuid) if msg_uuid else None

        if not msg:
            res = await self.session.execute(
                select(AIMessage).where(AIMessage.session_id == s_uuid).order_by(AIMessage.sequence.desc())
            )
            msg = res.scalars().first()

        if not msg:
            msg = await self.add_message(
                session_id=s_uuid,
                role="assistant",
                content=f"[Tool Call] Invoking {tool_name}",
            )

        # 3. Log invocation using record_tool_call
        tool_call = await self.record_tool_call(
            session_id=s_uuid,
            message_id=msg.id,
            tool_name=tool_name,
            arguments=arguments,
        )

        # 4. Execute corresponding database/service logic
        try:
            if tool_name == "check_inventory":
                result = await self._handle_check_inventory(arguments, m_uuid, store_uuid)
            elif tool_name == "create_order":
                result = await self._handle_create_order(arguments, m_uuid, store_uuid, s_uuid)
            elif tool_name == "request_merchant_approval":
                result = await self._handle_request_merchant_approval(arguments, m_uuid, store_uuid, s_uuid)
            else:
                result = {"error": f"Unknown tool: '{tool_name}'", "success": False}
        except Exception as exc:
            logger.exception("Error executing tool %s: %s", tool_name, exc)
            result = {"error": str(exc), "success": False}

        # 5. Complete record using complete_tool_call
        is_success = result.get("success", True) and not result.get("error")
        await self.complete_tool_call(
            tool_call_id=tool_call.id,
            result=result,
            status="completed" if is_success else "failed",
        )

        return result
