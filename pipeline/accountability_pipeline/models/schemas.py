"""Pydantic v2 models for the accountability pipeline.

Models mirror the Neo4j schema defined in init-scripts/01-create-schema.cypher
and extend it with pipeline-specific types for document processing and Ollama integration.
"""

import datetime as _dt
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# --- Enums ---

class VerificationStatus(str, Enum):
    """Verification status for agents and incidents."""
    CONFIRMED = "Confirmed"
    SUSPECTED = "Suspected"
    OUT_OF_FRAME = "Out of Frame"


class SeverityLevel(str, Enum):
    """Severity levels for violations."""
    CRITICAL = "critical"
    SEVERE = "severe"
    MODERATE = "moderate"
    MILD = "mild"


class ViolationType(str, Enum):
    """Types of violations tracked in the system."""
    EXECUTION = "execution"
    MURDER = "murder"
    ABUSE = "abuse"
    ASSAULT = "assault"
    HARASSMENT = "harassment"
    NEGLIGENCE = "negligence"
    MISCONDUCT = "misconduct"
    FRAUD = "fraud"
    CIVIL_RIGHTS = "civil_rights"
    OTHER = "other"


class EmployeeStatus(str, Enum):
    """Employment status."""
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    TERMINATED = "Terminated"


class SourceType(str, Enum):
    """Types of evidence sources."""
    FOIA = "FOIA"
    NEWS = "news"
    REPORT = "report"
    TESTIMONY = "testimony"
    COURT_RECORD = "court_record"
    INTERNAL_DOCUMENT = "internal_document"
    WHISTLEBLOWER = "whistleblower"
    OTHER = "other"


class RelationshipType(str, Enum):
    """Neo4j relationship types."""
    COMMITTED = "COMMITTED"
    INVOLVED_IN = "INVOLVED_IN"
    DOCUMENTED_BY = "DOCUMENTED_BY"
    RELATED_TO = "RELATED_TO"
    EMPLOYED_AS = "EMPLOYED_AS"


class ContentType(str, Enum):
    """Document content types the pipeline can process."""
    EMAIL = "email"
    TEXT = "text"
    CSV = "csv"
    PDF = "pdf"
    JSON = "json"
    HTML = "html"


class ProcessingStatus(str, Enum):
    """Pipeline document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_OLLAMA = "awaiting_ollama"
    PROCESSED = "processed"
    FAILED = "failed"


class ExtractionType(str, Enum):
    """Types of extraction Ollama can perform."""
    ENTITY_EXTRACTION = "entity_extraction"
    RELATIONSHIP_EXTRACTION = "relationship_extraction"
    SUMMARY = "summary"
    CLASSIFICATION = "classification"
    SENTIMENT = "sentiment"


# --- Helper ---

def _generate_id(prefix: str) -> str:
    """Generate a prefixed UUID."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


# --- Neo4j Node Models ---

class AgentModel(BaseModel):
    """ICE agent involved in violations. Maps to Neo4j :Agent node."""

    id: str = Field(default_factory=lambda: _generate_id("agent"))
    name: str = Field(..., min_length=1, max_length=500)
    badge_number: Optional[str] = None
    amount_paid: Optional[float] = Field(default=None, ge=0)
    address: Optional[str] = None
    status: VerificationStatus = VerificationStatus.SUSPECTED
    created_at: _dt.datetime = Field(default_factory=_utcnow)
    updated_at: _dt.datetime = Field(default_factory=_utcnow)
    notes: Optional[str] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class ViolationModel(BaseModel):
    """Documented violation. Maps to Neo4j :Violation node."""

    id: str = Field(default_factory=lambda: _generate_id("violation"))
    type: ViolationType
    description: str = Field(..., min_length=1)
    date: Optional[_dt.date] = None
    location: Optional[str] = None
    victim_count: Optional[int] = Field(default=None, ge=0)
    severity: SeverityLevel = SeverityLevel.MODERATE
    created_at: _dt.datetime = Field(default_factory=_utcnow)
    updated_at: _dt.datetime = Field(default_factory=_utcnow)


class IncidentModel(BaseModel):
    """Specific incident linking violations to agents. Maps to Neo4j :Incident node."""

    id: str = Field(default_factory=lambda: _generate_id("incident"))
    description: str = Field(..., min_length=1)
    date: Optional[_dt.date] = None
    location: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.SUSPECTED
    source_types: List[str] = Field(default_factory=list)
    created_at: _dt.datetime = Field(default_factory=_utcnow)
    updated_at: _dt.datetime = Field(default_factory=_utcnow)


class EmployeeModel(BaseModel):
    """ICE employee registry entry. Maps to Neo4j :Employee node."""

    id: str = Field(default_factory=lambda: _generate_id("employee"))
    name: str = Field(..., min_length=1, max_length=500)
    badge_number: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    hire_date: Optional[_dt.date] = None
    location: Optional[str] = None
    status: EmployeeStatus = EmployeeStatus.ACTIVE

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class SourceModel(BaseModel):
    """Evidence/documentation source. Maps to Neo4j :Source node."""

    id: str = Field(default_factory=lambda: _generate_id("source"))
    type: SourceType
    title: str = Field(..., min_length=1)
    url: Optional[str] = None
    content: Optional[str] = None
    date: Optional[_dt.date] = None
    credibility_score: float = Field(default=0.5, ge=0.0, le=1.0)


class RelationshipModel(BaseModel):
    """Relationship between two nodes. Maps to Neo4j relationships."""

    source_id: str
    target_id: str
    relationship_type: RelationshipType
    properties: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def ids_must_differ(self) -> "RelationshipModel":
        if self.source_id == self.target_id:
            raise ValueError("source_id and target_id must be different")
        return self


# --- Pipeline-Specific Models ---

class OllamaRequest(BaseModel):
    """Structured request for Ollama analysis via the workflow orchestrator.

    The pipeline cannot call Ollama directly. Instead, it formats these requests
    for the LLM workflow orchestrator to fulfill.
    """

    request_id: str = Field(default_factory=lambda: _generate_id("ollama-req"))
    file_id: str
    file_path: str
    extraction_type: ExtractionType
    prompt_template: str
    context: Optional[str] = None
    expected_schema: Optional[Dict[str, Any]] = None
    created_at: _dt.datetime = Field(default_factory=_utcnow)


class OllamaResponse(BaseModel):
    """Response from Ollama analysis, submitted by the orchestrator."""

    request_id: str
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_response: Optional[str] = None
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.extracted_data)


class PipelineDocument(BaseModel):
    """Document being processed through the pipeline."""

    file_id: str = Field(default_factory=lambda: _generate_id("doc"))
    file_path: str
    file_name: str = ""
    content_type: ContentType = ContentType.TEXT
    raw_content: Optional[str] = None
    extracted_entities: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    errors: List[str] = Field(default_factory=list)
    created_at: _dt.datetime = Field(default_factory=_utcnow)

    @model_validator(mode="after")
    def set_file_name(self) -> "PipelineDocument":
        if not self.file_name and self.file_path:
            self.file_name = self.file_path.rsplit("/", 1)[-1] if "/" in self.file_path else self.file_path
        return self


# --- Aggregate Models ---

class PipelineResult(BaseModel):
    """Complete result from a pipeline run."""

    run_id: str = Field(default_factory=lambda: _generate_id("run"))
    agents: List[AgentModel] = Field(default_factory=list)
    violations: List[ViolationModel] = Field(default_factory=list)
    incidents: List[IncidentModel] = Field(default_factory=list)
    employees: List[EmployeeModel] = Field(default_factory=list)
    sources: List[SourceModel] = Field(default_factory=list)
    relationships: List[RelationshipModel] = Field(default_factory=list)
    analysis_report: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)
    created_at: _dt.datetime = Field(default_factory=_utcnow)
    completed_at: Optional[_dt.datetime] = None


class FOIARequest(BaseModel):
    """Generated FOIA request letter."""

    request_id: str = Field(default_factory=lambda: _generate_id("foia"))
    agency: str
    subject: str
    date_range_start: Optional[_dt.date] = None
    date_range_end: Optional[_dt.date] = None
    description: str
    letter_content: str = ""
    status: str = "draft"
    created_at: _dt.datetime = Field(default_factory=_utcnow)
