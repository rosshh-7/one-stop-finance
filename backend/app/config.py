from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str
    database_url_sync: str

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    secret_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    algorithm: str = "HS256"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""

    # External APIs
    news_api_key: str = ""
    polygon_api_key: str = ""
    edgar_user_agent: str = "OneStopFinance contact@onestopfinance.com"
    fmp_api_key: str = ""
    anthropic_api_key: str = ""
    fred_api_key: str = ""  # fred.stlouisfed.org — macro data (free, instant signup)

    # App
    frontend_url: str = "http://localhost:3000"
    environment: str = "development"
    log_level: str = "info"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
