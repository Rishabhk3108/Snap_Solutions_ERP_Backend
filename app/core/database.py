from urllib.parse import quote

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME

# URL-encode the password so special chars like & don't break URL parsing
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{quote(DB_PASS, safe='')}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
