
from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field

class Settings(BaseSettings):
    app_env: str = "local"
    app_name: str = "yt-analytics"
    app_port: int = 8080

    youtube_api_key: str = ""

    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"
    redis_url: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
