from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """LayaPulse application settings. All values configurable via environment variables."""

    # ── App ──────────────────────────────────────────────
    app_name: str = "LayaPulse"
    debug: bool = True

    # ── Database ─────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./layapulse.db"

    # ── Stream source ────────────────────────────────────
    stream_mode: str = "mock"           # "mock" | "twitter"
    mock_post_interval: float = 2.5     # seconds between mock posts

    # ── Twitter / X API (only when stream_mode == "twitter") ──
    twitter_bearer_token: str = ""
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_search_query: str = "(AI OR technology OR startup OR bitcoin OR breaking) -is:retweet lang:en"
    twitter_poll_interval: float = 8.0
    twitter_stream_type: str = "auto"   # "filtered" | "recent" | "auto"

    # ── LLM ──────────────────────────────────────────────
    llm_provider: str = "mock"          # "mock" | "openai" | "gemini"
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # ── Embeddings ───────────────────────────────────────
    embedding_provider: str = "mock"    # "mock" | "openai"
    embedding_dim: int = 384

    # ── Vector store ─────────────────────────────────────
    vector_store_type: str = "memory"   # "memory" | "qdrant" | "pgvector"

    # ── Classification categories (default set) ─────────
    default_categories: List[str] = [
        "AI", "Machine Learning", "Technology", "Startups",
        "Finance", "Politics", "Sports", "Science",
        "Cybersecurity", "Climate", "Gaming", "Other",
    ]

    # ── Server ───────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "https://x.com",
        "https://twitter.com",
        "*",
    ]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
