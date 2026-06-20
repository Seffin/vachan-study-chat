"""
Application configuration.
"""

import os
import secrets

from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Vachan Study"
    APP_DESCRIPTION: str = "AI-powered Bible study chatbot with multilingual support"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Security — load from env or generate a random default to avoid hardcoded secrets
    SECRET_KEY: str = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "vachan_study"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Rate Limiting
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_MINUTES: int = 15

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()