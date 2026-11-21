from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_version: str = "0.1.0"
    api_port: int = 8000
    database_url: str = "postgresql://user:password@db:5432/agent_db"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    environment: Literal["development", "production"] = "development"
    llm_provider: Literal["openai", "anthropic", "gemini", "ollama", "xai"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = "sk-your-provider-key"
    xai_api_key: str = ""
    llm_base_url: str = ""
    oidc_issuer_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = ""
    oidc_allowed_emails: str = ""
    oidc_allow_any_emails: bool = False
    oidc_bootstrap_email: str = ""
    oidc_session_secret: str = ""
    session_cookie_secure: bool = False
    app_encryption_key: str = ""
    searxng_url: str = ""
    crawl4ai_url: str = ""
    research_max_queries: int = Field(default=3, ge=1, le=8)
    research_max_results: int = Field(default=8, ge=1, le=25)
    research_max_pages: int = Field(default=5, ge=1, le=12)
    research_max_bytes: int = Field(default=1_000_000, ge=10_000, le=5_000_000)
    research_timeout_seconds: float = Field(default=12.0, ge=1.0, le=60.0)
    research_max_tool_calls: int = Field(default=12, ge=1, le=30)
    workflow_engine: Literal["temporal", "celery_langgraph"] = "temporal"
    temporal_address: str = "temporal:7233"
    temporal_namespace: str = "default"
    temporal_api_key: str = ""
    cors_origins: str = ""
    log_level: str = "INFO"
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    rate_limit_max_requests: int = Field(default=30, ge=1, le=10000)
    seed_demo_data: bool = False
    celery_probe_timeout_seconds: float = Field(default=1.5, ge=0.1, le=10)
    max_request_bytes: int = Field(default=65536, ge=1024, le=1_048_576)

    @field_validator("llm_api_key", mode="before")
    @classmethod
    def normalize_key(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("xai_api_key", "oidc_client_secret", mode="before")
    @classmethod
    def normalize_sensitive_setting(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("oidc_allowed_emails", "oidc_bootstrap_email", mode="before")
    @classmethod
    def normalize_allowed_emails(cls, value: object) -> str:
        return ",".join(
            sorted({part.strip().lower() for part in str(value or "").split(",") if part.strip()})
        )

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if (
            self.oidc_bootstrap_email
            and not self.oidc_allow_any_emails
            and self.oidc_bootstrap_email not in self.allowed_email_list
        ):
            raise ValueError("OIDC_BOOTSTRAP_EMAIL must be included in OIDC_ALLOWED_EMAILS")
        if self.environment == "production":
            required = {
                "OIDC_ISSUER_URL": self.oidc_issuer_url,
                "OIDC_CLIENT_ID": self.oidc_client_id,
                "OIDC_CLIENT_SECRET": self.oidc_client_secret,
                "OIDC_REDIRECT_URI": self.oidc_redirect_uri,
                "OIDC_SESSION_SECRET": self.oidc_session_secret,
                "APP_ENCRYPTION_KEY": self.app_encryption_key,
            }
            missing = [name for name, value in required.items() if not value]
            if not self.oidc_allowed_emails and not self.oidc_allow_any_emails:
                missing.append("OIDC_ALLOWED_EMAILS or OIDC_ALLOW_ANY_EMAILS=true")
            if missing:
                raise ValueError(f"Production requires settings: {', '.join(missing)}")
            if not self.session_cookie_secure:
                raise ValueError("SESSION_COOKIE_SECURE must be true in production")
            if len(self.oidc_session_secret) < 32:
                raise ValueError("OIDC_SESSION_SECRET must contain at least 32 characters in production")
            if len(self.app_encryption_key) < 32:
                raise ValueError("APP_ENCRYPTION_KEY must contain at least 32 characters in production")
            if not self.oidc_issuer_url.startswith("https://") or not self.oidc_redirect_uri.startswith("https://"):
                raise ValueError("Production OIDC issuer and redirect URI must use HTTPS")
        return self

    @field_validator("database_url")
    @classmethod
    def require_postgres(cls, value: str) -> str:
        if not value.startswith(("postgresql://", "postgres://", "postgresql+")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return value

    @property
    def async_database_url(self) -> str:
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("postgresql+psycopg://"):
            return self.database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
        return self.database_url

    @property
    def sync_database_url(self) -> str:
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        return self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def uses_offline_writer(self) -> bool:
        if self.llm_provider == "ollama":
            return False
        key = (self.xai_api_key if self.llm_provider == "xai" else self.llm_api_key).lower()
        return not key or key.startswith("sk-your-") or key in {
            "your-api-key",
            "changeme",
            "placeholder",
        }

    @property
    def allowed_email_list(self) -> set[str]:
        return {part.strip().lower() for part in self.oidc_allowed_emails.split(",") if part.strip()}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
