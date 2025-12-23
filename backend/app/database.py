from contextlib import asynccontextmanager

from sqlmodel import SQLModel, create_engine

from .config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_engine():
    return engine


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield
