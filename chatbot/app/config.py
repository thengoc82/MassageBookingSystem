from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CHATBOT_")

    redis_url: str = Field(default="redis://localhost:6379/0")
    session_expiration_seconds: int = Field(default=3600)

    # NLU settings
    nlu_confidence_threshold: float = Field(default=0.7)

    # Knowledge system settings
    knowledge_root: str = Field(default="docs/knowledge")
    chunk_size: int = Field(default=500, ge=1)
    chunk_overlap: int = Field(default=50, ge=0)
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_dim: int = Field(default=384, ge=1)
    vector_store_top_k: int = Field(default=5, ge=1)
    pg_dsn: str = Field(default="postgresql://localhost:5432/chatbot")

    # OpenAI settings
    openai_api_key: str = Field(default="sk-no-key-provided", secret=True)
    openai_model: str = Field(default="gpt-4o")
    enable_rag: bool = Field(default=False)
