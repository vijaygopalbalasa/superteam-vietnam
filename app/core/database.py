from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .config import settings

# Convert SQLite URL to async format if not already in async format
db_url = settings.DATABASE_URL
if not db_url.startswith('sqlite+aiosqlite:///'):
    db_url = db_url.replace('sqlite:///', 'sqlite+aiosqlite:///')

# Create async engine
engine = create_async_engine(
    db_url,
    echo=True,
    connect_args={"check_same_thread": False}
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db():
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()