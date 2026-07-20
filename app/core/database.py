from urllib.parse import quote

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from app.core.config import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME

# connect_timeout=10 → fail in 10 s instead of hanging indefinitely when
# Supabase is slow to accept a connection.
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{quote(DB_PASS, safe='')}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require&connect_timeout=10"
)

# NullPool: each request opens its own connection and closes it immediately.
# No connection reuse means no stale-connection hangs — the most reliable
# choice for a low-traffic app on a shared host talking to a remote DB.
engine = create_engine(DATABASE_URL, echo=False, poolclass=NullPool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
