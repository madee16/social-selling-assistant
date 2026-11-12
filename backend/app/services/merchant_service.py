import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.buyer import Buyer
from app.models.merchant import Merchant
from app.models.store import Store
from app.models.store_member import StoreMember
from app.schemas.buyer import BuyerCreate, BuyerUpdate
from app.schemas.merchant import MerchantCreate, MerchantUpdate, StoreCreate, StoreUpdate
from app.services import crud


def _user_merchant_ids(user_id: uuid.UUID):
    return select(Merchant.id).where(Merchant.user_id == user_id)


def _user_store_where(user_id: uuid.UUID):
    return Store.merchant_id.in_(_user_merchant_ids(user_id))


async def get_merchant(db: AsyncSession, user_id: uuid.UUID) -> Merchant | None:
    return await crud.get_merchant_for_user(db, user_id)


async def create_merchant(db: AsyncSession, user_id: uuid.UUID, data: MerchantCreate) -> Merchant:
    return await crud.create_record(db, Merchant, {"user_id": user_id, **data.model_dump()})


async def update_merchant(db: AsyncSession, merchant: Merchant, data: MerchantUpdate) -> Merchant:
    return await crud.update_record(db, merchant, data.model_dump(exclude_unset=True))


async def list_stores(
    db: AsyncSession, user_id: uuid.UUID, page: int = 1, page_size: int = 20
):
    return await crud.list_records(
        db, Store, where=_user_store_where(user_id), page=page, page_size=page_size
    )


async def get_store(db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID) -> Store | None:
    where = (Store.id == store_id) & _user_store_where(user_id)
    return await crud.get_record(db, Store, where)


async def create_store(db: AsyncSession, user_id: uuid.UUID, data: StoreCreate) -> Store | None:
    merchant = await get_merchant(db, user_id)
    if not merchant:
        return None
    return await crud.create_record(
        db, Store, {"merchant_id": merchant.id, **data.model_dump()}
    )


async def update_store(db: AsyncSession, store: Store, data: StoreUpdate) -> Store:
    return await crud.update_record(db, store, data.model_dump(exclude_unset=True))


async def delete_store(db: AsyncSession, store: Store) -> None:
    await crud.delete_record(db, store)


async def list_store_members(
    db: AsyncSession, store_id: uuid.UUID, page: int = 1, page_size: int = 20
):
    return await crud.list_records(
        db, StoreMember, where=StoreMember.store_id == store_id, page=page, page_size=page_size
    )


async def add_store_member(
    db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID, role: str
) -> StoreMember:
    return await crud.create_record(
        db, StoreMember, {"store_id": store_id, "user_id": user_id, "role": role}
    )


async def remove_store_member(db: AsyncSession, member: StoreMember) -> None:
    await crud.delete_record(db, member)


async def list_buyers(
    db: AsyncSession, page: int = 1, page_size: int = 20, search: str | None = None
):
    where = None
    if search:
        where = (
            (Buyer.name.ilike(f"%{search}%"))
            | (Buyer.email.ilike(f"%{search}%"))
            | (Buyer.phone.ilike(f"%{search}%"))
        )
    return await crud.list_records(db, Buyer, where=where, page=page, page_size=page_size)


async def get_buyer(db: AsyncSession, buyer_id: uuid.UUID) -> Buyer | None:
    return await crud.get_record(db, Buyer, Buyer.id == buyer_id)


async def create_buyer(db: AsyncSession, data: BuyerCreate) -> Buyer:
    return await crud.create_record(db, Buyer, data.model_dump())


async def update_buyer(db: AsyncSession, buyer: Buyer, data: BuyerUpdate) -> Buyer:
    return await crud.update_record(db, buyer, data.model_dump(exclude_unset=True))


async def delete_buyer(db: AsyncSession, buyer: Buyer) -> None:
    await crud.delete_record(db, buyer)
