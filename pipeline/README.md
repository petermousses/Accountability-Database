# Accountability Pipeline

FOIA data processing pipeline for the ICE Accountability Knowledge Graph. Ingests FOIA documents, extracts structured data about agents, violations, and incidents, and exports to a Neo4j graph database for analysis.

## Overview

The pipeline processes FOIA documents through a LangGraph state machine:

```
Upload -> Intake -> Document Processing -> (Ollama Analysis) -> Normalization/Dedup -> Correlation Analysis -> Neo4j Export -> Report Generation
```

Core capabilities:

- Parse text, email, CSV, JSON, and HTML documents
- Extract entities (agents, violations, incidents) using regex and optional Ollama LLM analysis
- Deduplicate records using fuzzy name matching (rapidfuzz)
- Identify cross-incident patterns and co-perpetrator networks
- Generate Cypher import scripts and JSON exports for Neo4j
- Produce FOIA request letters for federal agencies
- Serve results through a FastAPI REST API with a React frontend

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ (for the UI)
- Neo4j 5.x (running via parent `docker-compose.yml`)

### Python Setup

```bash
cd pipeline

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the package with all dependencies
pip install -e ".[dev]"

# Download the spaCy language model
python -m spacy download en_core_web_sm
```

### UI Setup

```bash
cd ui
npm install
```

### Environment Variables

Configuration is loaded from environment variables with the `PIPELINE_` prefix, or from a `.env` file:

```bash
# .env
PIPELINE_NEO4J_URI=bolt://localhost:7687
PIPELINE_NEO4J_USER=neo4j
PIPELINE_NEO4J_PASSWORD=
PIPELINE_NEO4J_DATABASE=neo4j
PIPELINE_FUZZY_MATCH_THRESHOLD=0.85
PIPELINE_LOG_LEVEL=INFO
PIPELINE_CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

See `accountability_pipeline/config.py` for the full list of configuration options.

## Running

### Start the API Server

```bash
# From the pipeline/ directory
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API is available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

### Start the UI Development Server

```bash
cd ui
npm run dev
```

The UI runs at `http://localhost:5173` and connects to the API at port 8000.

### Run the Pipeline Programmatically

```python
from workflow.graph import run_pipeline

result = run_pipeline({
    "documents": [
        {"file_path": "/path/to/document.txt", "content_type": "text"}
    ]
})

print(result["agents"])
print(result["violations"])
print(result["report_path"])
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov --cov-report=term-missing

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run a specific test file
pytest tests/unit/test_schemas.py -v
```

The test suite contains 247 tests with 94.7% coverage. The coverage threshold is configured at 80% in `pyproject.toml`.

## Docker

### Build and Run with Docker Compose

```bash
# From the pipeline/ directory
docker compose up --build
```

This starts:
- `pipeline-api` on port 8000 (FastAPI)
- `pipeline-ui` on port 5173 (Nginx serving built Vite app)

Both services connect to the `accountability-net` network defined in the parent `docker-compose.yml`, giving them access to the Neo4j database.

### Build the API Image Standalone

```bash
docker build -t accountability-pipeline .
docker run -p 8000:8000 --env-file .env accountability-pipeline
```

## Project Structure

```
pipeline/
  accountability_pipeline/     # Core Python package
    core/                      # Processing modules
      document_processor.py    # Document parsing and entity extraction
      data_normalizer.py       # Fuzzy dedup and normalization
      correlation_analyzer.py  # Pattern analysis across entities
      neo4j_exporter.py        # Cypher script and JSON export generation
      foia_generator.py        # FOIA letter generation
    models/
      schemas.py               # Pydantic v2 models for all entities
      validation.py            # Schema validation and integrity checks
    utils/
      file_handler.py          # Atomic file I/O with audit trails
      string_matcher.py        # Fuzzy name matching (rapidfuzz)
      logger.py                # Structured logging (structlog)
    config.py                  # Environment-based configuration
  workflow/                    # LangGraph state machine
    state.py                   # PipelineState TypedDict
    nodes.py                   # Node functions for each stage
    graph.py                   # Graph construction and execution
  api/                         # FastAPI application
    main.py                    # App factory and middleware
    routes.py                  # REST endpoint handlers
  ui/                          # React frontend (Vite + TypeScript)
  tests/                       # pytest suite (unit + integration)
  docs/                        # Architecture and reference documentation
```

## Further Reading

- [Architecture](docs/ARCHITECTURE.md) -- System design and data flow
- [API Reference](docs/API.md) -- FastAPI endpoint documentation
- [Workflow](docs/WORKFLOW.md) -- LangGraph pipeline stages
- [Schema Reference](docs/SCHEMA.md) -- Pydantic model definitions
- [Integration Guide](docs/INTEGRATION.md) -- Ollama, Neo4j, and orchestrator setup
- [Testing Guide](docs/TESTING.md) -- Running tests and adding new ones
- [System Prompt](SYSTEM_PROMPT.md) -- LLM orchestrator instructions
