"""Tests for correlation analysis."""

import os

import pytest

from accountability_pipeline.core.correlation_analyzer import (
    find_agent_patterns,
    find_cross_incident_connections,
    generate_analysis_report,
)
from accountability_pipeline.utils.file_handler import read_text


class TestFindAgentPatterns:
    def test_basic_analysis(
        self, sample_agents_for_analysis, sample_violations_for_analysis, sample_relationships
    ):
        findings = find_agent_patterns(
            sample_agents_for_analysis,
            sample_violations_for_analysis,
            sample_relationships,
        )
        assert "repeat_offenders" in findings
        assert "co_perpetrators" in findings
        assert "temporal_patterns" in findings
        assert "geographic_patterns" in findings
        assert "severity_distribution" in findings
        assert "summary_stats" in findings

    def test_finds_repeat_offenders(
        self, sample_agents_for_analysis, sample_violations_for_analysis, sample_relationships
    ):
        findings = find_agent_patterns(
            sample_agents_for_analysis,
            sample_violations_for_analysis,
            sample_relationships,
        )
        repeat = findings["repeat_offenders"]
        # agent-001 has 2 COMMITTED relationships
        assert len(repeat) >= 1
        assert repeat[0]["violation_count"] >= 2

    def test_finds_co_perpetrators(
        self, sample_agents_for_analysis, sample_violations_for_analysis, sample_relationships
    ):
        findings = find_agent_patterns(
            sample_agents_for_analysis,
            sample_violations_for_analysis,
            sample_relationships,
        )
        co_perps = findings["co_perpetrators"]
        # agent-001 and agent-002 share violation-001 via COMMITTED
        assert len(co_perps) >= 1

    def test_summary_stats(
        self, sample_agents_for_analysis, sample_violations_for_analysis, sample_relationships
    ):
        findings = find_agent_patterns(
            sample_agents_for_analysis,
            sample_violations_for_analysis,
            sample_relationships,
        )
        stats = findings["summary_stats"]
        assert stats["total_agents"] == 3
        assert stats["total_violations"] == 3
        assert stats["total_relationships"] == len(sample_relationships)

    def test_empty_data(self):
        findings = find_agent_patterns([], [], [])
        assert findings["summary_stats"]["total_agents"] == 0

    def test_no_relationships(self, sample_agents_for_analysis, sample_violations_for_analysis):
        findings = find_agent_patterns(
            sample_agents_for_analysis, sample_violations_for_analysis, None
        )
        assert findings["repeat_offenders"] == []

    def test_severity_distribution(
        self, sample_agents_for_analysis, sample_violations_for_analysis
    ):
        findings = find_agent_patterns(
            sample_agents_for_analysis, sample_violations_for_analysis
        )
        sev = findings["severity_distribution"]
        assert "severe" in sev
        assert "critical" in sev

    def test_geographic_patterns(
        self, sample_agents_for_analysis, sample_violations_for_analysis
    ):
        findings = find_agent_patterns(
            sample_agents_for_analysis, sample_violations_for_analysis
        )
        geo = findings["geographic_patterns"]
        assert "El Paso, TX" in geo
        assert geo["El Paso, TX"] == 2

    def test_temporal_patterns(
        self, sample_agents_for_analysis, sample_violations_for_analysis
    ):
        findings = find_agent_patterns(
            sample_agents_for_analysis, sample_violations_for_analysis
        )
        temporal = findings["temporal_patterns"]
        assert "2025-03" in temporal


class TestFindCrossIncidentConnections:
    def test_similar_incidents(self):
        incidents = [
            {"id": "i-1", "description": "Excessive force used during detention processing at facility"},
            {"id": "i-2", "description": "Excessive force during detention processing at the facility"},
            {"id": "i-3", "description": "Medical neglect in transport vehicle"},
        ]
        connections = find_cross_incident_connections(incidents, threshold=0.7)
        assert len(connections) >= 1
        assert connections[0]["incident_1_id"] == "i-1"
        assert connections[0]["incident_2_id"] == "i-2"
        assert connections[0]["similarity"] >= 0.7

    def test_no_similar_incidents(self):
        incidents = [
            {"id": "i-1", "description": "Type A event"},
            {"id": "i-2", "description": "Completely different situation"},
        ]
        connections = find_cross_incident_connections(incidents, threshold=0.9)
        assert len(connections) == 0

    def test_empty_incidents(self):
        connections = find_cross_incident_connections([])
        assert connections == []


class TestGenerateAnalysisReport:
    def test_generates_markdown(
        self, tmp_dir, sample_agents_for_analysis, sample_violations_for_analysis, sample_relationships
    ):
        findings = find_agent_patterns(
            sample_agents_for_analysis, sample_violations_for_analysis, sample_relationships
        )
        output_path = os.path.join(tmp_dir, "report.md")
        result = generate_analysis_report(findings, output_path)

        assert result == output_path
        assert os.path.exists(output_path)

        content = read_text(output_path)
        assert "# Accountability Analysis Report" in content
        assert "Summary Statistics" in content
        assert "Total Agents" in content

    def test_report_includes_repeat_offenders(
        self, tmp_dir, sample_agents_for_analysis, sample_violations_for_analysis, sample_relationships
    ):
        findings = find_agent_patterns(
            sample_agents_for_analysis, sample_violations_for_analysis, sample_relationships
        )
        output_path = os.path.join(tmp_dir, "report.md")
        generate_analysis_report(findings, output_path)
        content = read_text(output_path)
        assert "Repeat Offenders" in content

    def test_empty_findings(self, tmp_dir):
        findings = {
            "repeat_offenders": [],
            "co_perpetrators": [],
            "temporal_patterns": {},
            "geographic_patterns": {},
            "severity_distribution": {},
            "violation_type_distribution": {},
            "summary_stats": {"total_agents": 0, "total_violations": 0},
            "generated_at": "2025-01-01T00:00:00",
        }
        output_path = os.path.join(tmp_dir, "empty_report.md")
        result = generate_analysis_report(findings, output_path)
        assert os.path.exists(result)
