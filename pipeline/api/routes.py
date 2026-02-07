"""API routes for the accountability pipeline."""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from accountability_pipeline.config import get_config
from accountability_pipeline.core.foia_generator import (
    create_foia_tracker_csv,
    generate_foia_requests,
)
from accountability_pipeline.utils.file_handler import read_json, write_json
from accountability_pipeline.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# In-memory store for pipeline runs (production would use a database)
_pipeline_runs: Dict[str, Dict[str, Any]] = {}


# --- Request/Response Models ---

class UploadResponse(BaseModel):
    run_id: str
    document_count: int
    status: str
    message: str


class PipelineStatusResponse(BaseModel):
    run_id: str
    current_stage: str
    completed: bool
    requires_human_input: bool
    error_count: int
    ollama_requests: List[Dict[str, Any]] = Field(default_factory=list)


class OllamaResponseSubmission(BaseModel):
    run_id: str
    responses: List[Dict[str, Any]]


class FOIAGenerateRequest(BaseModel):
    agencies: List[str]
    subject: str = "ICE enforcement actions and personnel records"
    description: str = ""
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None


class FOIAGenerateResponse(BaseModel):
    files: Dict[str, str]
    tracker_path: str


class PipelineResultResponse(BaseModel):
    run_id: str
    agents: List[Dict[str, Any]] = Field(default_factory=list)
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    incidents: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    analysis_report: Optional[Dict[str, Any]] = None
    cypher_scripts: Dict[str, str] = Field(default_factory=dict)
    json_exports: Dict[str, str] = Field(default_factory=dict)
    report_path: str = ""
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class HistoryEntry(BaseModel):
    run_id: str
    created_at: str
    current_stage: str
    completed: bool
    document_count: int
    error_count: int


# --- Endpoints ---

@router.post("/upload", response_model=UploadResponse)
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload documents for pipeline processing.

    Accepts multiple files, saves them to the upload directory,
    and initiates a pipeline run.
    """
    config = get_config()
    config.ensure_directories()

    run_id = f"run-{uuid.uuid4().hex[:12]}"
    documents = []

    for upload_file in files:
        filename = upload_file.filename or f"unknown-{uuid.uuid4().hex[:8]}"
        file_path = os.path.join(config.upload_dir, run_id, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        content = await upload_file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        documents.append({
            "file_path": file_path,
            "file_name": filename,
            "file_id": f"doc-{uuid.uuid4().hex[:12]}",
            "size_bytes": len(content),
        })

    # Store run state
    _pipeline_runs[run_id] = {
        "run_id": run_id,
        "documents": documents,
        "current_stage": "uploaded",
        "completed": False,
        "requires_human_input": False,
        "errors": [],
        "ollama_requests": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "results": None,
    }

    logger.info("documents_uploaded", run_id=run_id, count=len(documents))

    return UploadResponse(
        run_id=run_id,
        document_count=len(documents),
        status="uploaded",
        message=f"Uploaded {len(documents)} document(s). Pipeline run initialized.",
    )


@router.get("/status/{run_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(run_id: str):
    """Get the current status of a pipeline run."""
    run = _pipeline_runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    return PipelineStatusResponse(
        run_id=run_id,
        current_stage=run.get("current_stage", "unknown"),
        completed=run.get("completed", False),
        requires_human_input=run.get("requires_human_input", False),
        error_count=len(run.get("errors", [])),
        ollama_requests=run.get("ollama_requests", []),
    )


@router.post("/ollama-response")
async def submit_ollama_response(submission: OllamaResponseSubmission):
    """Submit Ollama analysis results for a paused pipeline run.

    The workflow orchestrator calls this endpoint after fulfilling
    Ollama requests from the pipeline.
    """
    run = _pipeline_runs.get(submission.run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Pipeline run {submission.run_id} not found")

    if not run.get("requires_human_input"):
        raise HTTPException(status_code=400, detail="Pipeline is not waiting for Ollama responses")

    run["ollama_responses"] = submission.responses
    run["requires_human_input"] = False
    run["current_stage"] = "ollama_responses_received"

    logger.info("ollama_responses_submitted", run_id=submission.run_id, count=len(submission.responses))

    return {"status": "accepted", "run_id": submission.run_id, "response_count": len(submission.responses)}


@router.get("/results/{run_id}", response_model=PipelineResultResponse)
async def get_pipeline_results(run_id: str):
    """Get the results of a completed pipeline run."""
    run = _pipeline_runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    results = run.get("results") or {}

    return PipelineResultResponse(
        run_id=run_id,
        agents=results.get("agents", []),
        violations=results.get("violations", []),
        incidents=results.get("incidents", []),
        relationships=results.get("relationships", []),
        analysis_report=results.get("analysis_report"),
        cypher_scripts=results.get("cypher_scripts", {}),
        json_exports=results.get("json_exports", {}),
        report_path=results.get("report_path", ""),
        errors=run.get("errors", []),
    )


@router.post("/foia/generate", response_model=FOIAGenerateResponse)
async def generate_foia(request: FOIAGenerateRequest):
    """Generate FOIA request letters for specified agencies."""
    config = get_config()
    config.ensure_directories()

    files = generate_foia_requests(
        agencies=request.agencies,
        output_dir=config.foia_output_dir,
        subject=request.subject,
        description=request.description,
        date_range_start=request.date_range_start,
        date_range_end=request.date_range_end,
    )

    tracker_path = create_foia_tracker_csv(
        os.path.join(config.foia_output_dir, "foia_tracker.csv")
    )

    return FOIAGenerateResponse(files=files, tracker_path=tracker_path)


@router.get("/history", response_model=List[HistoryEntry])
async def get_pipeline_history():
    """Get the history of all pipeline runs."""
    entries = []
    for run_id, run in _pipeline_runs.items():
        entries.append(HistoryEntry(
            run_id=run_id,
            created_at=run.get("created_at", ""),
            current_stage=run.get("current_stage", "unknown"),
            completed=run.get("completed", False),
            document_count=len(run.get("documents", [])),
            error_count=len(run.get("errors", [])),
        ))

    return sorted(entries, key=lambda e: e.created_at, reverse=True)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
