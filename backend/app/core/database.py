from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings, is_postgres

# Engine configuration differs by backend:
#  - SQLite: no pool tuning needed
#  - Postgres: enable a connection pool with sane defaults + pre-ping so stale
#    connections (common on managed Postgres / RDS) are recycled cleanly.
if is_postgres():
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,  # recycle connections every 30 min
    )
else:
    engine = create_async_engine(settings.database_url, echo=False)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    from app.models import (  # noqa
        user, tenant, connector, device, event, ticket, audit_log,
        ai_usage, custom_policy, platform, soc2, evidence, collector,
        framework, platform_settings,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
