"""Application settings and configuration."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

    # Application
    app_name: str = Field(default="MCParr AI Gateway", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    mcp_port: int = Field(default=8001, alias="MCP_PORT")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:////home/jeremie/Documents/Dev/ia-homelab/ia-homelab/backend/data/mcparr.db",
        alias="DATABASE_URL",
    )

    # Redis (optional)
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    cache_ttl: int = Field(default=300, alias="CACHE_TTL")

    # CORS - Use "*" in development to allow any origin
    cors_origins: List[str] = Field(
        default=["*"],
        alias="CORS_ORIGINS",
    )

    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # External Services
    plex_url: str = Field(default="", alias="PLEX_URL")
    plex_token: str = Field(default="", alias="PLEX_TOKEN")

    overseerr_url: str = Field(default="", alias="OVERSEERR_URL")
    overseerr_api_key: str = Field(default="", alias="OVERSEERR_API_KEY")

    zammad_url: str = Field(default="", alias="ZAMMAD_URL")
    zammad_token: str = Field(default="", alias="ZAMMAD_TOKEN")

    tautulli_url: str = Field(default="", alias="TAUTULLI_URL")
    tautulli_api_key: str = Field(default="", alias="TAUTULLI_API_KEY")

    authentik_url: str = Field(default="", alias="AUTHENTIK_URL")
    authentik_token: str = Field(default="", alias="AUTHENTIK_TOKEN")

    openwebui_url: str = Field(default="http://192.168.1.60:8080", alias="OPEN_WEBUI_URL")
    openwebui_api_key: str = Field(default="", alias="OPEN_WEBUI_API_KEY")

    ollama_url: str = Field(default="http://localhost:11434", alias="OLLAMA_URL")
    ollama_model: str = Field(default="llama2", alias="OLLAMA_MODEL")

    # Training Worker (GPU fine-tuning)
    training_worker_url: str = Field(default="http://192.168.1.60:8088", alias="TRAINING_WORKER_URL")
    training_worker_api_key: str = Field(default="", alias="TRAINING_WORKER_API_KEY")

    # Monitoring
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, alias="METRICS_PORT")

    # Docker
    docker_socket: str = Field(default="/var/run/docker.sock", alias="DOCKER_SOCKET")

    # Alerts
    alert_email_enabled: bool = Field(default=False, alias="ALERT_EMAIL_ENABLED")
    alert_email_host: str = Field(default="", alias="ALERT_EMAIL_HOST")
    alert_email_port: int = Field(default=587, alias="ALERT_EMAIL_PORT")
    alert_email_user: str = Field(default="", alias="ALERT_EMAIL_USER")
    alert_email_password: str = Field(default="", alias="ALERT_EMAIL_PASSWORD")
    alert_email_from: str = Field(default="", alias="ALERT_EMAIL_FROM")
    alert_email_to: str = Field(default="", alias="ALERT_EMAIL_TO")

    alert_webhook_enabled: bool = Field(default=False, alias="ALERT_WEBHOOK_ENABLED")
    alert_webhook_url: str = Field(default="", alias="ALERT_WEBHOOK_URL")

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as list."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.app_env.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
