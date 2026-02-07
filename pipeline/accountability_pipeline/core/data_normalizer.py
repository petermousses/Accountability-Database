"""Data normalization and deduplication for the accountability pipeline.

Handles fuzzy name matching, agent deduplication, violation deduplication,
and schema validation with confidence scoring.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from accountability_pipeline.models.schemas import (
    AgentModel,
    VerificationStatus,
    ViolationModel,
)
from accountability_pipeline.models.validation import validate_record
from accountability_pipeline.utils.logger import get_logger
from accountability_pipeline.utils.string_matcher import (
    calculate_name_similarity,
    find_duplicates_in_records,
    fuzzy_match_names,
)

logger = get_logger(__name__)


def normalize_names(names_list: List[str]) -> List[Dict[str, Any]]:
    """Normalize a list of names and group likely duplicates.

    For each unique name group, returns a canonical form and all variations.

    Args:
        names_list: List of raw name strings.

    Returns:
        List of dictionaries with:
        - canonical: The chosen canonical name (longest in group).
        - variations: All name variations in the group.
        - count: Number of variations.
    """
    if not names_list:
        return []

    groups = fuzzy_match_names(names_list, threshold=0.85)

    results = []
    for group in groups:
        canonical = max(group, key=len)
        results.append({
            "canonical": canonical,
            "variations": sorted(group),
            "count": len(group),
        })

    return sorted(results, key=lambda x: x["canonical"])


def deduplicate_agents(
    agents_list: List[Dict[str, Any]],
    confidence_threshold: float = 0.85,
) -> List[Dict[str, Any]]:
    """Deduplicate agents using fuzzy name matching and field comparison.

    When duplicates are found, merges them by keeping the most complete record
    and annotating with confidence scores.

    Args:
        agents_list: List of agent dictionaries.
        confidence_threshold: Minimum similarity to consider as duplicate.

    Returns:
        Deduplicated list with merged records and confidence metadata.
    """
    if not agents_list:
        return []

    duplicate_groups = find_duplicates_in_records(
        agents_list, name_field="name", threshold=confidence_threshold
    )

    merged_indices: set = set()
    result: List[Dict[str, Any]] = []

    for group in duplicate_groups:
        if not group:
            continue

        records = [agents_list[i] for i in group]
        merged = _merge_agent_records(records)
        result.append(merged)

        for idx in group:
            merged_indices.add(idx)

        logger.info(
            "agents_merged",
            count=len(records),
            names=[r.get("name", "") for r in records],
        )

    for i, agent in enumerate(agents_list):
        if i not in merged_indices:
            agent_copy = dict(agent)
            agent_copy.setdefault("_dedup_confidence", 1.0)
            agent_copy.setdefault("_merged_from", [agent.get("name", "")])
            result.append(agent_copy)

    return result


def _merge_agent_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple agent records into one canonical record.

    Strategy: keep the most complete record as the base and fill in
    missing fields from others. Annotate with merge metadata.
    """
    scored = []
    for r in records:
        completeness = sum(1 for v in r.values() if v is not None and v != "")
        scored.append((completeness, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    base = dict(scored[0][1])

    for _, other in scored[1:]:
        for key, value in other.items():
            if key.startswith("_"):
                continue
            if (base.get(key) is None or base.get(key) == "") and value is not None and value != "":
                base[key] = value

    names = [r.get("name", "") for r in records if r.get("name")]
    similarities = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            similarities.append(calculate_name_similarity(names[i], names[j]))

    base["_dedup_confidence"] = round(min(similarities) if similarities else 1.0, 4)
    base["_merged_from"] = names
    base["_merge_count"] = len(records)

    if base.get("status") == VerificationStatus.OUT_OF_FRAME.value:
        pass
    elif any(r.get("status") == VerificationStatus.CONFIRMED.value for r in records):
        base["status"] = VerificationStatus.CONFIRMED.value

    return base


def deduplicate_violations(violations_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identify and merge duplicate violation records.

    Violations are considered duplicates if they share:
    - Same type AND same date, OR
    - Same type AND same location AND overlapping description

    Args:
        violations_list: List of violation dictionaries.

    Returns:
        Deduplicated list with merge annotations.
    """
    if not violations_list:
        return []

    n = len(violations_list)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(n):
        for j in range(i + 1, n):
            if _violations_match(violations_list[i], violations_list[j]):
                union(i, j)

    groups: Dict[int, List[int]] = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(i)

    result = []
    for indices in groups.values():
        if len(indices) == 1:
            v = dict(violations_list[indices[0]])
            v.setdefault("_dedup_confidence", 1.0)
            result.append(v)
        else:
            records = [violations_list[i] for i in indices]
            merged = _merge_violation_records(records)
            result.append(merged)
            logger.info("violations_merged", count=len(records))

    return result


def _violations_match(v1: Dict, v2: Dict) -> bool:
    """Check if two violations are likely duplicates."""
    if v1.get("type") != v2.get("type"):
        return False

    if v1.get("date") and v2.get("date") and v1["date"] == v2["date"]:
        return True

    if v1.get("location") and v2.get("location") and v1["location"] == v2["location"]:
        desc1 = v1.get("description", "")
        desc2 = v2.get("description", "")
        if desc1 and desc2:
            sim = calculate_name_similarity(desc1, desc2)
            return sim >= 0.7

    return False


def _merge_violation_records(records: List[Dict]) -> Dict:
    """Merge multiple violation records."""
    scored = [(sum(1 for v in r.values() if v is not None and v != ""), r) for r in records]
    scored.sort(key=lambda x: x[0], reverse=True)
    base = dict(scored[0][1])

    for _, other in scored[1:]:
        for key, value in other.items():
            if key.startswith("_"):
                continue
            if (base.get(key) is None or base.get(key) == "") and value is not None and value != "":
                base[key] = value

    base["_dedup_confidence"] = 0.9
    base["_merge_count"] = len(records)
    return base


def validate_schema(data: Dict[str, Any], schema_type: str) -> Tuple[bool, List[str]]:
    """Validate data against a schema type.

    Convenience wrapper around models.validation.validate_record.

    Args:
        data: Record data dictionary.
        schema_type: Schema type name.

    Returns:
        Tuple of (is_valid, error_messages).
    """
    return validate_record(data, schema_type)


def normalize_and_validate_agents(
    raw_agents: List[Dict[str, Any]],
    confidence_threshold: float = 0.85,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Full normalization pipeline for agents: validate, then deduplicate.

    Args:
        raw_agents: List of raw agent dictionaries.
        confidence_threshold: Deduplication threshold.

    Returns:
        Tuple of (valid_deduplicated_agents, invalid_records).
    """
    valid = []
    invalid = []

    for agent in raw_agents:
        is_valid, errors = validate_schema(agent, "agent")
        if is_valid:
            valid.append(agent)
        else:
            invalid.append({"record": agent, "errors": errors})

    deduped = deduplicate_agents(valid, confidence_threshold=confidence_threshold)

    logger.info(
        "agent_normalization_complete",
        input_count=len(raw_agents),
        valid_count=len(valid),
        invalid_count=len(invalid),
        deduped_count=len(deduped),
    )

    return deduped, invalid
