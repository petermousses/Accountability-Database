# API Reference

The pipeline exposes a FastAPI REST API on port 8000. All endpoints are mounted under the `/api` prefix. Interactive documentation is available at `/docs` (Swagger UI) and `/redoc` when the server is running.

Base URL: `http://localhost:8000/api`

## Endpoints

---

### POST /api/upload

Upload one or more documents to start a pipeline run.

**Request**

- Content-Type: `multipart/form-data`
- Body: One or more files under the `files` field

**Response** `200 OK`

```json
{
  "run_id": "run-a1b2c3d4e5f6",
  "document_count": 2,
  "status": "uploaded",
  "message": "Uploaded 2 document(s). Pipeline run initialized."
}
```

**Response Model**: `UploadResponse`

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `string` | Unique pipeline run identifier |
| `document_count` | `integer` | Number of files accepted |
| `status` | `string` | Always `"uploaded"` on success |
| `message` | `string` | Human-readable confirmation |

**Example (curl)**

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "files=@incident_report.txt" \
  -F "files=@employee_roster.csv"
```

**Behavior**

Files are saved to `uploads/{run_id}/{filename}`. A pipeline run record is created in the in-memory store with status `uploaded`.

---

### GET /api/status/{run_id}

Check the current status of a pipeline run.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | `string` | Pipeline run identifier from the upload response |

**Response** `200 OK`

```json
{
  "run_id": "run-a1b2c3d4e5f6",
  "current_stage": "process_documents",
  "completed": false,
  "requires_human_input": true,
  "error_count": 0,
  "ollama_requests": [
    {
      "request_id": "ollama-req-abc123",
      "file_id": "incident_report.txt",
      "file_path": "uploads/run-a1b2c3d4e5f6/incident_report.txt",
      "extraction_type": "entity_extraction",
      "prompt_template": "Extract all named entities..."
    }
  ]
}
```

**Response Model**: `PipelineStatusResponse`

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `string` | Pipeline run identifier |
| `current_stage` | `string` | Current processing stage |
| `completed` | `boolean` | Whether the pipeline has finished |
| `requires_human_input` | `boolean` | Whether the pipeline is waiting for Ollama responses |
| `error_count` | `integer` | Number of errors encountered |
| `ollama_requests` | `array` | Pending Ollama analysis requests (present when `requires_human_input` is true) |

**Error** `404 Not Found`

```json
{
  "detail": "Pipeline run run-invalid not found"
}
```

---

### POST /api/ollama-response

Submit Ollama analysis results for a paused pipeline run. This endpoint is called by the LLM workflow orchestrator after it fulfills the Ollama requests.

**Request Body** (`application/json`)

```json
{
  "run_id": "run-a1b2c3d4e5f6",
  "responses": [
    {
      "request_id": "ollama-req-abc123",
      "extracted_data": {
        "entities": [
          {"name": "John Smith", "type": "person", "identifiers": ["ICE-12345"]},
          {"name": "El Paso Processing Center", "type": "organization", "identifiers": []}
        ],
        "relationships": [
          {"source": "John Smith", "target": "excessive force incident", "type": "COMMITTED", "confidence": 0.9}
        ]
      },
      "confidence": 0.85,
      "raw_response": "Extracted entities from document..."
    }
  ]
}
```

**Request Model**: `OllamaResponseSubmission`

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `string` | Pipeline run to resume |
| `responses` | `array` | List of Ollama response objects matching the pending requests |

**Response** `200 OK`

```json
{
  "status": "accepted",
  "run_id": "run-a1b2c3d4e5f6",
  "response_count": 1
}
```

**Error** `400 Bad Request`

```json
{
  "detail": "Pipeline is not waiting for Ollama responses"
}
```

**Error** `404 Not Found`

```json
{
  "detail": "Pipeline run run-invalid not found"
}
```

---

### GET /api/results/{run_id}

Retrieve the full results of a pipeline run.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | `string` | Pipeline run identifier |

**Response** `200 OK`

```json
{
  "run_id": "run-a1b2c3d4e5f6",
  "agents": [
    {"id": "agent-abc123", "name": "John Smith", "badge_number": "ICE-12345", "status": "Suspected"}
  ],
  "violations": [
    {"id": "violation-def456", "type": "abuse", "description": "Excessive force", "severity": "severe"}
  ],
  "incidents": [],
  "relationships": [
    {"source_id": "agent-abc123", "target_id": "violation-def456", "relationship_type": "COMMITTED"}
  ],
  "analysis_report": {
    "repeat_offenders": [],
    "severity_distribution": {"severe": 1},
    "summary_stats": {"total_agents": 1, "total_violations": 1}
  },
  "cypher_scripts": {
    "nodes": "output/exports/01-import-nodes.cypher",
    "relationships": "output/exports/02-import-relationships.cypher"
  },
  "json_exports": {
    "agents": "output/exports/agents.json",
    "violations": "output/exports/violations.json"
  },
  "report_path": "output/analysis_report.md",
  "errors": []
}
```

**Response Model**: `PipelineResultResponse`

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `string` | Pipeline run identifier |
| `agents` | `array` | Extracted and deduplicated agent records |
| `violations` | `array` | Extracted violation records |
| `incidents` | `array` | Extracted incident records |
| `relationships` | `array` | Entity relationship records |
| `analysis_report` | `object` or `null` | Correlation analysis findings |
| `cypher_scripts` | `object` | Map of script name to file path |
| `json_exports` | `object` | Map of entity type to export file path |
| `report_path` | `string` | Path to the generated markdown report |
| `errors` | `array` | List of error records from all stages |

---

### POST /api/foia/generate

Generate FOIA request letters for specified federal agencies.

**Request Body** (`application/json`)

```json
{
  "agencies": ["ICE", "CBP", "DHS"],
  "subject": "ICE enforcement actions and personnel records",
  "description": "All records related to enforcement actions in El Paso, TX during 2024-2025",
  "date_range_start": "2024-01-01",
  "date_range_end": "2025-12-31"
}
```

**Request Model**: `FOIAGenerateRequest`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agencies` | `array[string]` | Yes | Agency codes. Supported: `ICE`, `CBP`, `DHS`, `DOJ`. Custom codes accepted. |
| `subject` | `string` | No | Request subject line. Default: `"ICE enforcement actions and personnel records"` |
| `description` | `string` | No | Detailed description. Auto-generated if empty. |
| `date_range_start` | `date` | No | Start of records time period (ISO 8601) |
| `date_range_end` | `date` | No | End of records time period (ISO 8601) |

**Response** `200 OK`

```json
{
  "files": {
    "ICE": "output/foia/foia_request_ICE_2025-06-15.txt",
    "CBP": "output/foia/foia_request_CBP_2025-06-15.txt",
    "DHS": "output/foia/foia_request_DHS_2025-06-15.txt"
  },
  "tracker_path": "output/foia/foia_tracker.csv"
}
```

**Response Model**: `FOIAGenerateResponse`

| Field | Type | Description |
|-------|------|-------------|
| `files` | `object` | Map of agency code to generated letter file path |
| `tracker_path` | `string` | Path to the FOIA tracking CSV |

---

### GET /api/history

List all pipeline runs.

**Response** `200 OK`

```json
[
  {
    "run_id": "run-a1b2c3d4e5f6",
    "created_at": "2025-06-15T10:30:00",
    "current_stage": "complete",
    "completed": true,
    "document_count": 3,
    "error_count": 0
  },
  {
    "run_id": "run-789abc",
    "created_at": "2025-06-14T08:00:00",
    "current_stage": "process_documents",
    "completed": false,
    "document_count": 1,
    "error_count": 1
  }
]
```

**Response Model**: `List[HistoryEntry]`

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `string` | Pipeline run identifier |
| `created_at` | `string` | ISO 8601 timestamp of creation |
| `current_stage` | `string` | Last known pipeline stage |
| `completed` | `boolean` | Whether the run finished |
| `document_count` | `integer` | Number of uploaded documents |
| `error_count` | `integer` | Number of errors |

Results are sorted by `created_at` descending (most recent first).

---

### GET /api/health

Health check endpoint.

**Response** `200 OK`

```json
{
  "status": "healthy",
  "timestamp": "2025-06-15T10:30:00.000000"
}
```

## Error Responses

All endpoints return standard HTTP error codes with a JSON body:

```json
{
  "detail": "Human-readable error message"
}
```

| Code | Meaning |
|------|---------|
| `400` | Bad request (e.g., submitting Ollama responses when pipeline is not waiting) |
| `404` | Resource not found (e.g., invalid `run_id`) |
| `422` | Validation error (request body does not match expected schema) |
| `500` | Internal server error |

## CORS Configuration

CORS origins are configured via `PIPELINE_CORS_ORIGINS` (comma-separated). Defaults to `http://localhost:5173,http://localhost:3000` for local development with the Vite dev server.
