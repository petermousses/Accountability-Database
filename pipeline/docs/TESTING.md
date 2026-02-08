# Testing Guide

The pipeline uses pytest with 247 tests and 94.7% code coverage. This document covers running tests, understanding the test structure, and adding new tests.

## Running Tests

### Full Suite

```bash
# From the pipeline/ directory, with the virtual environment activated
pytest
```

### With Coverage

```bash
pytest --cov --cov-report=term-missing
```

The coverage report shows which lines are not covered. The minimum coverage threshold is 80%, configured in `pyproject.toml`:

```toml
[tool.coverage.report]
fail_under = 80
```

Coverage is measured across three source directories:
- `accountability_pipeline/`
- `workflow/`
- `api/`

### Subset Execution

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Single test file
pytest tests/unit/test_schemas.py

# Single test function
pytest tests/unit/test_schemas.py::test_agent_model_valid

# Tests matching a keyword
pytest -k "dedup"

# Verbose output with full tracebacks
pytest -v --tb=long
```

### Async Tests

Integration tests for the FastAPI endpoints use `pytest-asyncio`. The asyncio mode is set to `auto` in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

This means any `async def test_*` function is automatically treated as an async test.

## Test Structure

```
tests/
  conftest.py                    # Shared fixtures
  __init__.py
  unit/
    __init__.py
    test_config.py               # PipelineConfig tests
    test_schemas.py              # Pydantic model tests
    test_validation.py           # Validation function tests
    test_document_processor.py   # Document parsing tests
    test_data_normalizer.py      # Dedup and normalization tests
    test_correlation_analyzer.py # Pattern analysis tests
    test_neo4j_exporter.py       # Cypher/JSON export tests
    test_foia_generator.py       # FOIA letter generation tests
    test_file_handler.py         # File I/O utility tests
    test_string_matcher.py       # Fuzzy matching tests
  integration/
    __init__.py
    test_api.py                  # FastAPI endpoint tests
    test_workflow.py             # LangGraph pipeline tests
```

### Unit Tests

Each core module has a corresponding test file. Unit tests:

- Test individual functions in isolation
- Use temporary directories for file I/O (via the `tmp_dir` fixture)
- Mock external dependencies where needed
- Cover both happy paths and error cases
- Validate Pydantic model constraints (min_length, ge, enum values, validators)

### Integration Tests

- `test_api.py`: Tests FastAPI endpoints using `httpx.AsyncClient` with the test app
- `test_workflow.py`: Tests the complete LangGraph pipeline by invoking the compiled graph with sample documents

## Fixtures

All shared fixtures are defined in `tests/conftest.py`.

### Directory Fixtures

| Fixture | Type | Description |
|---------|------|-------------|
| `tmp_dir` | `str` | Temporary directory path, cleaned up after each test |

### Entity Fixtures

| Fixture | Type | Description |
|---------|------|-------------|
| `sample_agent_dict` | `dict` | Valid agent record with all fields populated |
| `sample_agent_list` | `list[dict]` | Six agents with intentional duplicates (John/Jon Smith, Robert/Bob Johnson) |
| `sample_violation_dict` | `dict` | Valid violation record |
| `sample_violation_list` | `list[dict]` | Three violations with two duplicates (same type+date) |
| `sample_incident_dict` | `dict` | Valid incident record |
| `sample_employee_dict` | `dict` | Valid employee record |
| `sample_source_dict` | `dict` | Valid source record |
| `sample_relationship_dict` | `dict` | Valid relationship record (COMMITTED) |

### File Fixtures

| Fixture | Type | Depends On | Description |
|---------|------|------------|-------------|
| `sample_email_content` | `str` | -- | Raw email text with ICE incident report content |
| `sample_csv_content` | `str` | -- | CSV text with employee records |
| `sample_text_document` | `str` (path) | `tmp_dir` | Text file with incident report |
| `sample_email_file` | `str` (path) | `tmp_dir`, `sample_email_content` | `.eml` file with incident email |
| `sample_csv_file` | `str` (path) | `tmp_dir`, `sample_csv_content` | CSV file with employee data |
| `sample_json_file` | `str` (path) | `tmp_dir` | JSON file with agent data |

### Analysis Fixtures

| Fixture | Type | Description |
|---------|------|-------------|
| `sample_agents_for_analysis` | `list[dict]` | Three agents with IDs for correlation testing |
| `sample_violations_for_analysis` | `list[dict]` | Three violations with IDs, dates, locations, severities |
| `sample_relationships` | `list[dict]` | Six relationships linking agents to violations and incidents |
| `sample_ollama_response` | `dict` | Ollama response with extracted entities and relationships |
| `full_pipeline_data` | `dict` | Complete data set with agents, violations, incidents, employees, sources, and relationships |

## Adding New Tests

### Writing a Unit Test

1. Identify the module and function to test
2. Create or open the corresponding test file in `tests/unit/`
3. Use fixtures from `conftest.py` or create test-local data
4. Follow the Arrange-Act-Assert pattern

Example:

```python
# tests/unit/test_data_normalizer.py

def test_deduplicate_agents_merges_similar_names(sample_agent_list):
    """Agents with similar names and same badge number should merge."""
    from accountability_pipeline.core.data_normalizer import deduplicate_agents

    result = deduplicate_agents(sample_agent_list, confidence_threshold=0.85)

    # John Smith and Jon Smith should be merged
    names = [a["name"] for a in result]
    assert len(result) < len(sample_agent_list)

    # Merged record should have confidence metadata
    merged = [a for a in result if a.get("_merge_count", 0) > 1]
    assert len(merged) > 0
    assert all("_dedup_confidence" in m for m in merged)
```

### Writing an Integration Test

Integration tests exercise multiple components together. For API tests, use the FastAPI test client:

```python
# tests/integration/test_api.py

import httpx
import pytest
from api.main import app

@pytest.fixture
def client():
    return httpx.AsyncClient(app=app, base_url="http://test")

async def test_upload_and_check_status(client, tmp_dir):
    """Upload a file and verify the run appears in status."""
    # Create a test file
    import os
    test_file = os.path.join(tmp_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("Test document content")

    # Upload
    with open(test_file, "rb") as f:
        response = await client.post(
            "/api/upload",
            files={"files": ("test.txt", f, "text/plain")},
        )
    assert response.status_code == 200
    run_id = response.json()["run_id"]

    # Check status
    response = await client.get(f"/api/status/{run_id}")
    assert response.status_code == 200
    assert response.json()["run_id"] == run_id
```

### Writing a Workflow Test

```python
# tests/integration/test_workflow.py

def test_pipeline_runs_to_completion(sample_text_document):
    """Pipeline should process a document and produce results."""
    from workflow.graph import run_pipeline

    result = run_pipeline({
        "documents": [{"file_path": sample_text_document}]
    })

    assert result["completed"] is True
    assert result["current_stage"] == "complete"
    assert isinstance(result["agents"], list)
```

### Test Data Guidelines

- Use the fixtures from `conftest.py` whenever possible
- For file-based tests, always use the `tmp_dir` fixture for output
- For Pydantic model tests, test both valid and invalid inputs
- For deduplication tests, include intentional near-duplicates with known similarity
- For export tests, verify the generated Cypher syntax is valid

### Common Patterns

**Testing Pydantic validation errors:**

```python
import pytest
from pydantic import ValidationError
from accountability_pipeline.models.schemas import AgentModel

def test_agent_model_rejects_empty_name():
    with pytest.raises(ValidationError):
        AgentModel(name="")
```

**Testing file output:**

```python
def test_generates_cypher_file(tmp_dir):
    from accountability_pipeline.core.neo4j_exporter import generate_cypher_scripts

    scripts = generate_cypher_scripts(
        agents=[{"id": "a1", "name": "Test"}],
        violations=[],
        incidents=[],
        output_dir=tmp_dir,
    )

    assert "nodes" in scripts
    assert os.path.exists(scripts["nodes"])

    content = open(scripts["nodes"]).read()
    assert "MERGE" in content
    assert "a1" in content
```

**Testing deduplication behavior:**

```python
def test_agents_with_same_badge_merge(sample_agent_list):
    from accountability_pipeline.core.data_normalizer import deduplicate_agents

    result = deduplicate_agents(sample_agent_list)
    badge_counts = {}
    for agent in result:
        badge = agent.get("badge_number")
        if badge:
            badge_counts[badge] = badge_counts.get(badge, 0) + 1

    # Same badge numbers should appear only once after dedup
    for badge, count in badge_counts.items():
        assert count == 1, f"Badge {badge} appears {count} times after dedup"
```
