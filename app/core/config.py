from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+asyncpg://vitara:password@localhost:5432/vitara_db"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    APP_ENV: str = "development"
    SECRET_KEY: str = "dev-secret-key"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()
