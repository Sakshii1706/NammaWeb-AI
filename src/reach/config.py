from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            f"Environment variable {name} must be an integer."
        ) from exc


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"Environment variable {name} must be a number."
        ) from exc


@dataclass(frozen=True)
class Settings:
    # ========================================================
    # APPLICATION
    # ========================================================

    app_name: str = _env(
        "NAMMAWEB_APP_NAME",
        "NammaWeb AI",
    )

    app_env: str = _env(
        "NAMMAWEB_APP_ENV",
        "development",
    )

    host: str = _env(
        "NAMMAWEB_HOST",
        "127.0.0.1",
    )

    port: int = _env_int(
        "NAMMAWEB_PORT",
        8502,
    )

    # ========================================================
    # STORAGE
    # ========================================================

    documents_path: Path = PROJECT_ROOT / _env(
        "NAMMAWEB_DOCUMENTS_PATH",
        "documents",
    )

    faiss_path: Path = PROJECT_ROOT / _env(
        "NAMMAWEB_FAISS_PATH",
        "data/faiss_index",
    )

    database_path: Path = PROJECT_ROOT / _env(
        "NAMMAWEB_DATABASE_PATH",
        "data/nammaweb.db",
    )

    # ========================================================
    # RAG
    # ========================================================

    embedding_model: str = _env(
        "NAMMAWEB_EMBEDDING_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2",
    )

    rag_top_k: int = _env_int(
        "NAMMAWEB_RAG_TOP_K",
        4,
    )

    chunk_size: int = _env_int(
        "NAMMAWEB_CHUNK_SIZE",
        400,
    )

    chunk_overlap: int = _env_int(
        "NAMMAWEB_CHUNK_OVERLAP",
        100,
    )

    max_context_characters_per_source: int = _env_int(
        "NAMMAWEB_MAX_CONTEXT_CHARS_PER_SOURCE",
        4000,
    )

    # ========================================================
    # LOCAL LLM
    # ========================================================

    ollama_model: str = _env(
        "NAMMAWEB_OLLAMA_MODEL",
        "llama3.2:1b",
    )

    llm_temperature: float = _env_float(
        "NAMMAWEB_LLM_TEMPERATURE",
        0.0,
    )

    llm_num_predict: int = _env_int(
        "NAMMAWEB_LLM_NUM_PREDICT",
        160,
    )

    llm_keep_alive: str = _env(
        "NAMMAWEB_LLM_KEEP_ALIVE",
        "24h",
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    def validate(self) -> None:
        if self.rag_top_k < 1:
            raise ValueError("rag_top_k must be >= 1.")

        if self.chunk_size < 1:
            raise ValueError("chunk_size must be >= 1.")

        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0.")

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size."
            )

        if self.max_context_characters_per_source < 1:
            raise ValueError(
                "max_context_characters_per_source must be >= 1."
            )

        if self.llm_num_predict < 1:
            raise ValueError(
                "llm_num_predict must be >= 1."
            )

        if not self.ollama_model:
            raise ValueError("ollama_model cannot be empty.")

        if not self.embedding_model:
            raise ValueError("embedding_model cannot be empty.")

    def ensure_directories(self) -> None:
        self.documents_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.faiss_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )


settings = Settings()

settings.validate()
settings.ensure_directories()

