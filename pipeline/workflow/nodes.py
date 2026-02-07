"""LangGraph node functions for the accountability pipeline.

Each function takes PipelineState and returns a partial state update.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from accountability_pipeline.config import get_config
from accountability_pipeline.core.correlation_analyzer import (
    find_agent_patterns,
    find_cross_incident_connections,
    generate_analysis_report,
)
from accountability_pipeline.core.data_normalizer import (
    deduplicate_agents,
    deduplicate_violations,
    normalize_names,
)
from accountability_pipeline.core.document_processor import (
    parse_text_document,
    request_ollama_analysis,
    store_raw_extraction,
)
from accountability_pipeline.core.neo4j_exporter import (
    generate_cypher_scripts,
    generate_json_export,
    validate_neo4j_readiness,
)
from accountability_pipeline.utils.logger import get_logger

logger = get_logger(__name__)


def _make_error(stage: str, message: str, details: Any = None) -> Dict[str, Any]:
    return {
        "stage": stage,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details,
    }


def intake_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize pipeline run and validate input documents.

    Reads: documents, config
    Writes: run_id, current_stage, errors
    """
    run_id = state.get("run_id") or f"run-{uuid.uuid4().hex[:12]}"
    documents = state.get("documents", [])
    errors = list(state.get("errors", []))

    logger.info("intake_start", run_id=run_id, document_count=len(documents))

    if not documents:
        errors.append(_make_error("intake", "No documents provided"))

    for doc in documents:
        if not doc.get("file_path"):
            errors.append(_make_error("intake", "Document missing file_path", doc))

    return {
        "run_id": run_id,
        "current_stage": "intake",
        "errors": errors,
        "completed": False,
        "requires_human_input": False,
    }


def process_documents_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Process uploaded documents and extract structured data.

    Reads: documents
    Writes: raw_extractions, ollama_requests, current_stage, errors
    """
    documents = state.get("documents", [])
    errors = list(state.get("errors", []))
    raw_extractions: List[Dict] = []
    ollama_requests: List[Dict] = []

    config = get_config()

    for doc in documents:
        file_path = doc.get("file_path", "")
        try:
            extracted = parse_text_document(file_path, doc.get("content_type"))
            raw_extractions.append(extracted)

            # Store extraction with audit trail
            file_id = doc.get("file_id", file_path.rsplit("/", 1)[-1])
            config.ensure_directories()
            store_raw_extraction(file_id, extracted, config.output_dir)

            # Create Ollama request for deeper analysis
            ollama_req = request_ollama_analysis(file_path, "entity_extraction")
            ollama_requests.append(ollama_req.model_dump())

        except Exception as e:
            errors.append(_make_error("process_documents", f"Failed to process {file_path}: {e}"))
            logger.error("document_processing_failed", file_path=file_path, error=str(e))

    return {
        "raw_extractions": raw_extractions,
        "ollama_requests": ollama_requests,
        "current_stage": "process_documents",
        "errors": errors,
        "requires_human_input": len(ollama_requests) > 0,
    }


def normalize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize and deduplicate extracted entities.

    Reads: raw_extractions, ollama_responses
    Writes: agents, violations, incidents, employees, sources, relationships, current_stage
    """
    raw_extractions = state.get("raw_extractions", [])
    ollama_responses = state.get("ollama_responses", [])
    errors = list(state.get("errors", []))
    config = get_config()

    # Collect all extracted entities
    all_agents: List[Dict] = []
    all_violations: List[Dict] = []
    all_incidents: List[Dict] = []
    all_employees: List[Dict] = []
    all_sources: List[Dict] = []
    all_relationships: List[Dict] = []

    # Extract from raw parsing results
    for extraction in raw_extractions:
        fields = extraction.get("extracted_fields", {})
        names = fields.get("potential_names", [])
        for name in names:
            all_agents.append({"name": name, "status": "Suspected"})

    # Extract from Ollama responses
    for response in ollama_responses:
        data = response.get("extracted_data", {})
        entities = data.get("entities", [])
        for entity in entities:
            etype = entity.get("type", "").lower()
            if etype == "person":
                all_agents.append({
                    "name": entity.get("name", ""),
                    "status": "Suspected",
                    "badge_number": _extract_identifier(entity),
                })
            elif etype == "organization":
                all_employees.append({"name": entity.get("name", ""), "department": ""})

        rels = data.get("relationships", [])
        for rel in rels:
            all_relationships.append({
                "source_id": rel.get("source", ""),
                "target_id": rel.get("target", ""),
                "relationship_type": rel.get("type", "RELATED_TO"),
            })

    # Deduplicate
    try:
        deduped_agents = deduplicate_agents(all_agents, config.fuzzy_match_threshold)
    except Exception as e:
        deduped_agents = all_agents
        errors.append(_make_error("normalize", f"Agent dedup failed: {e}"))

    try:
        deduped_violations = deduplicate_violations(all_violations)
    except Exception as e:
        deduped_violations = all_violations
        errors.append(_make_error("normalize", f"Violation dedup failed: {e}"))

    return {
        "agents": deduped_agents,
        "violations": deduped_violations,
        "incidents": all_incidents,
        "employees": all_employees,
        "sources": all_sources,
        "relationships": all_relationships,
        "current_stage": "normalize",
        "errors": errors,
    }


def _extract_identifier(entity: Dict) -> str:
    """Extract badge/ID number from entity identifiers."""
    identifiers = entity.get("identifiers", [])
    if identifiers:
        return str(identifiers[0])
    return ""


def analyze_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run correlation analysis on normalized data.

    Reads: agents, violations, incidents, relationships
    Writes: analysis_report, cross_incident_connections, current_stage
    """
    agents = state.get("agents", [])
    violations = state.get("violations", [])
    incidents = state.get("incidents", [])
    relationships = state.get("relationships", [])
    errors = list(state.get("errors", []))

    try:
        findings = find_agent_patterns(agents, violations, relationships)
    except Exception as e:
        findings = {}
        errors.append(_make_error("analyze", f"Pattern analysis failed: {e}"))

    try:
        connections = find_cross_incident_connections(incidents)
    except Exception as e:
        connections = []
        errors.append(_make_error("analyze", f"Cross-incident analysis failed: {e}"))

    return {
        "analysis_report": findings,
        "cross_incident_connections": connections,
        "current_stage": "analyze",
        "errors": errors,
    }


def export_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Neo4j export files (Cypher + JSON).

    Reads: agents, violations, incidents, employees, sources, relationships
    Writes: cypher_scripts, json_exports, current_stage
    """
    agents = state.get("agents", [])
    violations = state.get("violations", [])
    incidents = state.get("incidents", [])
    employees = state.get("employees", [])
    sources = state.get("sources", [])
    relationships = state.get("relationships", [])
    errors = list(state.get("errors", []))

    config = get_config()
    export_dir = config.export_dir
    config.ensure_directories()

    cypher_scripts = {}
    json_exports = {}

    # Validate before export
    data = {
        "agents": agents,
        "violations": violations,
        "incidents": incidents,
        "employees": employees,
        "sources": sources,
        "relationships": relationships,
    }

    is_ready, issues = validate_neo4j_readiness(data)
    if not is_ready:
        for issue in issues:
            errors.append(_make_error("export", f"Validation: {issue}"))

    # Generate exports regardless (with warnings)
    try:
        cypher_scripts = generate_cypher_scripts(
            agents, violations, incidents, export_dir,
            employees=employees, sources=sources, relationships=relationships,
        )
    except Exception as e:
        errors.append(_make_error("export", f"Cypher generation failed: {e}"))

    try:
        json_exports = generate_json_export(data, export_dir)
    except Exception as e:
        errors.append(_make_error("export", f"JSON export failed: {e}"))

    return {
        "cypher_scripts": cypher_scripts,
        "json_exports": json_exports,
        "current_stage": "export",
        "errors": errors,
    }


def report_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the final analysis report.

    Reads: analysis_report
    Writes: report_path, current_stage, completed
    """
    findings = state.get("analysis_report", {})
    errors = list(state.get("errors", []))

    config = get_config()
    config.ensure_directories()
    report_path = ""

    if findings:
        try:
            report_file = f"{config.output_dir}/analysis_report.md"
            report_path = generate_analysis_report(findings, report_file)
        except Exception as e:
            errors.append(_make_error("report", f"Report generation failed: {e}"))

    return {
        "report_path": report_path,
        "current_stage": "complete",
        "completed": True,
        "errors": errors,
    }


def error_handler_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle errors by logging and marking pipeline as failed.

    Reads: errors
    Writes: current_stage, completed
    """
    errors = state.get("errors", [])
    logger.error("pipeline_error", error_count=len(errors), errors=errors)

    return {
        "current_stage": "error",
        "completed": True,
    }
