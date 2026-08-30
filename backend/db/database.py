import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env")

# Parse DATABASE_URL
parsed = urlparse(DATABASE_URL)
query_params = parse_qs(parsed.query)

# Check SSL requirements
sslmode_param = query_params.pop("sslmode", [None])[0]
ssl_param = query_params.pop("ssl", [None])[0]
db_ssl_env = os.getenv("DB_SSL", "true").lower() not in ("false", "0")
is_cloud_host = any(
    cloud in (parsed.hostname or "")
    for cloud in ["azure.com", "supabase.co", "supabase.com", "neon.tech", "render.com", "railway.app", "fly.dev", "aivencloud"]
)
require_ssl = (
    db_ssl_env
    and (is_cloud_host or sslmode_param in ("require", "verify-ca", "verify-full") or ssl_param in ("require", "true", "1"))
)

# 1. Async URL for asyncpg (strip sslmode query param since asyncpg takes ssl in connect_args)
async_query = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
ASYNC_DATABASE_URL = urlunparse((
    "postgresql+asyncpg",
    parsed.netloc,
    parsed.path,
    parsed.params,
    urlencode(async_query),
    parsed.fragment
))

# 2. Sync URL for psycopg2
sync_query = dict(async_query)
if require_ssl:
    sync_query["sslmode"] = "require"
sync_url = urlunparse((
    "postgresql",
    parsed.netloc,
    parsed.path,
    parsed.params,
    urlencode(sync_query),
    parsed.fragment
))

async_connect_args = {"ssl": "require"} if require_ssl else {}
sync_connect_args = {"sslmode": "require"} if require_ssl else {}

engine = create_engine(sync_url, pool_pre_ping=True, connect_args=sync_connect_args)
async_engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True, connect_args=async_connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session
