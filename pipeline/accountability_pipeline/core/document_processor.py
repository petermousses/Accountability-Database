"""Document processing for FOIA data extraction.

Parses text, email, and CSV documents to extract structured data.
Formats Ollama analysis requests for the workflow orchestrator.
"""

from __future__ import annotations

import email
import os
import re
from datetime import datetime
from email import policy
from typing import Any, Dict, List, Optional

from accountability_pipeline.models.schemas import (
    ContentType,
    ExtractionType,
    OllamaRequest,
    PipelineDocument,
    ProcessingStatus,
)
from accountability_pipeline.utils.file_handler import (
    read_csv,
    read_json,
    read_text,
    store_with_audit,
)
from accountability_pipeline.utils.logger import get_logger

logger = get_logger(__name__)


def detect_content_type(file_path: str) -> ContentType:
    """Detect the content type of a file based on extension.

    Args:
        file_path: Path to the file.

    Returns:
        Detected ContentType enum value.
    """
    ext = os.path.splitext(file_path)[1].lower()
    type_map = {
        ".txt": ContentType.TEXT,
        ".eml": ContentType.EMAIL,
        ".msg": ContentType.EMAIL,
        ".csv": ContentType.CSV,
        ".json": ContentType.JSON,
        ".html": ContentType.HTML,
        ".htm": ContentType.HTML,
        ".pdf": ContentType.PDF,
    }
    return type_map.get(ext, ContentType.TEXT)


def parse_text_document(file_path: str, content_type: Optional[str] = None) -> Dict[str, Any]:
    """Extract structured data from a text document.

    Handles plain text, email, and CSV formats with basic entity extraction.

    Args:
        file_path: Path to the document file.
        content_type: Override content type. If None, auto-detected.

    Returns:
        Dictionary with extracted data:
        - file_path: Original file path
        - content_type: Detected/specified content type
        - raw_content: Full text content
        - metadata: File metadata (size, dates)
        - extracted_fields: Basic extracted fields
    """
    if content_type:
        ctype = ContentType(content_type)
    else:
        ctype = detect_content_type(file_path)

    logger.info("parsing_document", file_path=file_path, content_type=ctype.value)

    if ctype == ContentType.EMAIL:
        return _parse_email(file_path)
    elif ctype == ContentType.CSV:
        return _parse_csv(file_path)
    elif ctype == ContentType.JSON:
        return _parse_json(file_path)
    else:
        return _parse_text(file_path)


def _parse_text(file_path: str) -> Dict[str, Any]:
    """Parse a plain text document."""
    content = read_text(file_path)
    stat = os.stat(file_path)

    return {
        "file_path": file_path,
        "content_type": ContentType.TEXT.value,
        "raw_content": content,
        "metadata": {
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        },
        "extracted_fields": _extract_basic_fields(content),
    }


def _parse_email(file_path: str) -> Dict[str, Any]:
    """Parse an email file (.eml format)."""
    raw = read_text(file_path)
    msg = email.message_from_string(raw, policy=policy.default)

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                body = part.get_content()
                break
    else:
        body = msg.get_content()

    headers = {
        "from": str(msg.get("From", "")),
        "to": str(msg.get("To", "")),
        "cc": str(msg.get("Cc", "")),
        "subject": str(msg.get("Subject", "")),
        "date": str(msg.get("Date", "")),
        "message_id": str(msg.get("Message-ID", "")),
    }

    return {
        "file_path": file_path,
        "content_type": ContentType.EMAIL.value,
        "raw_content": raw,
        "metadata": headers,
        "extracted_fields": {
            **_extract_basic_fields(body),
            "email_from": headers["from"],
            "email_to": headers["to"],
            "email_subject": headers["subject"],
            "email_date": headers["date"],
        },
    }


def _parse_csv(file_path: str) -> Dict[str, Any]:
    """Parse a CSV file."""
    rows = read_csv(file_path)
    raw_content = read_text(file_path)

    return {
        "file_path": file_path,
        "content_type": ContentType.CSV.value,
        "raw_content": raw_content,
        "metadata": {
            "row_count": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
        },
        "extracted_fields": {
            "records": rows,
            "record_count": len(rows),
        },
    }


def _parse_json(file_path: str) -> Dict[str, Any]:
    """Parse a JSON file."""
    data = read_json(file_path)
    raw_content = read_text(file_path)

    return {
        "file_path": file_path,
        "content_type": ContentType.JSON.value,
        "raw_content": raw_content,
        "metadata": {
            "type": type(data).__name__,
        },
        "extracted_fields": {
            "data": data,
        },
    }


def _extract_basic_fields(text: str) -> Dict[str, Any]:
    """Extract basic fields from text using regex patterns.

    Extracts dates, names (capitalized sequences), locations, and badge numbers.

    Args:
        text: Raw text to extract from.

    Returns:
        Dictionary of extracted field lists.
    """
    date_patterns = re.findall(
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}\b',
        text,
        re.IGNORECASE,
    )

    # Badge/ID numbers
    badge_patterns = re.findall(
        r'\b(?:badge|id|employee)\s*(?:#|number|no\.?)?\s*:?\s*([A-Z0-9-]{3,15})\b',
        text,
        re.IGNORECASE,
    )

    # Names (sequences of capitalized words, 2-4 words)
    name_patterns = re.findall(
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b',
        text,
    )

    # Locations (common patterns like "City, State")
    location_patterns = re.findall(
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2})\b',
        text,
    )

    return {
        "dates": list(set(date_patterns)),
        "badge_numbers": list(set(badge_patterns)),
        "potential_names": list(set(name_patterns)),
        "locations": list(set(location_patterns)),
    }


def request_ollama_analysis(
    file_path: str,
    extraction_type: str,
    context: Optional[str] = None,
) -> OllamaRequest:
    """Create a structured Ollama analysis request.

    Since the pipeline cannot call Ollama directly, this formats a request
    object for the workflow orchestrator to fulfill.

    Args:
        file_path: Path to the file to analyze.
        extraction_type: Type of extraction to perform.
        context: Additional context for the analysis.

    Returns:
        OllamaRequest object for the orchestrator.
    """
    etype = ExtractionType(extraction_type)

    prompt_templates = {
        ExtractionType.ENTITY_EXTRACTION: (
            "Extract all named entities from the following document. "
            "For each entity, identify: name, type (person/organization/location), "
            "and any associated identifiers (badge numbers, employee IDs). "
            "Return as JSON with keys: entities (list of {name, type, identifiers}).\n\n"
            "Document:\n{content}"
        ),
        ExtractionType.RELATIONSHIP_EXTRACTION: (
            "Identify relationships between entities in this document. "
            "For each relationship, identify: source entity, target entity, "
            "relationship type, and confidence level. "
            "Return as JSON with keys: relationships (list of {source, target, type, confidence}).\n\n"
            "Document:\n{content}"
        ),
        ExtractionType.SUMMARY: (
            "Summarize this document, focusing on: key people mentioned, "
            "events described, dates, locations, and any violations or incidents. "
            "Return as JSON with keys: summary, key_people, events, dates, locations.\n\n"
            "Document:\n{content}"
        ),
        ExtractionType.CLASSIFICATION: (
            "Classify this document into one or more categories: "
            "enforcement_action, personnel_complaint, use_of_force, "
            "internal_investigation, policy_document, correspondence, other. "
            "Return as JSON with keys: categories (list), confidence, reasoning.\n\n"
            "Document:\n{content}"
        ),
        ExtractionType.SENTIMENT: (
            "Analyze the tone and implications of this document regarding "
            "accountability and potential violations. "
            "Return as JSON with keys: tone, severity_indicators, key_concerns.\n\n"
            "Document:\n{content}"
        ),
    }

    expected_schemas = {
        ExtractionType.ENTITY_EXTRACTION: {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "identifiers": {"type": "array"},
                        },
                    },
                },
            },
        },
        ExtractionType.RELATIONSHIP_EXTRACTION: {
            "type": "object",
            "properties": {
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "target": {"type": "string"},
                            "type": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                    },
                },
            },
        },
    }

    request = OllamaRequest(
        file_id=os.path.basename(file_path),
        file_path=file_path,
        extraction_type=etype,
        prompt_template=prompt_templates.get(etype, prompt_templates[ExtractionType.ENTITY_EXTRACTION]),
        context=context,
        expected_schema=expected_schemas.get(etype),
    )

    logger.info("ollama_request_created", request_id=request.request_id, extraction_type=etype.value)
    return request


def store_raw_extraction(
    file_id: str,
    extracted_data: Dict[str, Any],
    output_dir: str,
) -> str:
    """Save extraction results with an audit trail.

    Args:
        file_id: Unique identifier for the source file.
        extracted_data: The extracted data dictionary.
        output_dir: Directory to store the extraction.

    Returns:
        Path to the stored extraction file.
    """
    file_path = os.path.join(output_dir, f"{file_id}_extraction.json")

    metadata = {
        "file_id": file_id,
        "extraction_type": "raw",
        "field_count": len(extracted_data),
        "source": "document_processor",
    }

    result_path = store_with_audit(extracted_data, file_path, metadata=metadata)
    logger.info("extraction_stored", file_id=file_id, path=result_path)
    return result_path


def create_pipeline_document(file_path: str) -> PipelineDocument:
    """Create a PipelineDocument from a file path.

    Args:
        file_path: Path to the source document.

    Returns:
        PipelineDocument ready for processing.
    """
    ctype = detect_content_type(file_path)
    return PipelineDocument(
        file_path=file_path,
        content_type=ctype,
        processing_status=ProcessingStatus.PENDING,
    )
