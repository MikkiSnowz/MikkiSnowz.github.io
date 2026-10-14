from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://qr_user:qr_password@127.0.0.1:3307/qr_ordering"

    business_name: str = "My Local Cafe"
    currency: str = "aud"
    tax_rate: Decimal = Decimal("0.10")
    tax_inclusive: bool = True
    card_surcharge_rate: Decimal = Decimal("0")
    allow_pay_at_counter: bool = True

    frontend_url: str = "http://localhost:5173"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    admin_api_key: str = ""

    downstream_webhook_url: str = ""
    downstream_webhook_secret: str = ""
    downstream_timeout_seconds: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
