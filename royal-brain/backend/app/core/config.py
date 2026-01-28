from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    # .../royal-brain/backend/app/core/config.py -> parents[3] == repo root
    return Path(__file__).resolve().parents[3]


def _env_file_path() -> Path | None:
    """Return repo-root .env.<RB_ENV> if it exists.

    In production/container deployments, environment variables are commonly injected at runtime
    and no repo-root env file is present. In that case, return None and let BaseSettings read
    directly from the process environment.
    """

    rb_env = os.getenv("RB_ENV", "dev").strip() or "dev"
    candidate = _repo_root() / f".env.{rb_env}"
    if candidate.exists():
        return candidate

    return None


class Settings(BaseSettings):
    rb_env: str = Field(default="dev", validation_alias="RB_ENV")

    backend_host: str = Field(default="127.0.0.1", validation_alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, validation_alias="BACKEND_PORT")

    database_url: str = Field(validation_alias="DATABASE_URL")

    jwt_secret: str = Field(validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    cors_origins: list[str] = Field(default_factory=list, validation_alias="CORS_ORIGINS")

    bootstrap_admin_email: str | None = Field(
        default=None, validation_alias="BOOTSTRAP_ADMIN_EMAIL"
    )
    bootstrap_admin_password: str | None = Field(
        default=None, validation_alias="BOOTSTRAP_ADMIN_PASSWORD"
    )

    openai_api_key: str | None = Field(
        default=None, validation_alias="OPENAI_API_KEY"
    )

    # EVM anchoring (real on-chain transactions)
    evm_rpc_url: str | None = Field(default=None, validation_alias="EVM_RPC_URL")
    evm_chain_id: int | None = Field(default=None, validation_alias="EVM_CHAIN_ID")
    evm_private_key: str | None = Field(default=None, validation_alias="EVM_PRIVATE_KEY")
    evm_explorer_tx_url_base: str | None = Field(
        default=None, validation_alias="EVM_EXPLORER_TX_URL_BASE"
    )

    # `enable_decoding=False` ensures list fields can be supplied as comma-separated strings
    # (rather than requiring JSON arrays) and validated deterministically.
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file_encoding="utf-8",
        enable_decoding=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    env_file = _env_file_path()
    if env_file is not None:
        return Settings(_env_file=env_file)
    return Settings()
