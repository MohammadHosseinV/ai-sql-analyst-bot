"""
Core Application Configuration Module
Uses Pydantic Settings v2 to load, validate, and construct configuration parameters.
"""

from functools import lru_cache
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Global application settings loaded from environment variables and .env file.
    """

    # General App Settings
    APP_NAME: str = "Autonomous Data Analyst API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # PostgreSQL Database Settings
    POSTGRES_HOST: str = "postgres_db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ecommerce_analytics"
    POSTGRES_USER: str = "admin_user"
    POSTGRES_PASSWORD: str = "StrongAdminPassword_2026!"

    # Read-Only Database Credentials (Used strictly by AI SQL Execution)
    DB_READONLY_USER: str = "llm_reader"
    DB_READONLY_PASSWORD: str = "ReadOnlySafePassword_2026!"

    # Constructed Database Connection URLs
    ADMIN_DATABASE_URL: Optional[str] = None
    READONLY_DATABASE_URL: Optional[str] = None

    # LLM Settings (Supports "gemini" and "openai" providers)
    LLM_PROVIDER: str = "gemini"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_TEMPERATURE: float = 0.0
    LLM_TIMEOUT_SECONDS: int = 45

    # Self-Correction and Safety Limits
    MAX_SQL_RETRIES: int = 3
    MAX_RESULT_ROWS: int = 100

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @model_validator(mode="after")
    def assemble_database_urls(self) -> "Settings":
        """
        Dynamically constructs admin and readonly PostgreSQL URLs if not explicitly set in environment.
        """
        if not self.ADMIN_DATABASE_URL:
            self.ADMIN_DATABASE_URL = (
                f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        if not self.READONLY_DATABASE_URL:
            self.READONLY_DATABASE_URL = (
                f"postgresql+psycopg2://{self.DB_READONLY_USER}:{self.DB_READONLY_PASSWORD}@"
                f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    """
    Returns cached singleton instance of application settings.
    """
    return Settings()
