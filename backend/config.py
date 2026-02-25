from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    max_upload_size_mb: int = 10
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    enable_pdf_output: bool = False
    similarity_top_k: int = 5
    similarity_threshold: float = 0.6
    cors_allow_origin: str = "http://localhost:3000"

    class Config:
        env_prefix = "AI_ANALYZER_"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()

