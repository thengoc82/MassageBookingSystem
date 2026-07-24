from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CHATBOT_")

    redis_url: str = Field(default="redis://localhost:6379/0")
    session_expiration_seconds: int = Field(default=3600)