"""
Database connection and session management.
Uses SQLAlchemy 2.0 async API.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base



from sqlalchemy.pool import NullPool

def _pgbouncer_statement_name():
    """
    Returns empty string to force usage of anonymous prepared statements.
    Required for pgbouncer transaction pooling to avoid collisions.
    """
    return ""

from app.core.config import settings



print("DEBUG: Configuring database with connection pooling enabled")

# Create async engine
# Force unique prepared statement names to bypass "already exists" errors
database_url = settings.DATABASE_URL
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif database_url and database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Configure pool arguments based on settings
engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
    "connect_args": {
        "statement_cache_size": 0,
        "prepared_statement_name_func": _pgbouncer_statement_name,
    },
}

if settings.DATABASE_POOL_SIZE == 0:
    print("DEBUG: Disabling connection pooling (NullPool)")
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(database_url, **engine_kwargs)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency to get database session.
    Usage in FastAPI:
        @app.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database (create tables)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()
