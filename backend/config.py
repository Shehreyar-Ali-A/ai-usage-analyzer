from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    max_upload_size_mb: int = 10
    enable_pdf_output: bool = False
    cors_allow_origin: str = "http://localhost:3333"

    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-large"
    llm_model: str = "gpt-5.4"

    retrieval_top_k: int = 10
    semantic_threshold: float = 0.45
    lexical_threshold: float = 0.25
    max_evidence_pairs: int = 15

    chunk_min_words: int = 50
    chunk_max_words: int = 400
    chunk_overlap_words: int = 50

    class Config:
        env_prefix = "OPENAI_API_"
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()

