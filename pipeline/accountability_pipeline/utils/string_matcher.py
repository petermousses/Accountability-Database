"""Fuzzy string matching utilities for name deduplication.

Uses rapidfuzz for high-performance fuzzy matching with configurable thresholds.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process


def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two names using weighted ratio.

    Uses token_sort_ratio which handles word reordering
    (e.g., "John Smith" vs "Smith, John").

    Args:
        name1: First name.
        name2: Second name.

    Returns:
        Similarity score between 0.0 and 1.0.
    """
    if not name1 or not name2:
        return 0.0

    n1 = _normalize_name(name1)
    n2 = _normalize_name(name2)

    if n1 == n2:
        return 1.0

    token_sort = fuzz.token_sort_ratio(n1, n2) / 100.0
    token_set = fuzz.token_set_ratio(n1, n2) / 100.0
    partial = fuzz.partial_ratio(n1, n2) / 100.0

    return round(0.4 * token_sort + 0.4 * token_set + 0.2 * partial, 4)


def find_best_match(
    query: str,
    candidates: List[str],
    threshold: float = 0.85,
    limit: int = 5,
) -> List[Tuple[str, float]]:
    """Find the best matching names from a list of candidates.

    Args:
        query: Name to search for.
        candidates: List of candidate names to match against.
        threshold: Minimum similarity score (0.0-1.0) to include.
        limit: Maximum number of results.

    Returns:
        List of (candidate_name, similarity_score) tuples, sorted by score descending.
    """
    if not query or not candidates:
        return []

    normalized_query = _normalize_name(query)
    normalized_candidates = [_normalize_name(c) for c in candidates]

    results = process.extract(
        normalized_query,
        normalized_candidates,
        scorer=fuzz.token_sort_ratio,
        limit=limit,
    )

    matches = []
    for match_text, score, idx in results:
        normalized_score = score / 100.0
        if normalized_score >= threshold:
            matches.append((candidates[idx], round(normalized_score, 4)))

    return matches


def fuzzy_match_names(
    names: List[str],
    threshold: float = 0.85,
) -> List[List[str]]:
    """Group names that likely refer to the same person.

    Uses single-linkage clustering: if A matches B and B matches C,
    all three are grouped together.

    Args:
        names: List of names to cluster.
        threshold: Minimum similarity for two names to be considered a match.

    Returns:
        List of name groups. Each group is a list of names that likely refer
        to the same person.
    """
    if not names:
        return []

    n = len(names)
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
            sim = calculate_name_similarity(names[i], names[j])
            if sim >= threshold:
                union(i, j)

    groups: Dict[int, List[str]] = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(names[i])

    return list(groups.values())


def find_duplicates_in_records(
    records: List[Dict[str, Any]],
    name_field: str = "name",
    threshold: float = 0.85,
) -> List[List[int]]:
    """Find groups of potentially duplicate records based on name similarity.

    Args:
        records: List of record dictionaries.
        name_field: The field containing the name to compare.
        threshold: Minimum similarity for a match.

    Returns:
        List of groups, where each group is a list of record indices
        that are potential duplicates.
    """
    names = [r.get(name_field, "") for r in records]
    name_groups = fuzzy_match_names(names, threshold=threshold)

    index_groups = []
    for group in name_groups:
        if len(group) > 1:
            indices = [i for i, name in enumerate(names) if name in group]
            index_groups.append(indices)

    return index_groups


def _normalize_name(name: str) -> str:
    """Normalize a name for comparison.

    Lowercases, strips whitespace, removes common titles and suffixes.

    Args:
        name: Raw name string.

    Returns:
        Normalized name.
    """
    result = name.lower().strip()

    titles = ["mr.", "mrs.", "ms.", "dr.", "agent", "officer", "det.", "sgt.", "lt.", "cpt."]
    for title in titles:
        if result.startswith(title + " "):
            result = result[len(title):].strip()

    suffixes = [" jr.", " sr.", " ii", " iii", " iv"]
    for suffix in suffixes:
        if result.endswith(suffix):
            result = result[:-len(suffix)].strip()

    result = result.replace(",", " ").replace(".", " ")
    result = " ".join(result.split())

    return result
