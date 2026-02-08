"""Central configuration for the accountability pipeline.

Uses pydantic-settings to load from environment variables and .env files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineConfig(BaseSettings):
    """Pipeline configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="PIPELINE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Neo4j connection
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    # Processing
    fuzzy_match_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    max_document_size_mb: int = Field(default=50, ge=1)
    batch_size: int = Field(default=100, ge=1)

    # Directories
    output_dir: str = "./output"
    upload_dir: str = "./uploads"
    foia_output_dir: str = "./output/foia"
    export_dir: str = "./output/exports"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Logging
    log_level: str = "INFO"
    log_json: bool = False

    # spaCy model
    spacy_model: str = "en_core_web_sm"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_directories(self) -> None:
        """Create all configured directories if they don't exist."""
        for dir_path in [self.output_dir, self.upload_dir, self.foia_output_dir, self.export_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)


def get_config() -> PipelineConfig:
    """Get the pipeline configuration singleton."""
    return PipelineConfig()
