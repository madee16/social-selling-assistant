from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Supabase pooler uses port 6543; direct connections use 5432
direct_url = settings.supabase_db_url.replace(":6543/", ":5432/")
engine = create_async_engine(
    direct_url,
    echo=settings.database_echo,
)

async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
