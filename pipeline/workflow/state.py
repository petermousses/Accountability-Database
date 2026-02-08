"""Pipeline state definition for LangGraph workflow.

Defines the TypedDict that flows through all workflow nodes,
carrying documents, extracted data, and pipeline control state.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class PipelineState(TypedDict, total=False):
    """Complete state for the accountability pipeline workflow.

    All nodes read from and write to this state. Fields use total=False
    so nodes can selectively update only their output fields.
    """

    # --- Input ---
    documents: List[Dict[str, Any]]
    """Uploaded document metadata: [{file_path, content_type, ...}]"""

    config: Dict[str, Any]
    """Pipeline configuration overrides."""

    # --- Document Processing ---
    raw_extractions: List[Dict[str, Any]]
    """Output from document processing: [{file_path, content_type, raw_content, extracted_fields}]"""

    ollama_requests: List[Dict[str, Any]]
    """Pending Ollama analysis requests: [{request_id, file_id, extraction_type, prompt_template}]"""

    ollama_responses: List[Dict[str, Any]]
    """Completed Ollama responses: [{request_id, extracted_data, confidence}]"""

    # --- Normalized Entities ---
    agents: List[Dict[str, Any]]
    """Normalized and deduplicated agent records."""

    violations: List[Dict[str, Any]]
    """Normalized violation records."""

    incidents: List[Dict[str, Any]]
    """Normalized incident records."""

    employees: List[Dict[str, Any]]
    """Normalized employee records."""

    sources: List[Dict[str, Any]]
    """Normalized source/evidence records."""

    relationships: List[Dict[str, Any]]
    """Extracted relationships between entities."""

    # --- Analysis ---
    analysis_report: Dict[str, Any]
    """Correlation analysis findings."""

    cross_incident_connections: List[Dict[str, Any]]
    """Cross-incident similarity connections."""

    # --- Export ---
    cypher_scripts: Dict[str, str]
    """Generated Cypher file paths: {script_name: file_path}."""

    json_exports: Dict[str, str]
    """Generated JSON export paths: {entity_type: file_path}."""

    report_path: str
    """Path to generated markdown analysis report."""

    # --- Control ---
    run_id: str
    """Unique identifier for this pipeline run."""

    current_stage: str
    """Current pipeline stage name."""

    errors: List[Dict[str, Any]]
    """Error log: [{stage, message, timestamp, details}]."""

    requires_human_input: bool
    """Whether the pipeline is paused waiting for Ollama responses."""

    completed: bool
    """Whether the pipeline has finished processing."""
