from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewayConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CHATBOT_GATEWAY_")

    flask_base_url: str = Field(default="http://localhost:5000/api")
    timeout_seconds: float = Field(default=10.0, gt=0)
    max_retries: int = Field(default=3, ge=0)
    retry_backoff_factor: float = Field(default=0.5, ge=0)
    retry_backoff_max: float = Field(default=30.0, ge=0)
