import os
from typing import List
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env if present
load_dotenv()

class Settings(BaseSettings):
    """Application Settings loaded from environment variables."""

    API_ID: int = Field(default=..., validation_alias="API_ID")
    API_HASH: str = Field(default=..., validation_alias="API_HASH")
    BOT_TOKEN: str = Field(default=..., validation_alias="BOT_TOKEN")

    # Database
    MONGO_URI: str = Field(default="mongodb://localhost:27017", validation_alias="MONGO_URI")
    DATABASE_NAME: str = Field(default="telegram_verify_bot", validation_alias="DATABASE_NAME")

    # Admins
    SUPER_ADMIN_IDS: str = Field(default="", validation_alias="SUPER_ADMIN_IDS")

    # Defaults & Limits
    DEFAULT_VERIFICATION_TIMEOUT: int = Field(default=30, validation_alias="DEFAULT_VERIFICATION_TIMEOUT")
    RATE_LIMIT_VERIFY_SECONDS: float = Field(default=2.0)
    RATE_LIMIT_CALLBACK_SECONDS: float = Field(default=0.5)
    LOG_LEVEL: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    @property
    def admin_id_list(self) -> List[int]:
        """Parse comma-separated super admin IDs into a list of integers."""
        if not self.SUPER_ADMIN_IDS:
            return []
        ids = []
        for part in self.SUPER_ADMIN_IDS.split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))
        return ids

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings singleton
settings = Settings()
