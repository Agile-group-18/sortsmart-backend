from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SortSmart"
    frontend_url: str = "https://sortsmart.klepoatra.pro"

    database_url: str = (
        "postgresql+psycopg2://postgres:password@localhost:5432/sortsmart"
    )

    secret_key: str = "change_this_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10_080  # 7 days
    refresh_token_expire_days: int = 90

    refresh_interval_hours: int = 168  # 7 days

    mail_console: bool = True
    mail_username: str = ""
    mail_password: SecretStr = SecretStr("")
    mail_from: str = "noreply@sortsmart.klepoatra.pro"
    mail_port: int = 587
    mail_server: str = (
        "smtp.gmail.com"  # Using Gmail as an example; replace with your SMTP server
    )
    mail_starttls: bool = True
    mail_ssl_tls: bool = False

    max_nearby_limit: int = 200
    default_nearby_limit: int = 100
    default_radius_km: float = 50.0

    categories_cache_seconds: int = 7 * 24 * 3600  # 1 week
    nearby_cache_seconds: int = 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
