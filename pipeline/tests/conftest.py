"""Shared test fixtures for the accountability pipeline test suite."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime

import pytest


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_agent_dict():
    """A valid agent dictionary."""
    return {
        "id": "agent-test-001",
        "name": "John Smith",
        "badge_number": "ICE-12345",
        "amount_paid": 85000.0,
        "address": "123 Main St, Washington, DC",
        "status": "Suspected",
        "notes": "Test agent record",
    }


@pytest.fixture
def sample_agent_list():
    """List of agent dicts with some duplicates for dedup testing."""
    return [
        {"name": "John Smith", "badge_number": "ICE-001", "status": "Suspected"},
        {"name": "Jon Smith", "badge_number": "ICE-001", "status": "Confirmed"},
        {"name": "Jane Doe", "badge_number": "ICE-002", "status": "Suspected"},
        {"name": "Robert Johnson", "badge_number": "ICE-003", "status": "Suspected"},
        {"name": "Bob Johnson", "badge_number": "ICE-003", "status": "Suspected"},
        {"name": "Alice Williams", "badge_number": "ICE-004", "status": "Confirmed"},
    ]


@pytest.fixture
def sample_violation_dict():
    """A valid violation dictionary."""
    return {
        "id": "violation-test-001",
        "type": "abuse",
        "description": "Use of excessive force during detention",
        "date": date(2025, 3, 15),
        "location": "El Paso, TX",
        "victim_count": 1,
        "severity": "severe",
    }


@pytest.fixture
def sample_violation_list():
    """List of violation dicts with duplicates."""
    return [
        {
            "type": "abuse",
            "description": "Use of excessive force during detention",
            "date": date(2025, 3, 15),
            "location": "El Paso, TX",
            "severity": "severe",
        },
        {
            "type": "abuse",
            "description": "Use of excessive force during detention processing",
            "date": date(2025, 3, 15),
            "location": "El Paso, TX",
            "severity": "severe",
        },
        {
            "type": "negligence",
            "description": "Failure to provide medical care",
            "date": date(2025, 4, 1),
            "location": "Tucson, AZ",
            "severity": "critical",
        },
    ]


@pytest.fixture
def sample_incident_dict():
    """A valid incident dictionary."""
    return {
        "id": "incident-test-001",
        "description": "Detention facility incident involving excessive force",
        "date": date(2025, 3, 15),
        "location": "El Paso, TX",
        "verification_status": "Suspected",
        "source_types": ["FOIA", "news"],
    }


@pytest.fixture
def sample_employee_dict():
    """A valid employee dictionary."""
    return {
        "id": "employee-test-001",
        "name": "Michael Brown",
        "badge_number": "ICE-99999",
        "department": "Enforcement and Removal Operations",
        "title": "Deportation Officer",
        "hire_date": date(2020, 1, 15),
        "location": "Dallas, TX",
        "status": "Active",
    }


@pytest.fixture
def sample_source_dict():
    """A valid source dictionary."""
    return {
        "id": "source-test-001",
        "type": "FOIA",
        "title": "FOIA Response - ICE ERO Records 2025",
        "url": "https://example.com/foia/12345",
        "content": "Released document content...",
        "date": date(2025, 6, 1),
        "credibility_score": 0.95,
    }


@pytest.fixture
def sample_relationship_dict():
    """A valid relationship dictionary."""
    return {
        "source_id": "agent-test-001",
        "target_id": "violation-test-001",
        "relationship_type": "COMMITTED",
        "properties": {"confirmation_status": "Suspected", "role": "primary"},
    }


@pytest.fixture
def sample_email_content():
    """Sample email content for parsing tests."""
    return """\
From: officer.smith@ice.gov
To: supervisor.jones@ice.gov
Subject: Incident Report - March 15 2025
Date: Mon, 15 Mar 2025 14:30:00 -0500
Message-ID: <test-msg-001@ice.gov>
Content-Type: text/plain; charset="utf-8"

Supervisor Jones,

I am writing to report an incident that occurred on March 15, 2025 at the
El Paso Processing Center involving Agent John Smith (Badge #ICE-12345).

During routine processing, excessive force was used against a detainee.
Officer Robert Johnson (Badge #ICE-003) was also present during the incident.

The detainee was transferred to University Medical Center, El Paso, TX
for treatment of injuries.

Please advise on next steps.

Agent Mike Davis
Badge #ICE-789
"""


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for parsing tests."""
    return """\
name,badge_number,department,title,location,status
John Smith,ICE-12345,ERO,Deportation Officer,El Paso TX,Active
Jane Doe,ICE-67890,HSI,Special Agent,Dallas TX,Active
Robert Johnson,ICE-11111,ERO,Supervisory Officer,Tucson AZ,Active
"""


@pytest.fixture
def sample_text_document(tmp_dir):
    """Create a sample text document file."""
    content = """\
INCIDENT REPORT

Date: March 15, 2025
Location: El Paso Processing Center, El Paso, TX

Agent John Smith (Badge #ICE-12345) used excessive force during
the processing of a detainee at approximately 14:00 hours.

Witnesses: Officer Robert Johnson (Badge #ICE-003), Officer Jane Doe (Badge #ICE-002)

The detainee sustained injuries requiring medical attention.
Transferred to University Medical Center for treatment.

Classification: Use of Force - Level 3
Severity: Severe
"""
    file_path = os.path.join(tmp_dir, "incident_report.txt")
    with open(file_path, "w") as f:
        f.write(content)
    return file_path


@pytest.fixture
def sample_email_file(tmp_dir, sample_email_content):
    """Create a sample .eml file."""
    file_path = os.path.join(tmp_dir, "incident_email.eml")
    with open(file_path, "w") as f:
        f.write(sample_email_content)
    return file_path


@pytest.fixture
def sample_csv_file(tmp_dir, sample_csv_content):
    """Create a sample CSV file."""
    file_path = os.path.join(tmp_dir, "employees.csv")
    with open(file_path, "w") as f:
        f.write(sample_csv_content)
    return file_path


@pytest.fixture
def sample_json_file(tmp_dir):
    """Create a sample JSON file."""
    data = {
        "agents": [
            {"name": "John Smith", "badge_number": "ICE-12345"},
            {"name": "Jane Doe", "badge_number": "ICE-67890"},
        ]
    }
    file_path = os.path.join(tmp_dir, "data.json")
    with open(file_path, "w") as f:
        json.dump(data, f)
    return file_path


@pytest.fixture
def sample_relationships():
    """List of relationship dicts for analysis tests."""
    return [
        {"source_id": "agent-001", "target_id": "violation-001", "relationship_type": "COMMITTED"},
        {"source_id": "agent-001", "target_id": "violation-002", "relationship_type": "COMMITTED"},
        {"source_id": "agent-002", "target_id": "violation-001", "relationship_type": "COMMITTED"},
        {"source_id": "agent-003", "target_id": "violation-003", "relationship_type": "COMMITTED"},
        {"source_id": "agent-001", "target_id": "incident-001", "relationship_type": "INVOLVED_IN"},
        {"source_id": "agent-002", "target_id": "incident-001", "relationship_type": "INVOLVED_IN"},
    ]


@pytest.fixture
def sample_agents_for_analysis():
    """Agent records for correlation analysis."""
    return [
        {"id": "agent-001", "name": "John Smith", "status": "Confirmed"},
        {"id": "agent-002", "name": "Jane Doe", "status": "Suspected"},
        {"id": "agent-003", "name": "Robert Johnson", "status": "Suspected"},
    ]


@pytest.fixture
def sample_violations_for_analysis():
    """Violation records for correlation analysis."""
    return [
        {"id": "violation-001", "type": "abuse", "date": date(2025, 3, 15), "location": "El Paso, TX", "severity": "severe"},
        {"id": "violation-002", "type": "abuse", "date": date(2025, 3, 20), "location": "El Paso, TX", "severity": "moderate"},
        {"id": "violation-003", "type": "negligence", "date": date(2025, 4, 1), "location": "Tucson, AZ", "severity": "critical"},
    ]


@pytest.fixture
def sample_ollama_response():
    """Sample Ollama response for testing."""
    return {
        "request_id": "ollama-req-test001",
        "extracted_data": {
            "entities": [
                {"name": "John Smith", "type": "person", "identifiers": ["ICE-12345"]},
                {"name": "Robert Johnson", "type": "person", "identifiers": ["ICE-003"]},
                {"name": "El Paso Processing Center", "type": "organization", "identifiers": []},
            ],
            "relationships": [
                {"source": "John Smith", "target": "excessive force incident", "type": "COMMITTED", "confidence": 0.9},
            ],
        },
        "confidence": 0.85,
        "raw_response": "Extracted entities from document...",
    }


@pytest.fixture
def full_pipeline_data(
    sample_agents_for_analysis,
    sample_violations_for_analysis,
    sample_relationships,
):
    """Complete data set for Neo4j export testing."""
    return {
        "agents": sample_agents_for_analysis,
        "violations": sample_violations_for_analysis,
        "incidents": [
            {"id": "incident-001", "description": "El Paso detention facility incident", "date": date(2025, 3, 15), "location": "El Paso, TX"},
        ],
        "employees": [
            {"id": "employee-001", "name": "Michael Brown", "department": "ERO"},
        ],
        "sources": [
            {"id": "source-001", "type": "FOIA", "title": "FOIA Response 2025"},
        ],
        "relationships": sample_relationships,
    }
