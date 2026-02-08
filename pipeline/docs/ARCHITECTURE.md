# Architecture

## System Overview

The Accountability Pipeline is a multi-stage document processing system that transforms unstructured FOIA documents into structured knowledge graph data. It is designed to operate under the control of an LLM workflow orchestrator, which handles external service calls (Ollama) that the pipeline cannot make directly.

```
                              +---------------------+
                              |   LLM Orchestrator   |
                              |  (workflow control)  |
                              +----------+----------+
                                         |
                          Ollama req/resp | API calls
                                         |
+----------+    +--------+    +----------v----------+    +---------+
|  React   +--->| FastAPI+--->|   LangGraph Workflow |<-->|  Neo4j  |
|    UI    |<---+  API   |<---| (pipeline/workflow/) |    | (graph) |
+----------+    +--------+    +----------+----------+    +---------+
                                         |
                              +----------v----------+
                              | accountability_pipeline |
                              |                         |
                              |  core/                  |
                              |    document_processor   |
                              |    data_normalizer      |
                              |    correlation_analyzer  |
                              |    neo4j_exporter        |
                              |    foia_generator        |
                              |  models/                |
                              |    schemas, validation  |
                              |  utils/                 |
                              |    file_handler          |
                              |    string_matcher        |
                              |    logger                |
                              +-------------------------+
```

## Data Flow

### 1. Document Upload

The user uploads files through the React UI or directly to the FastAPI `POST /api/upload` endpoint. Files are stored under `uploads/{run_id}/` and a pipeline run is initialized.

### 2. Intake

The `intake_node` validates that documents were provided, generates a unique `run_id`, and initializes the pipeline state. If no documents are found, it routes to the error handler.

### 3. Document Processing

The `process_documents_node` calls `document_processor.parse_text_document()` to extract structured fields from each file:

- **Text files**: Regex-based extraction of dates, names, badge numbers, and locations.
- **Email files (.eml)**: Header parsing (from, to, subject, date) plus body text extraction.
- **CSV files**: Row-by-row record parsing via `csv.DictReader`.
- **JSON files**: Direct data loading.

Each document also generates an `OllamaRequest` for deeper LLM analysis. These requests are placed in the pipeline state for the orchestrator to fulfill.

### 4. Ollama Analysis (Optional, Human-in-the-Loop)

If `OllamaRequests` are generated, the pipeline pauses by setting `requires_human_input=True` and exiting to `END`. The LLM orchestrator:

1. Reads the pending requests from `GET /api/status/{run_id}`
2. Sends document content to Ollama with the provided prompt templates
3. Posts structured responses back via `POST /api/ollama-response`

The pipeline resumes from the `normalize` stage with the Ollama data merged into state via `resume_pipeline_after_ollama()`.

### 5. Normalization and Deduplication

The `normalize_node` collects entities from both regex extraction and Ollama responses, then:

- Groups agent names using single-linkage fuzzy clustering (rapidfuzz, threshold 0.85)
- Merges duplicate agent records by keeping the most complete record
- Deduplicates violations using a union-find algorithm on matching type+date or type+location+description
- Annotates all merged records with `_dedup_confidence` scores

### 6. Correlation Analysis

The `analyze_node` runs pattern detection:

- **Repeat offenders**: Agents linked to multiple violations via relationships
- **Co-perpetrator networks**: Agents appearing in the same incidents
- **Temporal patterns**: Violation clusters grouped by year-month
- **Geographic patterns**: Location frequency analysis
- **Severity and type distributions**: Statistical breakdowns

Cross-incident connections are identified via description similarity scoring.

### 7. Neo4j Export

The `export_node` generates import-ready files:

- **Cypher scripts**: `01-import-nodes.cypher` (MERGE statements for all entity types) and `02-import-relationships.cypher` (MATCH+MERGE for relationships)
- **JSON exports**: One file per entity type, compatible with `neo4j-admin import` and APOC procedures

Before export, `validate_neo4j_readiness()` checks for missing IDs, duplicate IDs, and referential integrity violations.

### 8. Report Generation

The `report_node` produces a Markdown analysis report at `output/analysis_report.md` with tables for repeat offenders, co-perpetrator networks, severity distributions, geographic and temporal patterns.

## Module Descriptions

### `accountability_pipeline/core/`

| Module | Purpose |
|--------|---------|
| `document_processor.py` | Parses text, email, CSV, and JSON files. Extracts basic entities via regex. Creates `OllamaRequest` objects for LLM analysis. |
| `data_normalizer.py` | Fuzzy deduplication of agents and violations. Name normalization. Schema validation wrapper. |
| `correlation_analyzer.py` | Cross-entity pattern analysis. Repeat offender detection. Co-perpetrator network mapping. Report generation. |
| `neo4j_exporter.py` | Cypher script generation with safe value escaping. JSON export. Pre-export validation. |
| `foia_generator.py` | FOIA letter generation using Jinja2 templates. Tracker CSV creation. Supports ICE, CBP, DHS, and DOJ. |

### `accountability_pipeline/models/`

| Module | Purpose |
|--------|---------|
| `schemas.py` | All Pydantic v2 models: entity types (Agent, Violation, Incident, Employee, Source), relationships, pipeline-specific types (OllamaRequest, OllamaResponse, PipelineDocument), and aggregate types (PipelineResult, FOIARequest). |
| `validation.py` | Schema validation functions (`validate_record`, `validate_batch`), referential integrity checking, and schema introspection. |

### `accountability_pipeline/utils/`

| Module | Purpose |
|--------|---------|
| `file_handler.py` | Atomic JSON/CSV/text read/write operations. Audit trail sidecar files (`.meta.json`). |
| `string_matcher.py` | Fuzzy name matching with rapidfuzz. Weighted similarity scoring (token_sort + token_set + partial). Union-find clustering for name groups. Title/suffix stripping. |
| `logger.py` | Structured logging via structlog. Console or JSON output modes. Context-bound loggers. |

### `workflow/`

| Module | Purpose |
|--------|---------|
| `state.py` | `PipelineState` TypedDict definition with all fields that flow through the graph. |
| `nodes.py` | Node functions: `intake_node`, `process_documents_node`, `normalize_node`, `analyze_node`, `export_node`, `report_node`, `error_handler_node`. |
| `graph.py` | Graph construction with `StateGraph`, conditional routing functions, `compile_pipeline()`, `run_pipeline()`, and `resume_pipeline_after_ollama()`. |

### `api/`

| Module | Purpose |
|--------|---------|
| `main.py` | FastAPI app factory with CORS middleware. Mounts routes under `/api`. |
| `routes.py` | Endpoint handlers for upload, status, Ollama response submission, results, FOIA generation, history, and health check. |

## Key Design Decisions

### 1. Pipeline Cannot Call Ollama Directly

The pipeline is a stateless data processor. LLM calls are delegated to the orchestrator via structured `OllamaRequest` objects with prompt templates and expected response schemas. This keeps the pipeline deterministic and testable.

### 2. Human-in-the-Loop via Graph Interruption

When Ollama analysis is needed, the LangGraph exits to `END` with `requires_human_input=True`. The orchestrator resumes processing by calling `resume_pipeline_after_ollama()`, which builds a sub-graph starting at `normalize`. This avoids holding open long-running connections.

### 3. Union-Find for Deduplication

Both agent and violation deduplication use union-find (disjoint set) data structures for single-linkage clustering. This efficiently handles transitive matches: if A matches B and B matches C, all three merge into one record.

### 4. Atomic File Writes

All file outputs use a temp-file-then-rename pattern to prevent partial writes from corrupting data. This is critical for Cypher scripts that will be imported into Neo4j.

### 5. Cypher MERGE Over CREATE

All generated Cypher uses `MERGE` rather than `CREATE` to support idempotent re-imports. Running the same export twice does not create duplicate nodes.

### 6. Environment-Based Configuration

All configuration flows through `PipelineConfig` (pydantic-settings), which reads from `PIPELINE_`-prefixed environment variables or a `.env` file. No hardcoded paths or credentials.
