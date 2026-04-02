from functools import lru_cache
from typing import Optional
from urllib.parse import urlsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_runtime_mode: str = Field(default="development", alias="APP_RUNTIME_MODE")
    airflow_base_url: Optional[str] = Field(default=None, alias="AIRFLOW_BASE_URL")

    hf_daily_papers_base_url: str = Field(default="https://huggingface.co/papers", alias="HF_DAILY_PAPERS_BASE_URL")
    hf_request_timeout_seconds: int = Field(default=20, alias="HF_REQUEST_TIMEOUT_SECONDS")

    arxiv_api_base_url: str = Field(default="https://export.arxiv.org/api/query", alias="ARXIV_API_BASE_URL")
    arxiv_request_timeout_seconds: int = Field(default=20, alias="ARXIV_REQUEST_TIMEOUT_SECONDS")
    arxiv_request_batch_size: int = Field(default=25, alias="ARXIV_REQUEST_BATCH_SIZE")
    arxiv_request_delay_seconds: float = Field(default=3.0, alias="ARXIV_REQUEST_DELAY_SECONDS")

    mongo_host: Optional[str] = Field(default=None, alias="MONGO_HOST")
    server_mongo_port: int = Field(default=27017, alias="SERVER_MONGO_PORT")
    mongo_db: str = Field(default="arxplore_source", alias="MONGO_DB")
    mongo_initdb_root_username: Optional[str] = Field(default=None, alias="MONGO_INITDB_ROOT_USERNAME")
    mongo_initdb_root_password: Optional[str] = Field(default=None, alias="MONGO_INITDB_ROOT_PASSWORD")
    mongo_daily_papers_collection: str = Field(default="daily_papers_raw", alias="MONGO_DAILY_PAPERS_COLLECTION")

    postgres_host: Optional[str] = Field(default=None, alias="POSTGRES_HOST")
    server_postgres_port: int = Field(default=5432, alias="SERVER_POSTGRES_PORT")
    postgres_db: Optional[str] = Field(default=None, alias="POSTGRES_DB")
    app_postgres_db: Optional[str] = Field(default=None, alias="APP_POSTGRES_DB")
    postgres_user: Optional[str] = Field(default=None, alias="POSTGRES_USER")
    postgres_password: Optional[str] = Field(default=None, alias="POSTGRES_PASSWORD")

    langsmith_api_key: Optional[str] = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="ArXplore", alias="LANGSMITH_PROJECT")
    langsmith_workspace_id: Optional[str] = Field(default=None, alias="LANGSMITH_WORKSPACE_ID")
    langsmith_tracing: bool = Field(default=True, alias="LANGSMITH_TRACING")
    langsmith_trace_user: Optional[str] = Field(default=None, alias="LANGSMITH_TRACE_USER")

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")


def resolve_host_and_port(host: str, default_port: int) -> tuple[str, int]:
    normalized = host.strip()
    if not normalized:
        raise ValueError("호스트 값이 비어 있습니다.")

    parsed = urlsplit(f"//{normalized}")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"호스트 값을 해석할 수 없습니다: {host}")

    return hostname, parsed.port or default_port


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
