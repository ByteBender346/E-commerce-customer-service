import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from dianshang.conf.config import settings

engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db_engine():
    global engine, session_factory
    engine = create_async_engine(settings.database_url)
    # expire_on_commit=False：异步场景下提交后不自动过期对象，避免额外查询
    session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def close_db_engine():
    if engine:
        await engine.dispose()


if __name__ == '__main__':
    async def test():
        init_db_engine()
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            print(result.scalar())
        await close_db_engine()

    asyncio.run(test())
