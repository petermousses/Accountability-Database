"""Tests for pipeline configuration."""

import os

import pytest

from accountability_pipeline.config import PipelineConfig, get_config


class TestPipelineConfig:
    def test_defaults(self):
        config = PipelineConfig()
        assert config.neo4j_uri == "bolt://localhost:7687"
        assert config.fuzzy_match_threshold == 0.85
        assert config.batch_size == 100
        assert config.api_port == 8000
        assert config.log_level == "INFO"

    def test_cors_origin_list(self):
        config = PipelineConfig()
        origins = config.cors_origin_list
        assert isinstance(origins, list)
        assert len(origins) >= 1

    def test_custom_cors(self):
        config = PipelineConfig(cors_origins="http://a.com,http://b.com")
        assert config.cors_origin_list == ["http://a.com", "http://b.com"]

    def test_ensure_directories(self, tmp_dir):
        config = PipelineConfig(
            output_dir=os.path.join(tmp_dir, "out"),
            upload_dir=os.path.join(tmp_dir, "up"),
            foia_output_dir=os.path.join(tmp_dir, "foia"),
            export_dir=os.path.join(tmp_dir, "export"),
        )
        config.ensure_directories()
        assert os.path.isdir(config.output_dir)
        assert os.path.isdir(config.upload_dir)
        assert os.path.isdir(config.foia_output_dir)
        assert os.path.isdir(config.export_dir)

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_NEO4J_URI", "bolt://custom:7687")
        monkeypatch.setenv("PIPELINE_LOG_LEVEL", "DEBUG")
        config = PipelineConfig()
        assert config.neo4j_uri == "bolt://custom:7687"
        assert config.log_level == "DEBUG"

    def test_threshold_bounds(self):
        config = PipelineConfig(fuzzy_match_threshold=0.0)
        assert config.fuzzy_match_threshold == 0.0
        config = PipelineConfig(fuzzy_match_threshold=1.0)
        assert config.fuzzy_match_threshold == 1.0


class TestGetConfig:
    def test_returns_config(self):
        config = get_config()
        assert isinstance(config, PipelineConfig)
