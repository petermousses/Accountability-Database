"""Tests for Neo4j export utilities."""

import json
import os

import pytest

from accountability_pipeline.core.neo4j_exporter import (
    _build_properties,
    _cypher_escape,
    generate_cypher_scripts,
    generate_json_export,
    validate_neo4j_readiness,
)
from accountability_pipeline.utils.file_handler import read_json, read_text


class TestCypherEscape:
    def test_none(self):
        assert _cypher_escape(None) == "null"

    def test_bool(self):
        assert _cypher_escape(True) == "true"
        assert _cypher_escape(False) == "false"

    def test_int(self):
        assert _cypher_escape(42) == "42"

    def test_float(self):
        assert _cypher_escape(3.14) == "3.14"

    def test_string(self):
        assert _cypher_escape("hello") == '"hello"'

    def test_string_with_quotes(self):
        result = _cypher_escape('he said "hi"')
        assert '\\"' in result

    def test_string_with_backslash(self):
        result = _cypher_escape("path\\to\\file")
        assert "\\\\" in result

    def test_list(self):
        result = _cypher_escape(["a", "b"])
        assert result == '["a", "b"]'

    def test_date(self):
        from datetime import date
        result = _cypher_escape(date(2025, 3, 15))
        assert result == 'date("2025-03-15")'


class TestBuildProperties:
    def test_basic_properties(self):
        props = _build_properties({"name": "John", "age": 30})
        assert "name" in props
        assert "age" in props

    def test_excludes_none(self):
        props = _build_properties({"name": "John", "address": None})
        assert "address" not in props

    def test_excludes_internal_keys(self):
        props = _build_properties({"name": "John", "_merged": True})
        assert "_merged" not in props

    def test_excludes_specified_keys(self):
        props = _build_properties({"id": "1", "name": "John"}, exclude_keys={"id"})
        assert "id" not in props

    def test_empty_dict(self):
        props = _build_properties({})
        assert props == "{}"


class TestGenerateCypherScripts:
    def test_generates_nodes(self, tmp_dir, full_pipeline_data):
        result = generate_cypher_scripts(
            full_pipeline_data["agents"],
            full_pipeline_data["violations"],
            full_pipeline_data["incidents"],
            tmp_dir,
            employees=full_pipeline_data["employees"],
            sources=full_pipeline_data["sources"],
        )
        assert "nodes" in result
        assert os.path.exists(result["nodes"])

        content = read_text(result["nodes"])
        assert "MERGE" in content
        assert "Agent" in content
        assert "Violation" in content
        assert "Incident" in content

    def test_generates_relationships(self, tmp_dir, full_pipeline_data):
        result = generate_cypher_scripts(
            full_pipeline_data["agents"],
            full_pipeline_data["violations"],
            full_pipeline_data["incidents"],
            tmp_dir,
            relationships=full_pipeline_data["relationships"],
        )
        assert "relationships" in result
        content = read_text(result["relationships"])
        assert "COMMITTED" in content
        assert "INVOLVED_IN" in content

    def test_empty_data(self, tmp_dir):
        result = generate_cypher_scripts([], [], [], tmp_dir)
        assert "nodes" in result

    def test_creates_output_dir(self, tmp_dir):
        out = os.path.join(tmp_dir, "new_dir")
        generate_cypher_scripts([{"id": "a1", "name": "Test"}], [], [], out)
        assert os.path.isdir(out)


class TestGenerateJsonExport:
    def test_exports_all_types(self, tmp_dir, full_pipeline_data):
        result = generate_json_export(full_pipeline_data, tmp_dir)
        assert "agents" in result
        assert "violations" in result
        assert "incidents" in result

        agents = read_json(result["agents"])
        assert len(agents) == 3

    def test_skips_empty(self, tmp_dir):
        data = {"agents": [{"id": "a1"}], "violations": []}
        result = generate_json_export(data, tmp_dir)
        assert "agents" in result
        assert "violations" not in result

    def test_strips_internal_keys(self, tmp_dir):
        data = {"agents": [{"id": "a1", "name": "Test", "_merged": True}]}
        result = generate_json_export(data, tmp_dir)
        agents = read_json(result["agents"])
        assert "_merged" not in agents[0]

    def test_serializes_dates(self, tmp_dir):
        from datetime import date
        data = {"agents": [{"id": "a1", "date": date(2025, 1, 1)}]}
        result = generate_json_export(data, tmp_dir)
        agents = read_json(result["agents"])
        assert agents[0]["date"] == "2025-01-01"


class TestValidateNeo4jReadiness:
    def test_valid_data(self, full_pipeline_data):
        is_ready, issues = validate_neo4j_readiness(full_pipeline_data)
        assert is_ready is True
        assert issues == []

    def test_missing_id(self):
        data = {"agents": [{"name": "No ID"}], "violations": [], "incidents": [], "relationships": []}
        is_ready, issues = validate_neo4j_readiness(data)
        assert is_ready is False
        assert any("missing 'id'" in i for i in issues)

    def test_duplicate_ids(self):
        data = {
            "agents": [{"id": "dup"}, {"id": "dup"}],
            "violations": [],
            "incidents": [],
            "relationships": [],
        }
        is_ready, issues = validate_neo4j_readiness(data)
        assert is_ready is False
        assert any("duplicate" in i for i in issues)

    def test_broken_references(self):
        data = {
            "agents": [{"id": "a1"}],
            "violations": [],
            "incidents": [],
            "relationships": [{"source_id": "a1", "target_id": "missing"}],
        }
        is_ready, issues = validate_neo4j_readiness(data)
        assert is_ready is False

    def test_empty_data(self):
        data = {"agents": [], "violations": [], "incidents": [], "relationships": []}
        is_ready, issues = validate_neo4j_readiness(data)
        assert is_ready is True
