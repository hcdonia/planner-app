"""Application configuration."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = DATA_DIR / "planner.db"
    CREDENTIALS_PATH: Path = BASE_DIR / "credentials.json"
    TOKEN_PATH: Path = BASE_DIR / "token.json"

    # Database - use DATABASE_URL for production (PostgreSQL), fallback to SQLite
    DATABASE_URL: Optional[str] = None

    # API Keys
    OPENAI_API_KEY: str = ""

    # OpenAI Configuration
    OPENAI_MODEL: str = "gpt-4o"

    # Google Calendar - support base64 encoded credentials for cloud deployment
    GOOGLE_SCOPES: list = ["https://www.googleapis.com/auth/calendar"]
    GOOGLE_CREDENTIALS_JSON: Optional[str] = None  # Base64 encoded credentials.json
    GOOGLE_TOKEN_JSON: Optional[str] = None  # Base64 encoded token.json

    # Timezone
    TIMEZONE: str = "America/New_York"

    # Default work hours
    WORK_START_HOUR: int = 9
    WORK_END_HOUR: int = 18  # 6 PM - reasonable end time

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Frontend URL for CORS
    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
