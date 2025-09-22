import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://memoria:memoria@db:5432/memoria",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")
    llm_model: str = os.getenv("LLM_MODEL", "llama3.2:3b")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    vector_dim: int = int(os.getenv("VECTOR_DIM", "384"))

    class Config:
        case_sensitive = False


settings = Settings()


