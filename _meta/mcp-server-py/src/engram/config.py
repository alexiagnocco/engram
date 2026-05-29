from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class FallbackMode(StrEnum):
    AUTO = "auto"
    REST_ONLY = "rest_only"
    FS_ONLY = "fs_only"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Vault root. Override via the VAULT_PATH env var; defaults to ~/vault.
    vault_path: Path = Path.home() / "vault"
    obsidian_rest_url: str = "https://127.0.0.1:27124"
    obsidian_api_key: str = ""
    obsidian_rest_api_version_min: str = "3.6.2"
    obsidian_verify_tls: str = "false"
    obsidian_recheck_interval_sec: int = 30
    obsidian_fallback_mode: FallbackMode = FallbackMode.AUTO
    engram_log_level: str = "INFO"
    engram_log_file: str = ""

    # Hybrid dense retrieval (vault_retrieve).
    # backend: auto | onnx | hashing | none
    engram_embeddings_backend: str = "auto"
    # Directory containing model.onnx + tokenizer.json for the ONNX backend.
    engram_embeddings_model_dir: str = ""
    # Vector dimension for the dependency-free hashing fallback backend.
    engram_embeddings_dim: int = 256
    # Weight of the z-normalized dense signal vs the keyword base in fusion.
    engram_dense_weight: float = 1.0

    @field_validator("vault_path")
    @classmethod
    def resolve_vault_path(cls, v: Path) -> Path:
        return v.resolve()

    @model_validator(mode="after")
    def resolve_api_key_from_keyring(self) -> Settings:
        if self.obsidian_api_key:
            return self
        try:
            import keyring as kr

            secret = kr.get_password("engram", "obsidian-rest")
            if secret:
                self.obsidian_api_key = secret
                logger.info("API key resolved from keyring")
                return self
        except Exception:
            logger.debug("keyring fallback failed", exc_info=True)
        logger.warning("No OBSIDIAN_API_KEY found in env or keyring; state will be UNCONFIGURED")
        return self

    @property
    def tls_verify(self) -> bool | str:
        val = self.obsidian_verify_tls.strip().lower()
        if val == "false":
            return False
        if val == "true":
            return True
        return self.obsidian_verify_tls
