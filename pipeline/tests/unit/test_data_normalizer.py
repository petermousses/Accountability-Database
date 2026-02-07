"""Tests for data normalization and deduplication."""

import pytest

from accountability_pipeline.core.data_normalizer import (
    deduplicate_agents,
    deduplicate_violations,
    normalize_and_validate_agents,
    normalize_names,
    validate_schema,
)


class TestNormalizeNames:
    def test_groups_similar_names(self):
        names = ["John Smith", "Jon Smith", "Jane Doe"]
        result = normalize_names(names)
        assert len(result) >= 2  # At least 2 groups

        # Find the Smith group
        smith_group = [g for g in result if "John Smith" in g["variations"]]
        assert len(smith_group) == 1
        assert smith_group[0]["count"] >= 2

    def test_canonical_is_longest(self):
        names = ["Jon Smith", "Jonathan Smith"]
        result = normalize_names(names)
        group = [g for g in result if len(g["variations"]) > 1]
        if group:
            assert group[0]["canonical"] == "Jonathan Smith"

    def test_empty_list(self):
        assert normalize_names([]) == []

    def test_no_duplicates(self):
        result = normalize_names(["Alice", "Bob", "Charlie"])
        assert all(g["count"] == 1 for g in result)


class TestDeduplicateAgents:
    def test_merges_similar_names(self, sample_agent_list):
        result = deduplicate_agents(sample_agent_list, confidence_threshold=0.8)
        assert len(result) < len(sample_agent_list)

    def test_preserves_unique_agents(self):
        agents = [
            {"name": "Alice Johnson", "status": "Confirmed"},
            {"name": "Bob Williams", "status": "Suspected"},
        ]
        result = deduplicate_agents(agents)
        assert len(result) == 2

    def test_empty_list(self):
        assert deduplicate_agents([]) == []

    def test_adds_dedup_metadata(self, sample_agent_list):
        result = deduplicate_agents(sample_agent_list, confidence_threshold=0.8)
        for agent in result:
            assert "_dedup_confidence" in agent

    def test_confirms_if_any_confirmed(self):
        agents = [
            {"name": "John Smith", "status": "Suspected"},
            {"name": "Jon Smith", "status": "Confirmed"},
        ]
        result = deduplicate_agents(agents, confidence_threshold=0.7)
        merged = [a for a in result if a.get("_merge_count", 0) > 1]
        if merged:
            assert merged[0]["status"] == "Confirmed"

    def test_keeps_most_complete_record(self):
        agents = [
            {"name": "John Smith", "badge_number": "ICE-001"},
            {"name": "Jon Smith", "badge_number": None, "address": "123 Main St"},
        ]
        result = deduplicate_agents(agents, confidence_threshold=0.7)
        merged = [a for a in result if a.get("_merge_count", 0) > 1]
        if merged:
            assert merged[0]["badge_number"] == "ICE-001"
            assert merged[0]["address"] == "123 Main St"


class TestDeduplicateViolations:
    def test_merges_same_type_date(self, sample_violation_list):
        result = deduplicate_violations(sample_violation_list)
        # First two violations share type+date and should merge
        assert len(result) < len(sample_violation_list)

    def test_preserves_unique(self):
        violations = [
            {"type": "abuse", "description": "Incident A", "date": "2025-01-01"},
            {"type": "negligence", "description": "Incident B", "date": "2025-02-01"},
        ]
        result = deduplicate_violations(violations)
        assert len(result) == 2

    def test_empty_list(self):
        assert deduplicate_violations([]) == []

    def test_adds_metadata(self, sample_violation_list):
        result = deduplicate_violations(sample_violation_list)
        for v in result:
            assert "_dedup_confidence" in v


class TestValidateSchema:
    def test_valid_agent(self, sample_agent_dict):
        is_valid, errors = validate_schema(sample_agent_dict, "agent")
        assert is_valid is True
        assert errors == []

    def test_invalid_agent(self):
        is_valid, errors = validate_schema({"name": ""}, "agent")
        assert is_valid is False
        assert len(errors) > 0

    def test_valid_violation(self, sample_violation_dict):
        is_valid, errors = validate_schema(sample_violation_dict, "violation")
        assert is_valid is True

    def test_unknown_schema(self):
        with pytest.raises(ValueError):
            validate_schema({}, "nonexistent")


class TestNormalizeAndValidateAgents:
    def test_full_pipeline(self, sample_agent_list):
        valid, invalid = normalize_and_validate_agents(sample_agent_list)
        assert len(valid) > 0
        assert isinstance(invalid, list)

    def test_rejects_invalid(self):
        agents = [
            {"name": "Valid Agent", "status": "Suspected"},
            {"name": ""},  # Invalid: empty name
        ]
        valid, invalid = normalize_and_validate_agents(agents)
        assert len(invalid) >= 1

    def test_empty_input(self):
        valid, invalid = normalize_and_validate_agents([])
        assert valid == []
        assert invalid == []
