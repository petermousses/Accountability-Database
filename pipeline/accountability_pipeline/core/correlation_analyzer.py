"""Correlation analysis for accountability data.

Finds patterns across agents, violations, and incidents.
Generates analysis reports in markdown format.
"""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from accountability_pipeline.utils.file_handler import write_text
from accountability_pipeline.utils.logger import get_logger
from accountability_pipeline.utils.string_matcher import calculate_name_similarity

logger = get_logger(__name__)


def find_agent_patterns(
    agents_db: List[Dict[str, Any]],
    violations_db: List[Dict[str, Any]],
    relationships: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Find patterns across agents and violations.

    Identifies:
    - Repeat offenders (agents linked to multiple violations)
    - Co-perpetrator networks (agents appearing in same incidents)
    - Temporal patterns (violation clusters by time)
    - Geographic patterns (violation clusters by location)
    - Severity distribution

    Args:
        agents_db: List of agent records.
        violations_db: List of violation records.
        relationships: Optional list of relationship records linking agents to violations.

    Returns:
        Dictionary of analysis findings.
    """
    findings: Dict[str, Any] = {
        "repeat_offenders": [],
        "co_perpetrators": [],
        "temporal_patterns": {},
        "geographic_patterns": {},
        "severity_distribution": {},
        "violation_type_distribution": {},
        "summary_stats": {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Build agent-violation mappings from relationships
    agent_violations: Dict[str, List[str]] = defaultdict(list)
    violation_agents: Dict[str, List[str]] = defaultdict(list)

    if relationships:
        for rel in relationships:
            if rel.get("relationship_type") in ("COMMITTED", "INVOLVED_IN"):
                source_id = rel.get("source_id", "")
                target_id = rel.get("target_id", "")
                agent_violations[source_id].append(target_id)
                violation_agents[target_id].append(source_id)

    # Repeat offenders
    agent_name_map = {a.get("id", ""): a.get("name", "Unknown") for a in agents_db}
    repeat = []
    for agent_id, viol_ids in agent_violations.items():
        if len(viol_ids) > 1:
            repeat.append({
                "agent_id": agent_id,
                "agent_name": agent_name_map.get(agent_id, "Unknown"),
                "violation_count": len(viol_ids),
                "violation_ids": viol_ids,
            })
    findings["repeat_offenders"] = sorted(repeat, key=lambda x: x["violation_count"], reverse=True)

    # Co-perpetrator networks
    co_perps: Dict[str, set] = defaultdict(set)
    for viol_id, agent_ids in violation_agents.items():
        if len(agent_ids) > 1:
            for a_id in agent_ids:
                co_perps[a_id].update(set(agent_ids) - {a_id})

    findings["co_perpetrators"] = [
        {
            "agent_id": agent_id,
            "agent_name": agent_name_map.get(agent_id, "Unknown"),
            "co_perpetrator_ids": sorted(partners),
            "co_perpetrator_names": [agent_name_map.get(p, "Unknown") for p in sorted(partners)],
        }
        for agent_id, partners in co_perps.items()
    ]

    # Temporal patterns
    date_counts: Counter = Counter()
    for v in violations_db:
        d = v.get("date")
        if d:
            date_str = str(d)
            year_month = date_str[:7] if len(date_str) >= 7 else date_str
            date_counts[year_month] += 1
    findings["temporal_patterns"] = dict(date_counts.most_common())

    # Geographic patterns
    location_counts: Counter = Counter()
    for v in violations_db:
        loc = v.get("location")
        if loc:
            location_counts[loc] += 1
    findings["geographic_patterns"] = dict(location_counts.most_common())

    # Severity distribution
    severity_counts: Counter = Counter()
    for v in violations_db:
        sev = v.get("severity", "unknown")
        severity_counts[sev] += 1
    findings["severity_distribution"] = dict(severity_counts)

    # Violation type distribution
    type_counts: Counter = Counter()
    for v in violations_db:
        vtype = v.get("type", "unknown")
        type_counts[vtype] += 1
    findings["violation_type_distribution"] = dict(type_counts)

    # Summary stats
    findings["summary_stats"] = {
        "total_agents": len(agents_db),
        "total_violations": len(violations_db),
        "total_relationships": len(relationships) if relationships else 0,
        "agents_with_violations": len(agent_violations),
        "repeat_offender_count": len(findings["repeat_offenders"]),
        "co_perpetrator_network_size": len(findings["co_perpetrators"]),
        "unique_locations": len(location_counts),
    }

    logger.info("analysis_complete", stats=findings["summary_stats"])
    return findings


def find_cross_incident_connections(
    incidents: List[Dict[str, Any]],
    threshold: float = 0.7,
) -> List[Dict[str, Any]]:
    """Find connections between incidents based on description similarity.

    Args:
        incidents: List of incident records.
        threshold: Minimum similarity to consider connected.

    Returns:
        List of connection records with similarity scores.
    """
    connections = []
    for i in range(len(incidents)):
        for j in range(i + 1, len(incidents)):
            desc_i = incidents[i].get("description", "")
            desc_j = incidents[j].get("description", "")

            if desc_i and desc_j:
                sim = calculate_name_similarity(desc_i, desc_j)
                if sim >= threshold:
                    connections.append({
                        "incident_1_id": incidents[i].get("id", ""),
                        "incident_2_id": incidents[j].get("id", ""),
                        "similarity": sim,
                        "shared_location": (
                            incidents[i].get("location") == incidents[j].get("location")
                            and incidents[i].get("location") is not None
                        ),
                    })

    return sorted(connections, key=lambda x: x["similarity"], reverse=True)


def generate_analysis_report(findings: Dict[str, Any], output_path: str) -> str:
    """Generate a markdown analysis report from findings.

    Args:
        findings: Analysis findings from find_agent_patterns.
        output_path: Path to write the markdown report.

    Returns:
        The output file path.
    """
    stats = findings.get("summary_stats", {})
    lines = [
        "# Accountability Analysis Report",
        "",
        f"Generated: {findings.get('generated_at', datetime.now(timezone.utc).isoformat())}",
        "",
        "## Summary Statistics",
        "",
        f"- **Total Agents**: {stats.get('total_agents', 0)}",
        f"- **Total Violations**: {stats.get('total_violations', 0)}",
        f"- **Agents with Violations**: {stats.get('agents_with_violations', 0)}",
        f"- **Repeat Offenders**: {stats.get('repeat_offender_count', 0)}",
        f"- **Co-Perpetrator Networks**: {stats.get('co_perpetrator_network_size', 0)}",
        f"- **Unique Locations**: {stats.get('unique_locations', 0)}",
        "",
    ]

    # Repeat offenders
    repeat = findings.get("repeat_offenders", [])
    if repeat:
        lines.extend([
            "## Repeat Offenders",
            "",
            "| Agent | Violation Count |",
            "|-------|----------------|",
        ])
        for r in repeat[:20]:
            lines.append(f"| {r['agent_name']} | {r['violation_count']} |")
        lines.append("")

    # Co-perpetrators
    co_perps = findings.get("co_perpetrators", [])
    if co_perps:
        lines.extend([
            "## Co-Perpetrator Networks",
            "",
        ])
        for cp in co_perps[:20]:
            partners = ", ".join(cp["co_perpetrator_names"])
            lines.append(f"- **{cp['agent_name']}** connected to: {partners}")
        lines.append("")

    # Severity distribution
    severity = findings.get("severity_distribution", {})
    if severity:
        lines.extend([
            "## Severity Distribution",
            "",
            "| Severity | Count |",
            "|----------|-------|",
        ])
        for sev, count in sorted(severity.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {sev} | {count} |")
        lines.append("")

    # Violation types
    vtypes = findings.get("violation_type_distribution", {})
    if vtypes:
        lines.extend([
            "## Violation Types",
            "",
            "| Type | Count |",
            "|------|-------|",
        ])
        for vtype, count in sorted(vtypes.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {vtype} | {count} |")
        lines.append("")

    # Geographic patterns
    geo = findings.get("geographic_patterns", {})
    if geo:
        lines.extend([
            "## Geographic Patterns",
            "",
            "| Location | Incidents |",
            "|----------|-----------|",
        ])
        for loc, count in sorted(geo.items(), key=lambda x: x[1], reverse=True)[:20]:
            lines.append(f"| {loc} | {count} |")
        lines.append("")

    # Temporal patterns
    temporal = findings.get("temporal_patterns", {})
    if temporal:
        lines.extend([
            "## Temporal Patterns",
            "",
            "| Period | Incidents |",
            "|--------|-----------|",
        ])
        for period, count in sorted(temporal.items()):
            lines.append(f"| {period} | {count} |")
        lines.append("")

    report = "\n".join(lines)
    write_text(report, output_path)
    logger.info("report_generated", path=output_path, lines=len(lines))
    return output_path
