from contextlib import asynccontextmanager
import time

from sqlalchemy.exc import OperationalError
from sqlmodel import SQLModel, create_engine

from .config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)


def init_db(max_retries: int = 10, delay_seconds: float = 2.0) -> None:
    attempts = 0
    while True:
        try:
            SQLModel.metadata.create_all(engine)
            return
        except OperationalError:
            attempts += 1
            if attempts > max_retries:
                raise
            time.sleep(delay_seconds)


def get_engine():
    return engine


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield
