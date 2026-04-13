from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/ai_workspace"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o"
    openai_analysis_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-large"
    openai_use_vector_stores: bool = True

    file_storage_mode: str = "local"
    local_storage_path: str = "./uploads"
    max_upload_mb: int = 10

    cors_origins: str = "http://localhost:3333"

    retrieval_top_k: int = 10
    semantic_threshold: float = 0.45
    max_evidence_pairs: int = 15

    chunk_min_words: int = 50
    chunk_max_words: int = 400
    chunk_overlap_words: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
