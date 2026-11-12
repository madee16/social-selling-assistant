"""Seed the database with demo data for the supervisor demo."""
import asyncio
import uuid
from datetime import datetime, timedelta

from app.config import settings
from app.database import async_session
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.order import Order, OrderItem
from app.models.merchant import Merchant
from app.models.store import Store
from app.models.store_member import StoreMember
from app.models.buyer import Buyer
from app.models.attribute_def import AttributeDef
from app.models.product_attribute import ProductAttribute
from app.models.product_variant import ProductVariant
from app.models.inventory import Inventory
from app.models.price import Price
from app.models.seo_data import SeoData
from app.models.collection import Collection
from app.models.marketplace_listing import MarketplaceListing
from app.models.product_score import ProductScore
from app.models.seller_trust_score import SellerTrustScore
from app.models.ai_session import AISession
from app.models.ai_message import AIMessage
from app.models.ai_tool_call import AIToolCall
from app.models.audit_log import AuditLog
from app.models.event import Event
from app.models.event_collection import EventCollection
from app.models.event_product_gap import EventProductGap
from app.models.consent_record import ConsentRecord
from app.models.approval import Approval
from app.models.automation_rule import AutomationRule
from app.models.notification import Notification
from app.utils.security import hash_password
from sqlalchemy import select


async def seed():
    async with async_session() as db:
        # 1. Demo user (reuse if it already exists)
        result = await db.execute(select(User).where(User.email == "demo@socialselling.tn"))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                id=uuid.uuid4(),
                email="demo@socialselling.tn",
                password_hash=hash_password("demo123"),
                company_name="Tunisia Handmade",
                phone="+216 50 000 000",
            )
            db.add(user)
            await db.flush()
        print(f"User: {user.email} / demo123")

        # 2. Merchant (reuse if it already exists for this user)
        result = await db.execute(select(Merchant).where(Merchant.user_id == user.id))
        merchant = result.scalar_one_or_none()
        if merchant is None:
            merchant = Merchant(
                id=uuid.uuid4(),
                user_id=user.id,
                company_name="Tunisia Handmade",
                verification_status="verified",
                trust_score_ref=0.85,
            )
            db.add(merchant)
            await db.flush()
        print(f"Merchant: {merchant.company_name}")

        # 3. Store (reuse if the slug already exists)
        result = await db.execute(select(Store).where(Store.slug == "tunisia-handmade"))
        store = result.scalar_one_or_none()
        if store is None:
            store = Store(
                id=uuid.uuid4(),
                merchant_id=merchant.id,
                slug="tunisia-handmade",
                name="Tunisia Handmade Store",
                domain="tunisia-handmade.tn",
                settings={"currency": "TND", "language": "fr"},
                status="active",
            )
            db.add(store)
            await db.flush()
        print(f"Store: {store.name}")

        # 4. Store Member
        member = StoreMember(
            id=uuid.uuid4(),
            store_id=store.id,
            user_id=user.id,
            role="admin",
        )
        db.add(member)
        await db.flush()

        # 5. Buyers
        buyers = []
        buyer_data = [
            ("Amira Ben Ali", "+216 50 111 111", "Tunis", "amira@example.com"),
            ("Karim Jebali", "+216 52 222 222", "Sfax", "karim@example.com"),
            ("Sarra Makhlouf", "+216 55 333 333", "Sousse", "sarra@example.com"),
            ("Mehdi Gharbi", None, None, None),
            ("Lamia Trabelsi", "+216 58 444 444", "Nabeul", "lamia@example.com"),
        ]
        for name, phone, addr, email in buyer_data:
            existing = None
            if email:
                result = await db.execute(select(Buyer).where(Buyer.email == email))
                existing = result.scalar_one_or_none()
            if existing is None:
                result = await db.execute(select(Buyer).where(Buyer.name == name))
                existing = result.scalar_one_or_none()
            if existing is not None:
                buyers.append(existing)
                continue
            b = Buyer(
                id=uuid.uuid4(),
                email=email,
                phone=phone,
                name=name,
                preferences={"language": "fr", "notifications": True},
            )
            db.add(b)
            await db.flush()
            buyers.append(b)
        print(f"Buyers: {len(buyers)} ready")

        # 6. Categories
        cats = {}
        for name in ["Artisanat", "Vêtements", "Accessoires", "Maison & Déco", "Alimentaire"]:
            result = await db.execute(select(Category).where(Category.user_id == user.id, Category.name == name))
            c = result.scalar_one_or_none()
            if c is None:
                c = Category(user_id=user.id, store_id=store.id, name=name)
                db.add(c)
                await db.flush()
            else:
                c.store_id = store.id
            cats[name] = c

        # 7. Attribute Definitions
        attr_defs = {}
        attr_data = [
            ("Material", "text", ["Terre cuite", "Zellige", "Cuir", "Argent", "Laine", "Coton"], True, True),
            ("Color", "text", ["Bleu", "Blanc", "Vert", "Rouge", "Naturel"], True, True),
            ("Size", "text", ["S", "M", "L", "XL", "Unique"], False, True),
            ("Style", "text", ["Traditionnel", "Moderne", "Bohème", "Classique"], False, False),
            ("Origin", "text", ["Tunisie", "Maroc", "France"], True, False),
        ]
        for name, atype, values, req, filt in attr_data:
            ad = AttributeDef(
                merchant_id=merchant.id,
                name=name,
                attribute_type=atype,
                values=values,
                is_required=req,
                is_filterable=filt,
            )
            db.add(ad)
            await db.flush()
            attr_defs[name] = ad

        # 8. Products
        products_data = [
            ("Poterie traditionnelle", "Pot en terre cuite fait main", 45.00, cats["Artisanat"], 20, "Terre cuite", "Bleu", "Unique", "Traditionnel", "Tunisie"),
            ("Zellige marocain", "Carreau de zellige artisanal (lot de 10)", 120.00, cats["Artisanat"], 15, "Zellige", "Blanc", "Unique", "Traditionnel", "Maroc"),
            ("Keswa féminine", "Robe traditionnelle brodée", 250.00, cats["Vêtements"], 10, "Coton", "Bleu", "L", "Traditionnel", "Tunisie"),
            ("Fouta de plage", "Serviette en coton tissé", 35.00, cats["Vêtements"], 50, "Coton", "Vert", "M", "Bohème", "Tunisie"),
            ("Sac en cuir", "Sac à main en cuir véritable", 180.00, cats["Accessoires"], 12, "Cuir", "Naturel", "M", "Classique", "Maroc"),
            ("Boucles d'oreilles", "Bijoux en argent filigrane", 65.00, cats["Accessoires"], 30, "Argent", "Blanc", "Unique", "Traditionnel", "Tunisie"),
            ("Huile d'olive", "Huile d'olive extra vierge 1L", 28.00, cats["Alimentaire"], 100, "Olive", "Vert", "Unique", "Classique", "Tunisie"),
            ("Miel de cactus", "Miel de figue de barbarie 500g", 35.00, cats["Alimentaire"], 40, "Naturel", "Ambre", "Unique", "Traditionnel", "Tunisie"),
            ("Tapis berbère", "Tapis tissé main laine naturelle", 450.00, cats["Maison & Déco"], 5, "Laine", "Naturel", "XL", "Traditionnel", "Maroc"),
            ("Lampes en cuivre", "Lampe artisanale en cuivre martelé", 150.00, cats["Maison & Déco"], 8, "Cuivre", "Naturel", "Unique", "Classique", "Tunisie"),
        ]
        products = []
        for name, desc, price, cat, stock, mat, color, size, style, origin in products_data:
            result = await db.execute(select(Product).where(Product.user_id == user.id, Product.name == name))
            p = result.scalar_one_or_none()
            is_new = p is None
            if is_new:
                p = Product(
                    user_id=user.id,
                    category_id=cat.id,
                    store_id=store.id,
                    name=name,
                    description=desc,
                    price=price,
                    stock_quantity=stock,
                    is_active=True,
                )
                db.add(p)
                await db.flush()
            else:
                p.category_id = cat.id
                p.store_id = store.id
            products.append(p)

            if not is_new:
                continue

            # ProductAttributes
            attr_values = [mat, color, size, style, origin]
            for i, val in enumerate(attr_values):
                pa = ProductAttribute(
                    product_id=p.id,
                    attribute_def_id=list(attr_defs.values())[i].id,
                    value=val,
                )
                db.add(pa)
                await db.flush()

            # ProductVariant
            sku = f"SKU-{p.id.hex[:8].upper()}"
            pv = ProductVariant(
                product_id=p.id,
                sku=sku,
                name=f"{name} - {size}",
                options={"material": mat, "color": color, "size": size},
                quantity=stock,
            )
            db.add(pv)
            await db.flush()

            # Inventory
            inv = Inventory(
                product_id=p.id,
                store_id=store.id,
                quantity=stock,
                reserved_quantity=0,
                low_stock_threshold=5,
            )
            db.add(inv)
            await db.flush()

            # Price
            pr = Price(
                product_id=p.id,
                store_id=store.id,
                amount=price,
                currency="TND",
            )
            db.add(pr)
            await db.flush()

            # SeoData
            sd = SeoData(
                entity_type="product",
                entity_id=p.id,
                title=f"{name} | Tunisia Handmade",
                description=desc,
                keywords=[name, mat, "artisanat tunisien"],
                slug=name.lower().replace(" ", "-"),
                canonical_url=f"https://tunisia-handmade.tn/products/{name.lower().replace(' ', '-')}",
                is_indexable=True,
            )
            db.add(sd)
            await db.flush()

        print(f"Products: {len(products)} created")

        # ProductScores
        for p in products:
            ps = ProductScore(
                product_id=p.id,
                store_id=store.id,
                score=round(0.7 + (hash(str(p.id)) % 10) * 0.03, 2),
                score_type="ai",
                detail={"relevance": 0.85, "quality": 0.9, "trending": 0.7},
            )
            db.add(ps)
            await db.flush()

        # SellerTrustScores
        st = SellerTrustScore(
            seller_id=merchant.id,
            score=0.85,
            components={"delivery": 0.9, "quality": 0.88, "response": 0.82, "reviews": 0.85},
            level="gold",
        )
        db.add(st)
        await db.flush()

        # Collections
        collections = {}
        coll_data = [
            ("Collection Printemps", "collection-printemps", "Nouvelles pièces artisanales printanières", 1),
            ("Best Sellers", "best-sellers", "Nos produits les plus vendus", 2),
            ("Editions Limitées", "editions-limitees", "Pièces uniques en édition limitée", 3),
        ]
        for name, slug, desc, order in coll_data:
            result = await db.execute(select(Collection).where(Collection.slug == slug))
            c = result.scalar_one_or_none()
            if c is None:
                c = Collection(
                    merchant_id=merchant.id,
                    store_id=store.id,
                    name=name,
                    slug=slug,
                    description=desc,
                    sort_order=order,
                )
                db.add(c)
                await db.flush()
            else:
                c.store_id = store.id
            collections[name] = c

        # Marketplace listings
        for p in products[:5]:
            ml = MarketplaceListing(
                product_id=p.id,
                store_id=store.id,
                marketplace="Jumia Tunisia",
                marketplace_product_id=f"JM-{p.id.hex[:8].upper()}",
                listing_status="active",
                sync_status="synced",
            )
            db.add(ml)
            await db.flush()

        print(f"Collections: {len(collections)}, Marketplace listings: 5 created")

        # 9. Conversations with messages
        customers = [
            ("Amira Ben Ali", "+216 50 111 111", "Tunis", buyers[0]),
            ("Karim Jebali", "+216 52 222 222", "Sfax", buyers[1]),
            ("Sarra Makhlouf", "+216 55 333 333", "Sousse", buyers[2]),
            ("Mehdi Gharbi", None, None, buyers[3]),
            ("Lamia Trabelsi", "+216 58 444 444", "Nabeul", buyers[4]),
        ]

        convos = []
        for name, phone, addr, buyer in customers:
            days_ago = len(convos) * 4 + 1
            created = datetime.utcnow() - timedelta(days=days_ago)
            conv = Conversation(
                user_id=user.id,
                buyer_id=buyer.id,
                store_id=store.id,
                customer_name=name,
                customer_phone=phone,
                customer_address=addr,
                language="fr",
                platform="website",
                status="active",
                created_at=created,
                updated_at=created,
            )
            db.add(conv)
            await db.flush()

            msg_texts = [
                "Bonjour, je cherche un cadeau pour ma mère",
                "Salam, est-ce que vous avez des produits en cuir ?",
                "Bonjour, combien coûte la poterie ?",
                "Hi, do you ship to Sousse ?",
                "السلام عليكم، عندي حفلة عائلية",
            ]
            idx = len(convos)
            msg = Message(
                conversation_id=conv.id,
                role="user",
                content=msg_texts[idx],
                language="fr",
                created_at=created + timedelta(seconds=10),
            )
            db.add(msg)

            replies = {
                "fr": [
                    "Bien sûr ! Nous avons de magnifiques boucles d'oreilles en argent à 65 TND, ou un sac en cuir véritable à 180 TND. Que préfère-t-elle ?",
                    "Oui, nous avons un superbe sac en cuir véritable à 180 TND ainsi que des ceintures artisanales. Souhaitez-vous voir les modèles ?",
                    "La poterie traditionnelle est à 45 TND. C'est une pièce unique faite à la main. Vous souhaitez commander ?",
                    "Yes, we deliver to Sousse and all over Tunisia. Delivery takes 2-3 business days. Would you like to place an order?",
                    "مرحباً! بالتأكيد. لدينا فساتين تقليدية مطرزة و أكسسوارات جميلة. هل تريدين شيئاً معيناً؟",
                ],
            }
            reply_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=replies["fr"][idx],
                language="fr",
                created_at=created + timedelta(seconds=15),
            )
            db.add(reply_msg)
            await db.flush()
            convos.append(conv)
        print(f"Conversations: {len(convos)} created")

        # 10. Orders
        statuses = ["pending", "confirmed", "preparing", "shipped", "delivered", "delivered", "cancelled"]
        orders_data = [
            (customers[0], [products[4], products[5]], [1, 2]),
            (customers[1], [products[6]], [3]),
            (customers[2], [products[0], products[2]], [2, 1]),
            (customers[3], [products[9]], [1]),
            (customers[0], [products[1], products[8]], [1, 1]),
            (customers[4], [products[3], products[7]], [5, 2]),
            (customers[2], [products[4]], [1]),
        ]

        for i, ((name, phone, addr, buyer), prods, qtys) in enumerate(orders_data):
            created = datetime.utcnow() - timedelta(days=i * 2 + 1)
            total = sum(p.price * q for p, q in zip(prods, qtys))
            order = Order(
                user_id=user.id,
                buyer_id=buyer.id,
                store_id=store.id,
                conversation_id=convos[i].id if i < len(convos) else None,
                customer_name=name,
                customer_phone=phone,
                customer_address=addr,
                status=statuses[i],
                total_amount=total,
                created_at=created,
                updated_at=created,
            )
            db.add(order)
            await db.flush()

            for p, q in zip(prods, qtys):
                item = OrderItem(
                    order_id=order.id,
                    product_id=p.id,
                    quantity=q,
                    unit_price=float(p.price),
                    subtotal=q * float(p.price),
                )
                db.add(item)
            await db.flush()
        print(f"Orders: {len(orders_data)} created")

        # 11. AI sessions with messages and tool calls
        for i, conv in enumerate(convos):
            buyer = customers[i][3]
            session = AISession(
                store_id=store.id,
                buyer_id=buyer.id,
                intent="product_recommendation" if i % 2 == 0 else "order_assistance",
                status="closed" if i > 1 else "active",
                conversation_summary=f"Session de vente avec {customers[i][0]}",
                total_messages=2,
            )
            db.add(session)
            await db.flush()

            user_msg = AIMessage(
                session_id=session.id,
                role="user",
                content=msg_texts[i],
                confidence=0.9,
                sequence=0,
            )
            db.add(user_msg)
            await db.flush()

            assistant_msg = AIMessage(
                session_id=session.id,
                role="assistant",
                content=replies["fr"][i],
                confidence=0.95,
                sequence=1,
                tool_calls={"tool": "search_products", "args": {"query": "cadeau"}},
            )
            db.add(assistant_msg)
            await db.flush()

            tool_call = AIToolCall(
                session_id=session.id,
                message_id=assistant_msg.id,
                tool_name="search_products",
                arguments={"query": "cadeau", "limit": 5},
                result={"count": 2, "top": [products[i % 10].name]},
                status="completed",
            )
            db.add(tool_call)
            await db.flush()
        print(f"AI sessions: {len(convos)} created")

        # 12. Events + collections + product gaps
        events = []
        for i in range(3):
            ev = Event(
                event_type="holiday",
                entity_type="product",
                entity_id=str(products[i].id),
                payload={"name": ["Ramadan", "Aid El Fitr", "Mariage"][i], "date": "2026-04-01"},
                meta_data={"season": ["spring", "spring", "summer"][i]},
            )
            db.add(ev)
            await db.flush()
            events.append(ev)

        event_collection = EventCollection(
            event_id=events[0].id,
            collection_type="recommended_by_ai",
            collection_id=str(products[0].id),
            meta_data={"reason": "matching gift occasion"},
        )
        db.add(event_collection)
        await db.flush()

        gap = EventProductGap(
            event_collection_id=event_collection.id,
            product_id=products[0].id,
            gap_type="missing_option",
            details={"needed": "gift_wrapping", "current": "none"},
        )
        db.add(gap)
        await db.flush()
        print(f"Events: {len(events)} created")

        # 13. Consent records
        consent = ConsentRecord(
            buyer_id=buyers[0].id,
            consent_type="marketing",
            consent_text="OK pour recevoir des offres par SMS",
            granted=True,
            meta_data={"channel": "whatsapp"},
        )
        db.add(consent)

        reject_consent = ConsentRecord(
            buyer_id=buyers[2].id,
            consent_type="data_processing",
            consent_text=None,
            granted=False,
            meta_data={"reason": "declined"},
        )
        db.add(reject_consent)
        await db.flush()

        # 14. Approval
        approval = Approval(
            approval_type="price_change",
            entity_type="product",
            entity_id=str(products[0].id),
            title="Approuver la baisse de prix de la poterie",
            description="L'IA propose -10% pour la saison",
            requester_id=user.id,
            status="pending",
            meta_data={"suggested_price": 40.5, "original_price": 45.0},
        )
        db.add(approval)
        await db.flush()

        # 15. Automation rules
        rules = [
            AutomationRule(
                merchant_id=merchant.id,
                name="Alerte stock faible",
                description="Notifier quand le stock d'un produit < 5",
                event_type="inventory_alert",
                conditions={"field": "quantity", "operator": "lt", "value": 5},
                actions={"type": "notify", "channel": "dashboard"},
                is_active=True,
                priority=1,
                execution_count=3,
            ),
            AutomationRule(
                merchant_id=merchant.id,
                name="Relance panier abandonné",
                description="Relancer le client 24h après abandon",
                event_type="cart_abandoned",
                conditions={"field": "hours_since", "operator": "eq", "value": 24},
                actions={"type": "send_message", "channel": "whatsapp"},
                is_active=True,
                priority=2,
                execution_count=0,
            ),
        ]
        for rule in rules:
            db.add(rule)
        print(f"Automation rules: {len(rules)} created")

        # 16. Notifications
        notification = Notification(
            user_id=user.id,
            buyer_id=buyers[0].id,
            store_id=store.id,
            type="order",
            title="Nouvelle commande",
            message="Amira Ben Ali a passé une commande de 2 articles",
            link="/orders/overview",
            read=False,
        )
        db.add(notification)
        await db.flush()

        # 17. Audit logs
        for i in range(5):
            al = AuditLog(
                user_id=user.id,
                action=f"demo_action_{i}",
                entity_type="product",
                entity_id=str(products[i % 10].id),
                details={"source": "seed"},
                ip_address="127.0.0.1",
            )
            db.add(al)
            await db.flush()

        await db.commit()
        print("--- Database seeded successfully! ---")
        print("   Email: demo@socialselling.tn")
        print("   Password: demo123")
        print(f"   Merchant: {merchant.company_name}")
        print(f"   Store: {store.name}")
        print(f"   Buyers: {len(buyers)}")
        print(f"   Products: {len(products)}")
        print(f"   Collections: {len(collections)}")
        print(f"   Orders: {len(orders_data)}")


if __name__ == "__main__":
    asyncio.run(seed())