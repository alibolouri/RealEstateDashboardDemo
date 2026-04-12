from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI-Powered Real Estate Assistant API"
    app_env: str = "local"
    database_url: str = "sqlite:///./real_estate.db"
    fixed_contact_number: str = "+1-555-123-4567"
    default_realtor_id: int = 1
    admin_username: str = "admin"
    admin_password: str = "changeme-demo-only"
    session_secret: str = "change-this-local-session-secret"
    cookie_secure: bool = False
    session_max_age: int = 60 * 60 * 8
    trusted_hosts: str = "127.0.0.1,localhost,testserver"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
