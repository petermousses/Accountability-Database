"""Integration tests for the LangGraph pipeline workflow."""

import os

import pytest

from workflow.nodes import (
    analyze_node,
    error_handler_node,
    export_node,
    intake_node,
    normalize_node,
    process_documents_node,
    report_node,
)
from workflow.graph import (
    build_pipeline_graph,
    should_continue_after_intake,
    should_continue_after_processing,
    should_continue_after_analysis,
)


class TestIntakeNode:
    def test_initializes_run(self):
        state = {"documents": [{"file_path": "/test/doc.txt"}]}
        result = intake_node(state)
        assert result["run_id"].startswith("run-")
        assert result["current_stage"] == "intake"
        assert result["completed"] is False
        assert len(result["errors"]) == 0

    def test_errors_on_empty_documents(self):
        state = {"documents": []}
        result = intake_node(state)
        assert len(result["errors"]) > 0

    def test_errors_on_missing_file_path(self):
        state = {"documents": [{"file_name": "test.txt"}]}
        result = intake_node(state)
        assert len(result["errors"]) > 0

    def test_preserves_run_id(self):
        state = {"documents": [{"file_path": "/test.txt"}], "run_id": "custom-id"}
        result = intake_node(state)
        assert result["run_id"] == "custom-id"


class TestProcessDocumentsNode:
    def test_processes_text_file(self, sample_text_document, tmp_dir, monkeypatch):
        monkeypatch.setenv("PIPELINE_OUTPUT_DIR", tmp_dir)
        state = {"documents": [{"file_path": sample_text_document}], "errors": []}
        result = process_documents_node(state)
        assert len(result["raw_extractions"]) == 1
        assert len(result["ollama_requests"]) == 1
        assert result["current_stage"] == "process_documents"
        assert result["requires_human_input"] is True

    def test_handles_missing_file(self, tmp_dir, monkeypatch):
        monkeypatch.setenv("PIPELINE_OUTPUT_DIR", tmp_dir)
        state = {"documents": [{"file_path": "/nonexistent/file.txt"}], "errors": []}
        result = process_documents_node(state)
        assert len(result["errors"]) > 0

    def test_processes_multiple_files(self, sample_text_document, sample_csv_file, tmp_dir, monkeypatch):
        monkeypatch.setenv("PIPELINE_OUTPUT_DIR", tmp_dir)
        state = {
            "documents": [
                {"file_path": sample_text_document},
                {"file_path": sample_csv_file},
            ],
            "errors": [],
        }
        result = process_documents_node(state)
        assert len(result["raw_extractions"]) == 2


class TestNormalizeNode:
    def test_normalizes_extractions(self, monkeypatch, tmp_dir):
        monkeypatch.setenv("PIPELINE_OUTPUT_DIR", tmp_dir)
        state = {
            "raw_extractions": [
                {
                    "extracted_fields": {
                        "potential_names": ["John Smith", "Jon Smith"],
                    },
                },
            ],
            "ollama_responses": [],
            "errors": [],
        }
        result = normalize_node(state)
        assert "agents" in result
        assert "violations" in result
        assert result["current_stage"] == "normalize"

    def test_handles_ollama_responses(self, sample_ollama_response, monkeypatch, tmp_dir):
        monkeypatch.setenv("PIPELINE_OUTPUT_DIR", tmp_dir)
        state = {
            "raw_extractions": [],
            "ollama_responses": [sample_ollama_response],
            "errors": [],
        }
        result = normalize_node(state)
        assert len(result["agents"]) >= 2  # John Smith and Robert Johnson


class TestAnalyzeNode:
    def test_runs_analysis(
        self, sample_agents_for_analysis, sample_violations_for_analysis, sample_relationships
    ):
        state = {
            "agents": sample_agents_for_analysis,
            "violations": sample_violations_for_analysis,
            "incidents": [],
            "relationships": sample_relationships,
            "errors": [],
        }
        result = analyze_node(state)
        assert "analysis_report" in result
        assert result["analysis_report"]["summary_stats"]["total_agents"] == 3

    def test_empty_data(self):
        state = {"agents": [], "violations": [], "incidents": [], "relationships": [], "errors": []}
        result = analyze_node(state)
        assert result["current_stage"] == "analyze"


class TestExportNode:
    def test_generates_exports(self, tmp_dir, full_pipeline_data, monkeypatch):
        monkeypatch.setenv("PIPELINE_EXPORT_DIR", tmp_dir)
        state = {**full_pipeline_data, "errors": []}
        result = export_node(state)
        assert "cypher_scripts" in result
        assert "json_exports" in result
        assert result["current_stage"] == "export"

    def test_reports_validation_issues(self, tmp_dir, monkeypatch):
        monkeypatch.setenv("PIPELINE_EXPORT_DIR", tmp_dir)
        state = {
            "agents": [{"name": "No ID Agent"}],  # Missing id
            "violations": [],
            "incidents": [],
            "employees": [],
            "sources": [],
            "relationships": [],
            "errors": [],
        }
        result = export_node(state)
        assert any("Validation" in e["message"] for e in result["errors"])


class TestReportNode:
    def test_generates_report(
        self, tmp_dir, sample_agents_for_analysis, sample_violations_for_analysis, sample_relationships, monkeypatch
    ):
        monkeypatch.setenv("PIPELINE_OUTPUT_DIR", tmp_dir)
        findings = {
            "repeat_offenders": [],
            "co_perpetrators": [],
            "temporal_patterns": {},
            "geographic_patterns": {},
            "severity_distribution": {},
            "violation_type_distribution": {},
            "summary_stats": {"total_agents": 3},
            "generated_at": "2025-01-01",
        }
        state = {"analysis_report": findings, "errors": []}
        result = report_node(state)
        assert result["completed"] is True
        assert result["report_path"] != ""

    def test_handles_empty_findings(self, tmp_dir, monkeypatch):
        monkeypatch.setenv("PIPELINE_OUTPUT_DIR", tmp_dir)
        state = {"analysis_report": {}, "errors": []}
        result = report_node(state)
        assert result["completed"] is True


class TestErrorHandlerNode:
    def test_marks_completed(self):
        state = {"errors": [{"stage": "test", "message": "error"}]}
        result = error_handler_node(state)
        assert result["completed"] is True
        assert result["current_stage"] == "error"


class TestConditionalEdges:
    def test_intake_success(self):
        state = {"errors": []}
        assert should_continue_after_intake(state) == "process_documents"

    def test_intake_error(self):
        state = {"errors": [{"stage": "intake", "message": "No docs"}]}
        assert should_continue_after_intake(state) == "error_handler"

    def test_processing_needs_ollama(self):
        state = {"requires_human_input": True}
        assert should_continue_after_processing(state) == "wait_for_ollama"

    def test_processing_no_ollama(self):
        state = {"requires_human_input": False}
        assert should_continue_after_processing(state) == "normalize"

    def test_analysis_success(self):
        state = {"errors": []}
        assert should_continue_after_analysis(state) == "export"

    def test_analysis_too_many_errors(self):
        state = {"errors": [
            {"message": "analysis failed 1"},
            {"message": "analysis failed 2"},
            {"message": "analysis failed 3"},
            {"message": "analysis failed 4"},
        ]}
        assert should_continue_after_analysis(state) == "error_handler"


class TestBuildPipelineGraph:
    def test_graph_builds(self):
        graph = build_pipeline_graph()
        assert graph is not None

    def test_graph_compiles(self):
        graph = build_pipeline_graph()
        compiled = graph.compile()
        assert compiled is not None
