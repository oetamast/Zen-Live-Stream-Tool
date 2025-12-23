from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ZenStream Tool"
    environment: str = "development"
    database_url: str = "postgresql+psycopg2://zenstream:zenstream@db:5432/zenstream"
    admin_username: str = "admin"
    admin_password: str = "changeme"
    data_dir: str = "/data"
    safety_cap_default: bool = True
    runner_heartbeat_seconds: int = 30
    license_endpoint: str = "https://example.com/activation"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
