"""Tests for validation utilities."""

import pytest

from accountability_pipeline.models.validation import (
    SCHEMA_MAP,
    check_referential_integrity,
    get_schema_fields,
    validate_batch,
    validate_record,
)


class TestValidateRecord:
    def test_valid_agent(self, sample_agent_dict):
        is_valid, errors = validate_record(sample_agent_dict, "agent")
        assert is_valid is True
        assert errors == []

    def test_invalid_agent_empty_name(self):
        is_valid, errors = validate_record({"name": ""}, "agent")
        assert is_valid is False
        assert len(errors) > 0

    def test_valid_violation(self, sample_violation_dict):
        is_valid, errors = validate_record(sample_violation_dict, "violation")
        assert is_valid is True

    def test_invalid_violation_no_description(self):
        is_valid, errors = validate_record({"type": "abuse"}, "violation")
        assert is_valid is False

    def test_valid_incident(self, sample_incident_dict):
        is_valid, errors = validate_record(sample_incident_dict, "incident")
        assert is_valid is True

    def test_valid_employee(self, sample_employee_dict):
        is_valid, errors = validate_record(sample_employee_dict, "employee")
        assert is_valid is True

    def test_valid_source(self, sample_source_dict):
        is_valid, errors = validate_record(sample_source_dict, "source")
        assert is_valid is True

    def test_valid_relationship(self, sample_relationship_dict):
        is_valid, errors = validate_record(sample_relationship_dict, "relationship")
        assert is_valid is True

    def test_invalid_relationship_same_ids(self):
        is_valid, errors = validate_record(
            {"source_id": "x", "target_id": "x", "relationship_type": "COMMITTED"},
            "relationship",
        )
        assert is_valid is False

    def test_unknown_schema_type(self):
        with pytest.raises(ValueError, match="Unknown schema type"):
            validate_record({}, "nonexistent")


class TestValidateBatch:
    def test_all_valid(self, sample_agent_dict):
        valid, invalid = validate_batch([sample_agent_dict, sample_agent_dict], "agent")
        assert len(valid) == 2
        assert len(invalid) == 0

    def test_mixed_validity(self, sample_agent_dict):
        records = [sample_agent_dict, {"name": ""}]
        valid, invalid = validate_batch(records, "agent")
        assert len(valid) == 1
        assert len(invalid) == 1
        assert "errors" in invalid[0]
        assert "record" in invalid[0]

    def test_all_invalid(self):
        valid, invalid = validate_batch([{"name": ""}, {}], "agent")
        assert len(valid) == 0
        assert len(invalid) == 2

    def test_empty_batch(self):
        valid, invalid = validate_batch([], "agent")
        assert valid == []
        assert invalid == []


class TestCheckReferentialIntegrity:
    def test_valid_references(self):
        agents = [{"id": "a1"}]
        violations = [{"id": "v1"}]
        incidents = [{"id": "i1"}]
        relationships = [
            {"source_id": "a1", "target_id": "v1"},
        ]
        is_valid, errors = check_referential_integrity(agents, violations, incidents, relationships)
        assert is_valid is True
        assert errors == []

    def test_missing_source_reference(self):
        agents = [{"id": "a1"}]
        relationships = [{"source_id": "missing", "target_id": "a1"}]
        is_valid, errors = check_referential_integrity(agents, [], [], relationships)
        assert is_valid is False
        assert any("missing" in e for e in errors)

    def test_missing_target_reference(self):
        agents = [{"id": "a1"}]
        relationships = [{"source_id": "a1", "target_id": "missing"}]
        is_valid, errors = check_referential_integrity(agents, [], [], relationships)
        assert is_valid is False

    def test_empty_relationships(self):
        is_valid, errors = check_referential_integrity([], [], [], [])
        assert is_valid is True


class TestGetSchemaFields:
    def test_agent_schema(self):
        schema = get_schema_fields("agent")
        assert "properties" in schema
        assert "name" in schema["properties"]

    def test_violation_schema(self):
        schema = get_schema_fields("violation")
        assert "properties" in schema

    def test_unknown_type(self):
        with pytest.raises(ValueError):
            get_schema_fields("unknown")

    def test_all_schema_types(self):
        for schema_type in SCHEMA_MAP:
            schema = get_schema_fields(schema_type)
            assert isinstance(schema, dict)
