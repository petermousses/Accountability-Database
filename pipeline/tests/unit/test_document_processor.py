"""Tests for document processing."""

import json
import os

import pytest

from accountability_pipeline.core.document_processor import (
    _extract_basic_fields,
    create_pipeline_document,
    detect_content_type,
    parse_text_document,
    request_ollama_analysis,
    store_raw_extraction,
)
from accountability_pipeline.models.schemas import ContentType, ExtractionType, ProcessingStatus


class TestDetectContentType:
    def test_text_file(self):
        assert detect_content_type("report.txt") == ContentType.TEXT

    def test_email_file(self):
        assert detect_content_type("message.eml") == ContentType.EMAIL

    def test_csv_file(self):
        assert detect_content_type("data.csv") == ContentType.CSV

    def test_json_file(self):
        assert detect_content_type("config.json") == ContentType.JSON

    def test_html_file(self):
        assert detect_content_type("page.html") == ContentType.HTML
        assert detect_content_type("page.htm") == ContentType.HTML

    def test_pdf_file(self):
        assert detect_content_type("document.pdf") == ContentType.PDF

    def test_unknown_defaults_to_text(self):
        assert detect_content_type("file.xyz") == ContentType.TEXT

    def test_with_path(self):
        assert detect_content_type("/path/to/data.csv") == ContentType.CSV


class TestParseTextDocument:
    def test_parse_text(self, sample_text_document):
        result = parse_text_document(sample_text_document)
        assert result["content_type"] == "text"
        assert result["raw_content"] is not None
        assert "extracted_fields" in result
        assert "metadata" in result

    def test_parse_email(self, sample_email_file):
        result = parse_text_document(sample_email_file)
        assert result["content_type"] == "email"
        assert "email_from" in result["extracted_fields"]
        assert "email_subject" in result["extracted_fields"]
        assert "Incident Report" in result["extracted_fields"]["email_subject"]

    def test_parse_csv(self, sample_csv_file):
        result = parse_text_document(sample_csv_file)
        assert result["content_type"] == "csv"
        assert result["extracted_fields"]["record_count"] == 3

    def test_parse_json(self, sample_json_file):
        result = parse_text_document(sample_json_file)
        assert result["content_type"] == "json"
        assert "data" in result["extracted_fields"]

    def test_override_content_type(self, sample_text_document):
        result = parse_text_document(sample_text_document, content_type="text")
        assert result["content_type"] == "text"


class TestExtractBasicFields:
    def test_extracts_dates(self):
        text = "The incident occurred on March 15, 2025 and was reported on 03/20/2025."
        fields = _extract_basic_fields(text)
        assert len(fields["dates"]) >= 1

    def test_extracts_badge_numbers(self):
        text = "Agent Smith (Badge #ICE-12345) was involved."
        fields = _extract_basic_fields(text)
        assert len(fields["badge_numbers"]) >= 1

    def test_extracts_names(self):
        text = "Agent John Smith and Officer Jane Doe were present."
        fields = _extract_basic_fields(text)
        assert len(fields["potential_names"]) >= 1

    def test_extracts_locations(self):
        text = "The incident occurred in El Paso, TX near the border."
        fields = _extract_basic_fields(text)
        assert len(fields["locations"]) >= 1

    def test_empty_text(self):
        fields = _extract_basic_fields("")
        assert fields["dates"] == []
        assert fields["badge_numbers"] == []


class TestRequestOllamaAnalysis:
    def test_entity_extraction(self, sample_text_document):
        req = request_ollama_analysis(sample_text_document, "entity_extraction")
        assert req.extraction_type == ExtractionType.ENTITY_EXTRACTION
        assert req.request_id.startswith("ollama-req-")
        assert "entities" in req.prompt_template.lower() or "entity" in req.prompt_template.lower()
        assert req.expected_schema is not None

    def test_relationship_extraction(self, sample_text_document):
        req = request_ollama_analysis(sample_text_document, "relationship_extraction")
        assert req.extraction_type == ExtractionType.RELATIONSHIP_EXTRACTION

    def test_summary(self, sample_text_document):
        req = request_ollama_analysis(sample_text_document, "summary")
        assert req.extraction_type == ExtractionType.SUMMARY

    def test_classification(self, sample_text_document):
        req = request_ollama_analysis(sample_text_document, "classification")
        assert req.extraction_type == ExtractionType.CLASSIFICATION

    def test_with_context(self, sample_text_document):
        req = request_ollama_analysis(
            sample_text_document, "entity_extraction",
            context="Focus on ICE agent identifiers",
        )
        assert req.context == "Focus on ICE agent identifiers"


class TestStoreRawExtraction:
    def test_stores_with_audit(self, tmp_dir):
        data = {"entities": [{"name": "John Smith"}]}
        path = store_raw_extraction("doc-001", data, tmp_dir)

        assert os.path.exists(path)
        assert os.path.exists(path + ".meta.json")

        stored = json.loads(open(path).read())
        assert stored["entities"][0]["name"] == "John Smith"


class TestCreatePipelineDocument:
    def test_create_from_text(self, sample_text_document):
        doc = create_pipeline_document(sample_text_document)
        assert doc.content_type == ContentType.TEXT
        assert doc.processing_status == ProcessingStatus.PENDING
        assert doc.file_name == "incident_report.txt"

    def test_create_from_csv(self, sample_csv_file):
        doc = create_pipeline_document(sample_csv_file)
        assert doc.content_type == ContentType.CSV
