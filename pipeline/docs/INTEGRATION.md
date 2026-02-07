# Integration Guide

This document explains how the pipeline connects with external systems: the LLM workflow orchestrator, Ollama, and Neo4j.

## System Context

```
+---------------------+       +-------------------+       +----------+
|  LLM Orchestrator   |<----->|  Ollama (local)   |       |  Neo4j   |
|  (Claude/LangChain) |       |  llama3 / mistral |       |  5.x     |
+----------+----------+       +-------------------+       +----+-----+
           |                                                    ^
           | HTTP                                               |
           v                                                    |
+----------+----------+                                         |
|   Pipeline API      +------- Cypher scripts / JSON exports ---+
|   (FastAPI :8000)   |
+---------------------+
```

The pipeline is a stateless data processor. It does not call Ollama or Neo4j directly. Instead:

1. It produces **OllamaRequest** objects for the orchestrator to fulfill
2. It produces **Cypher scripts** and **JSON exports** for Neo4j import

## Ollama Integration

### Architecture

The pipeline cannot call Ollama directly. This is a deliberate design decision that keeps the pipeline deterministic, testable, and independent of any specific LLM backend. The LLM workflow orchestrator mediates all Ollama interactions.

### Request Flow

#### Step 1: Pipeline Creates Requests

When processing documents, the pipeline creates `OllamaRequest` objects:

```python
# Inside process_documents_node
ollama_req = request_ollama_analysis(file_path, "entity_extraction")
```

Each request contains:
- `request_id`: Unique tracking ID (e.g., `"ollama-req-a1b2c3"`)
- `file_id`: Source file identifier
- `file_path`: Path to the document on disk
- `extraction_type`: One of `entity_extraction`, `relationship_extraction`, `summary`, `classification`, `sentiment`
- `prompt_template`: Complete prompt with a `{content}` placeholder
- `expected_schema`: JSON Schema describing the expected response format

#### Step 2: Pipeline Pauses

The pipeline sets `requires_human_input=True` and exits the graph. The API exposes the pending requests through `GET /api/status/{run_id}`.

#### Step 3: Orchestrator Fulfills Requests

The orchestrator should:

1. Poll `GET /api/status/{run_id}` until `requires_human_input` is `true`
2. Read the `ollama_requests` array from the response
3. For each request:
   a. Read the document content from `file_path`
   b. Replace `{content}` in `prompt_template` with the document text
   c. Send the completed prompt to Ollama
   d. Parse the JSON response from Ollama
   e. Validate against `expected_schema` if provided
   f. Construct an `OllamaResponse` dict

4. Submit all responses via `POST /api/ollama-response`:

```json
{
  "run_id": "run-abc123",
  "responses": [
    {
      "request_id": "ollama-req-a1b2c3",
      "extracted_data": {
        "entities": [
          {"name": "John Smith", "type": "person", "identifiers": ["ICE-12345"]}
        ]
      },
      "confidence": 0.85
    }
  ]
}
```

#### Step 4: Pipeline Resumes

After responses are submitted, the pipeline resumes from the normalize stage. This can be triggered programmatically:

```python
from workflow.graph import resume_pipeline_after_ollama

final_state = resume_pipeline_after_ollama(paused_state, ollama_responses)
```

### Extraction Types and Prompt Templates

| Type | Purpose | Expected Response Keys |
|------|---------|----------------------|
| `entity_extraction` | Extract named entities | `entities`: list of `{name, type, identifiers}` |
| `relationship_extraction` | Identify entity relationships | `relationships`: list of `{source, target, type, confidence}` |
| `summary` | Document summary | `summary`, `key_people`, `events`, `dates`, `locations` |
| `classification` | Document categorization | `categories`, `confidence`, `reasoning` |
| `sentiment` | Tone and severity analysis | `tone`, `severity_indicators`, `key_concerns` |

### Handling Ollama Errors

If Ollama fails or returns invalid data, the orchestrator should still submit a response with the `error` field set:

```json
{
  "request_id": "ollama-req-a1b2c3",
  "extracted_data": {},
  "confidence": 0.0,
  "error": "Ollama returned invalid JSON: ..."
}
```

The normalize node handles missing or empty `extracted_data` gracefully by falling back to regex-only extraction.

### Skipping Ollama

To run the pipeline without Ollama analysis, the orchestrator can submit empty responses for all requests:

```json
{
  "run_id": "run-abc123",
  "responses": [
    {
      "request_id": "ollama-req-a1b2c3",
      "extracted_data": {},
      "confidence": 0.0
    }
  ]
}
```

## Neo4j Integration

### Connection Configuration

Neo4j connection parameters are set via environment variables:

```bash
PIPELINE_NEO4J_URI=bolt://localhost:7687
PIPELINE_NEO4J_USER=neo4j
PIPELINE_NEO4J_PASSWORD=
PIPELINE_NEO4J_DATABASE=neo4j
```

The parent repository's `docker-compose.yml` runs Neo4j with authentication disabled (`NEO4J_AUTH: "none"`) on the `accountability-net` Docker network.

### Export Outputs

The pipeline does not write directly to Neo4j. It generates two types of export files:

#### Cypher Scripts

Generated in `output/exports/`:

- `01-import-nodes.cypher` -- Creates/merges all node types (Agent, Violation, Incident, Employee, Source) using `MERGE` for idempotency
- `02-import-relationships.cypher` -- Creates/merges all relationships with `MATCH` on both endpoints

Example generated Cypher:

```cypher
MERGE (a:Agent {id: "agent-abc123"})
SET a += {
  name: "John Smith",
  badge_number: "ICE-12345",
  status: "Suspected"
};

MATCH (a:Agent {id: "agent-abc123"})
MATCH (b:Violation {id: "violation-def456"})
MERGE (a)-[:COMMITTED]->(b);
```

#### JSON Exports

One JSON file per entity type in `output/exports/`:
- `agents.json`
- `violations.json`
- `incidents.json`
- `employees.json`
- `sources.json`
- `relationships.json`

These files are compatible with `neo4j-admin import` and APOC procedures like `apoc.load.json`.

### Importing Into Neo4j

#### Option A: Cypher Shell

```bash
cat output/exports/01-import-nodes.cypher | cypher-shell -u neo4j -p password
cat output/exports/02-import-relationships.cypher | cypher-shell -u neo4j -p password
```

#### Option B: Neo4j Browser

Copy and paste the contents of each Cypher file into the Neo4j Browser at `http://localhost:7474`.

#### Option C: APOC JSON Import

```cypher
CALL apoc.load.json("file:///exports/agents.json") YIELD value
MERGE (a:Agent {id: value.id})
SET a += value;
```

### Pre-Export Validation

Before generating exports, `validate_neo4j_readiness()` checks:

1. All node records have an `id` field
2. No duplicate IDs within entity types
3. All relationship `source_id` and `target_id` values reference existing nodes

Validation warnings are included in the pipeline `errors` list but do not block export.

## Orchestrator Integration

### Overview

The LLM workflow orchestrator (defined in `SYSTEM_PROMPT.md`) drives the pipeline through the API. A typical orchestration sequence:

```
1. Upload documents     -> POST /api/upload
2. Check status         -> GET /api/status/{run_id}     (poll until requires_human_input or completed)
3. Fulfill Ollama reqs  -> Send to Ollama, POST /api/ollama-response
4. Check status again   -> GET /api/status/{run_id}     (poll until completed)
5. Retrieve results     -> GET /api/results/{run_id}
6. Verify Neo4j export  -> Check cypher_scripts and json_exports paths
7. Import to Neo4j      -> Run Cypher scripts
```

### Error Recovery

The orchestrator should check `error_count` in the status response and the `errors` array in results. Common recoverable situations:

- **Document parsing failure**: Individual files may fail without blocking the pipeline. Check `errors` for `"stage": "process_documents"` entries.
- **Ollama timeout**: Submit a response with the `error` field. The pipeline continues with regex-only extraction.
- **Export validation warnings**: The pipeline generates exports even with warnings. The orchestrator should review validation errors before importing to Neo4j.

### FOIA Generation

FOIA requests can be generated independently of the main pipeline:

```bash
curl -X POST http://localhost:8000/api/foia/generate \
  -H "Content-Type: application/json" \
  -d '{
    "agencies": ["ICE", "CBP"],
    "subject": "Enforcement actions in El Paso",
    "date_range_start": "2024-01-01",
    "date_range_end": "2025-12-31"
  }'
```

Supported agencies with pre-configured addresses: `ICE`, `CBP`, `DHS`, `DOJ`. Custom agency codes are accepted but require the requester to fill in the agency address.

## Network Architecture (Docker)

When running in Docker, all services connect through the `accountability-net` bridge network defined in the parent `docker-compose.yml`:

| Service | Container | Port | Network Alias |
|---------|-----------|------|---------------|
| Neo4j | `accountability-neo4j` | 7474 (HTTP), 7687 (Bolt) | `neo4j` |
| Pipeline API | `pipeline-api` | 8000 | `pipeline-api` |
| Pipeline UI | `pipeline-ui` | 5173 | `pipeline-ui` |

The pipeline API reaches Neo4j at `bolt://accountability-neo4j:7687` within the Docker network.
