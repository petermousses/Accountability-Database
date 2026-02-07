"""Tests for Pydantic models in schemas.py."""

import pytest
from pydantic import ValidationError

from accountability_pipeline.models.schemas import (
    AgentModel,
    ContentType,
    EmployeeModel,
    EmployeeStatus,
    ExtractionType,
    FOIARequest,
    IncidentModel,
    OllamaRequest,
    OllamaResponse,
    PipelineDocument,
    PipelineResult,
    ProcessingStatus,
    RelationshipModel,
    RelationshipType,
    SeverityLevel,
    SourceModel,
    SourceType,
    VerificationStatus,
    ViolationModel,
    ViolationType,
)


class TestAgentModel:
    def test_create_with_defaults(self):
        agent = AgentModel(name="John Smith")
        assert agent.name == "John Smith"
        assert agent.status == VerificationStatus.SUSPECTED
        assert agent.id.startswith("agent-")
        assert agent.badge_number is None
        assert agent.amount_paid is None

    def test_create_full(self, sample_agent_dict):
        agent = AgentModel(**sample_agent_dict)
        assert agent.name == "John Smith"
        assert agent.badge_number == "ICE-12345"
        assert agent.amount_paid == 85000.0
        assert agent.status == VerificationStatus.SUSPECTED

    def test_name_stripped(self):
        agent = AgentModel(name="  John Smith  ")
        assert agent.name == "John Smith"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            AgentModel(name="")

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            AgentModel(name="Test", amount_paid=-100)

    def test_valid_statuses(self):
        for status in VerificationStatus:
            agent = AgentModel(name="Test", status=status)
            assert agent.status == status


class TestViolationModel:
    def test_create_minimal(self):
        v = ViolationModel(type=ViolationType.ABUSE, description="Test violation")
        assert v.type == ViolationType.ABUSE
        assert v.severity == SeverityLevel.MODERATE
        assert v.id.startswith("violation-")

    def test_create_full(self, sample_violation_dict):
        v = ViolationModel(**sample_violation_dict)
        assert v.type == ViolationType.ABUSE
        assert v.severity == SeverityLevel.SEVERE
        assert v.victim_count == 1

    def test_empty_description_rejected(self):
        with pytest.raises(ValidationError):
            ViolationModel(type="abuse", description="")

    def test_negative_victim_count_rejected(self):
        with pytest.raises(ValidationError):
            ViolationModel(type="abuse", description="test", victim_count=-1)

    def test_all_types(self):
        for vtype in ViolationType:
            v = ViolationModel(type=vtype, description="test")
            assert v.type == vtype

    def test_all_severities(self):
        for sev in SeverityLevel:
            v = ViolationModel(type="abuse", description="test", severity=sev)
            assert v.severity == sev


class TestIncidentModel:
    def test_create_minimal(self):
        i = IncidentModel(description="Test incident")
        assert i.id.startswith("incident-")
        assert i.verification_status == VerificationStatus.SUSPECTED
        assert i.source_types == []

    def test_create_full(self, sample_incident_dict):
        i = IncidentModel(**sample_incident_dict)
        assert i.description == "Detention facility incident involving excessive force"
        assert len(i.source_types) == 2


class TestEmployeeModel:
    def test_create_minimal(self):
        e = EmployeeModel(name="Michael Brown")
        assert e.status == EmployeeStatus.ACTIVE
        assert e.id.startswith("employee-")

    def test_create_full(self, sample_employee_dict):
        e = EmployeeModel(**sample_employee_dict)
        assert e.title == "Deportation Officer"
        assert e.department == "Enforcement and Removal Operations"

    def test_name_stripped(self):
        e = EmployeeModel(name="  Mike  ")
        assert e.name == "Mike"


class TestSourceModel:
    def test_create_minimal(self):
        s = SourceModel(type=SourceType.FOIA, title="Test Source")
        assert s.credibility_score == 0.5
        assert s.id.startswith("source-")

    def test_create_full(self, sample_source_dict):
        s = SourceModel(**sample_source_dict)
        assert s.credibility_score == 0.95
        assert s.type == SourceType.FOIA

    def test_credibility_bounds(self):
        with pytest.raises(ValidationError):
            SourceModel(type="FOIA", title="test", credibility_score=1.5)
        with pytest.raises(ValidationError):
            SourceModel(type="FOIA", title="test", credibility_score=-0.1)


class TestRelationshipModel:
    def test_create(self, sample_relationship_dict):
        r = RelationshipModel(**sample_relationship_dict)
        assert r.relationship_type == RelationshipType.COMMITTED
        assert r.properties["role"] == "primary"

    def test_same_ids_rejected(self):
        with pytest.raises(ValidationError):
            RelationshipModel(
                source_id="same-id",
                target_id="same-id",
                relationship_type="COMMITTED",
            )

    def test_all_relationship_types(self):
        for rtype in RelationshipType:
            r = RelationshipModel(
                source_id="a", target_id="b", relationship_type=rtype
            )
            assert r.relationship_type == rtype


class TestOllamaRequest:
    def test_create(self):
        req = OllamaRequest(
            file_id="doc-001",
            file_path="/path/to/doc.txt",
            extraction_type=ExtractionType.ENTITY_EXTRACTION,
            prompt_template="Extract entities from: {content}",
        )
        assert req.request_id.startswith("ollama-req-")
        assert req.extraction_type == ExtractionType.ENTITY_EXTRACTION


class TestOllamaResponse:
    def test_success(self):
        resp = OllamaResponse(
            request_id="req-001",
            extracted_data={"entities": []},
            confidence=0.9,
        )
        assert resp.success is True

    def test_failure(self):
        resp = OllamaResponse(
            request_id="req-001",
            error="Model timeout",
        )
        assert resp.success is False

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            OllamaResponse(request_id="req-001", confidence=1.5)


class TestPipelineDocument:
    def test_create(self):
        doc = PipelineDocument(file_path="/path/to/report.txt")
        assert doc.file_name == "report.txt"
        assert doc.content_type == ContentType.TEXT
        assert doc.processing_status == ProcessingStatus.PENDING

    def test_file_name_from_path(self):
        doc = PipelineDocument(file_path="/long/path/to/doc.eml")
        assert doc.file_name == "doc.eml"

    def test_explicit_file_name(self):
        doc = PipelineDocument(file_path="/path/file.txt", file_name="custom.txt")
        assert doc.file_name == "custom.txt"


class TestPipelineResult:
    def test_create_empty(self):
        result = PipelineResult()
        assert result.run_id.startswith("run-")
        assert result.agents == []
        assert result.completed_at is None


class TestFOIARequest:
    def test_create(self):
        req = FOIARequest(
            agency="ICE",
            subject="Enforcement records",
            description="All records related to...",
        )
        assert req.request_id.startswith("foia-")
        assert req.status == "draft"


class TestEnums:
    def test_verification_status_values(self):
        assert VerificationStatus.CONFIRMED.value == "Confirmed"
        assert VerificationStatus.SUSPECTED.value == "Suspected"
        assert VerificationStatus.OUT_OF_FRAME.value == "Out of Frame"

    def test_violation_type_values(self):
        assert len(ViolationType) == 10

    def test_source_type_values(self):
        assert SourceType.FOIA.value == "FOIA"
        assert SourceType.WHISTLEBLOWER.value == "whistleblower"
