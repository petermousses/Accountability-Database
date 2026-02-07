"""Tests for string matching utilities."""

import pytest

from accountability_pipeline.utils.string_matcher import (
    _normalize_name,
    calculate_name_similarity,
    find_best_match,
    find_duplicates_in_records,
    fuzzy_match_names,
)


class TestCalculateNameSimilarity:
    def test_identical_names(self):
        assert calculate_name_similarity("John Smith", "John Smith") == 1.0

    def test_reordered_names(self):
        sim = calculate_name_similarity("John Smith", "Smith, John")
        assert sim > 0.85

    def test_nickname_variation(self):
        sim = calculate_name_similarity("Robert Johnson", "Bob Johnson")
        assert sim > 0.6

    def test_completely_different(self):
        sim = calculate_name_similarity("John Smith", "Alice Williams")
        assert sim < 0.5

    def test_empty_names(self):
        assert calculate_name_similarity("", "John") == 0.0
        assert calculate_name_similarity("John", "") == 0.0
        assert calculate_name_similarity("", "") == 0.0

    def test_case_insensitive(self):
        sim = calculate_name_similarity("JOHN SMITH", "john smith")
        assert sim == 1.0

    def test_with_titles(self):
        sim = calculate_name_similarity("Agent John Smith", "John Smith")
        assert sim > 0.85

    def test_with_suffixes(self):
        sim = calculate_name_similarity("John Smith Jr.", "John Smith")
        assert sim > 0.85


class TestFindBestMatch:
    def test_exact_match(self):
        candidates = ["John Smith", "Jane Doe", "Bob Wilson"]
        matches = find_best_match("John Smith", candidates, threshold=0.8)
        assert len(matches) >= 1
        assert matches[0][0] == "John Smith"
        assert matches[0][1] == 1.0

    def test_fuzzy_match(self):
        candidates = ["John Smith", "Jane Doe", "Bob Wilson"]
        matches = find_best_match("Jon Smith", candidates, threshold=0.7)
        assert len(matches) >= 1
        assert matches[0][0] == "John Smith"

    def test_no_match_above_threshold(self):
        candidates = ["Alice Johnson", "Bob Williams"]
        matches = find_best_match("Xyz Abc", candidates, threshold=0.95)
        assert len(matches) == 0

    def test_empty_inputs(self):
        assert find_best_match("", ["a", "b"]) == []
        assert find_best_match("test", []) == []

    def test_limit(self):
        candidates = ["John Smith", "Jon Smith", "Johnny Smith"]
        matches = find_best_match("John Smith", candidates, threshold=0.5, limit=2)
        assert len(matches) <= 2


class TestFuzzyMatchNames:
    def test_groups_similar_names(self):
        names = ["John Smith", "Jon Smith", "Jane Doe"]
        groups = fuzzy_match_names(names, threshold=0.8)
        # John Smith and Jon Smith should be grouped
        found_group = False
        for group in groups:
            if "John Smith" in group and "Jon Smith" in group:
                found_group = True
        assert found_group

    def test_no_duplicates(self):
        names = ["Alice", "Bob", "Charlie"]
        groups = fuzzy_match_names(names, threshold=0.95)
        # Each should be in its own group
        assert len(groups) == 3

    def test_empty_list(self):
        assert fuzzy_match_names([]) == []

    def test_single_name(self):
        groups = fuzzy_match_names(["John"])
        assert len(groups) == 1
        assert groups[0] == ["John"]

    def test_all_similar(self):
        names = ["John Smith", "Jon Smith", "Johnn Smith"]
        groups = fuzzy_match_names(names, threshold=0.7)
        # All should be in one group
        assert len(groups) == 1
        assert len(groups[0]) == 3


class TestFindDuplicatesInRecords:
    def test_finds_duplicates(self, sample_agent_list):
        groups = find_duplicates_in_records(sample_agent_list, threshold=0.8)
        assert len(groups) >= 1  # Should find at least Smith duplicates

    def test_no_duplicates(self):
        records = [{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}]
        groups = find_duplicates_in_records(records, threshold=0.95)
        assert len(groups) == 0

    def test_empty_records(self):
        groups = find_duplicates_in_records([], threshold=0.85)
        assert groups == []

    def test_custom_name_field(self):
        records = [
            {"full_name": "John Smith"},
            {"full_name": "Jon Smith"},
        ]
        groups = find_duplicates_in_records(records, name_field="full_name", threshold=0.8)
        assert len(groups) >= 1


class TestNormalizeName:
    def test_lowercase(self):
        assert _normalize_name("JOHN SMITH") == "john smith"

    def test_strip_whitespace(self):
        assert _normalize_name("  John Smith  ") == "john smith"

    def test_remove_title(self):
        assert _normalize_name("Agent John Smith") == "john smith"
        assert _normalize_name("Officer Jane Doe") == "jane doe"
        assert _normalize_name("Dr. James Wilson") == "james wilson"

    def test_remove_suffix(self):
        assert _normalize_name("John Smith Jr.") == "john smith"
        assert _normalize_name("John Smith III") == "john smith"

    def test_normalize_separators(self):
        result = _normalize_name("Smith, John")
        assert result == "smith john"

    def test_collapse_whitespace(self):
        assert _normalize_name("John   Smith") == "john smith"
