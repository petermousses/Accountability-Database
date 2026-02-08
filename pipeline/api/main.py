"""FastAPI application for the accountability pipeline."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from accountability_pipeline.config import get_config
from accountability_pipeline.utils.logger import setup_logging
from api.routes import router

config = get_config()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_logging(level=config.log_level, json_output=config.log_json)

    app = FastAPI(
        title="Accountability Pipeline API",
        description="FOIA data processing pipeline for ICE accountability knowledge graph",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")

    return app


app = create_app()
