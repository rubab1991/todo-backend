import logging
import os
from pydantic_settings import BaseSettings
from typing import Optional

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Database settings
    neon_db_url: str = ""
    database_url: str = ""
    # Authentication settings
    better_auth_secret: str = ""
    better_auth_url: Optional[str] = "http://localhost:3000"
    # AI/ML services
    cohere_api_key: str = ""
    # Application settings
    debug: str = "false"
    log_level: str = "info"
    # Dapr settings (Phase V)
    dapr_http_port: int = 3500
    dapr_app_id: str = "todo-backend"
    internal_api_base: str = "http://localhost:8000"

    @property
    def database_url_resolved(self) -> str:
        """Return the database URL, preferring neon_db_url if available."""
        return self.neon_db_url or self.database_url

    class Config:
        env_file = ".env"
        env_prefix = ""
        arbitrary_types_allowed = True


def _fetch_dapr_secret(key: str, dapr_port: int = 3500) -> Optional[str]:
    """
    Attempt to fetch a secret from Dapr secretstore (kubernetes).
    Falls back to None if Dapr sidecar is unavailable.
    """
    try:
        import httpx
        url = f"http://localhost:{dapr_port}/v1.0/secrets/kubernetes/{key}"
        resp = httpx.get(url, timeout=2.0)
        if resp.status_code == 200:
            data = resp.json()
            value = data.get(key) or data.get("data", {}).get(key)
            if value:
                logger.info("Loaded '%s' from Dapr secretstore", key)
                return value
    except Exception:
        pass  # Dapr unavailable — fall through to env var
    return None


def load_settings() -> Settings:
    """
    Load settings, attempting Dapr secrets first, then env vars.
    """
    s = Settings()
    # Attempt to enrich with Dapr secrets when running inside K8s
    dapr_port = s.dapr_http_port
    if not s.neon_db_url:
        val = _fetch_dapr_secret("NEON_DB_URL", dapr_port)
        if val:
            s.neon_db_url = val
    if not s.cohere_api_key:
        val = _fetch_dapr_secret("COHERE_API_KEY", dapr_port)
        if val:
            s.cohere_api_key = val
    return s


# Create a single instance of settings
settings = load_settings()