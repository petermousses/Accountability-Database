# LangGraph Workflow

The pipeline is orchestrated as a LangGraph `StateGraph` that routes documents through processing stages based on conditional logic. This document describes the state schema, nodes, edges, and the human-in-the-loop flow for Ollama integration.

## PipelineState

Defined in `workflow/state.py` as a `TypedDict` with `total=False`. Every node reads from and writes to this shared state. Fields use `total=False` so nodes can return partial updates containing only the fields they modify.

### Input Fields

| Field | Type | Description |
|-------|------|-------------|
| `documents` | `List[Dict[str, Any]]` | Uploaded document metadata. Each dict contains `file_path`, `content_type`, `file_name`, `file_id`, and `size_bytes`. |
| `config` | `Dict[str, Any]` | Pipeline configuration overrides. |

### Document Processing Fields

| Field | Type | Description |
|-------|------|-------------|
| `raw_extractions` | `List[Dict[str, Any]]` | Output from document parsing. Each dict contains `file_path`, `content_type`, `raw_content`, `metadata`, and `extracted_fields`. |
| `ollama_requests` | `List[Dict[str, Any]]` | Pending Ollama analysis requests with `request_id`, `file_id`, `extraction_type`, and `prompt_template`. |
| `ollama_responses` | `List[Dict[str, Any]]` | Completed Ollama responses with `request_id`, `extracted_data`, and `confidence`. |

### Normalized Entity Fields

| Field | Type | Description |
|-------|------|-------------|
| `agents` | `List[Dict[str, Any]]` | Normalized and deduplicated agent records. |
| `violations` | `List[Dict[str, Any]]` | Normalized violation records. |
| `incidents` | `List[Dict[str, Any]]` | Normalized incident records. |
| `employees` | `List[Dict[str, Any]]` | Normalized employee records. |
| `sources` | `List[Dict[str, Any]]` | Normalized source/evidence records. |
| `relationships` | `List[Dict[str, Any]]` | Extracted relationships between entities. |

### Analysis Fields

| Field | Type | Description |
|-------|------|-------------|
| `analysis_report` | `Dict[str, Any]` | Correlation analysis findings (repeat offenders, patterns, distributions). |
| `cross_incident_connections` | `List[Dict[str, Any]]` | Incident pairs linked by description similarity. |

### Export Fields

| Field | Type | Description |
|-------|------|-------------|
| `cypher_scripts` | `Dict[str, str]` | Map of script name to generated Cypher file path. |
| `json_exports` | `Dict[str, str]` | Map of entity type to exported JSON file path. |
| `report_path` | `str` | Path to the generated markdown analysis report. |

### Control Fields

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | Unique identifier for the pipeline run. |
| `current_stage` | `str` | Name of the last completed stage. |
| `errors` | `List[Dict[str, Any]]` | Error log. Each entry has `stage`, `message`, `timestamp`, and `details`. |
| `requires_human_input` | `bool` | Whether the pipeline is paused waiting for Ollama responses. |
| `completed` | `bool` | Whether the pipeline has finished processing. |

## Node Descriptions

### `intake_node`

- **Reads**: `documents`, `config`
- **Writes**: `run_id`, `current_stage`, `errors`, `completed`, `requires_human_input`
- **Purpose**: Validates input. Generates `run_id` if not provided. Checks that at least one document is present and all documents have a `file_path`. Initializes control fields.

### `process_documents_node`

- **Reads**: `documents`
- **Writes**: `raw_extractions`, `ollama_requests`, `current_stage`, `errors`, `requires_human_input`
- **Purpose**: Calls `parse_text_document()` for each document to extract text content and basic entities (dates, names, badge numbers, locations). Stores extraction results with audit trails. Creates an `OllamaRequest` per document for deeper entity extraction. Sets `requires_human_input=True` when Ollama requests are generated.

### `normalize_node`

- **Reads**: `raw_extractions`, `ollama_responses`
- **Writes**: `agents`, `violations`, `incidents`, `employees`, `sources`, `relationships`, `current_stage`, `errors`
- **Purpose**: Collects entities from regex extraction and Ollama responses. Runs fuzzy deduplication on agents (using configurable threshold, default 0.85). Deduplicates violations using type+date and type+location+description matching. Populates entity lists for downstream analysis.

### `analyze_node`

- **Reads**: `agents`, `violations`, `incidents`, `relationships`
- **Writes**: `analysis_report`, `cross_incident_connections`, `current_stage`, `errors`
- **Purpose**: Runs `find_agent_patterns()` to detect repeat offenders, co-perpetrator networks, temporal patterns, geographic patterns, and severity/type distributions. Runs `find_cross_incident_connections()` to find similar incidents.

### `export_node`

- **Reads**: `agents`, `violations`, `incidents`, `employees`, `sources`, `relationships`
- **Writes**: `cypher_scripts`, `json_exports`, `current_stage`, `errors`
- **Purpose**: Validates data readiness with `validate_neo4j_readiness()`. Generates `01-import-nodes.cypher` and `02-import-relationships.cypher` using MERGE statements. Generates per-entity-type JSON files.

### `report_node`

- **Reads**: `analysis_report`
- **Writes**: `report_path`, `current_stage`, `completed`
- **Purpose**: Converts the analysis findings into a markdown report. Sets `completed=True` and `current_stage="complete"`.

### `error_handler_node`

- **Reads**: `errors`
- **Writes**: `current_stage`, `completed`
- **Purpose**: Logs all errors and marks the pipeline as terminated. Sets `current_stage="error"` and `completed=True`.

## Graph Structure

```
                     +--------+
                     | intake |
                     +---+----+
                         |
              has intake errors?
                    /         \
                  yes          no
                  /             \
    +-------------+     +-------v-----------+
    |error_handler|     | process_documents |
    +------+------+     +--------+----------+
           |                     |
          END         requires_human_input?
                          /            \
                        yes             no
                        /                \
                      END         +------v-----+
                 (pause for       | normalize  |
                  Ollama)         +------+-----+
                                        |
                                 +------v-----+
                                 |  analyze   |
                                 +------+-----+
                                        |
                              >3 critical errors?
                                  /          \
                                yes           no
                                /              \
                  +-------------+       +------v-----+
                  |error_handler|       |   export   |
                  +------+------+       +------+-----+
                         |                     |
                        END              +-----v----+
                                         |  report  |
                                         +-----+----+
                                               |
                                              END
```

## Conditional Routing Functions

### `should_continue_after_intake(state)`

Checks for errors with `stage == "intake"`. Routes to `error_handler` if any exist, otherwise to `process_documents`.

### `should_continue_after_processing(state)`

Checks `requires_human_input`. Routes to `END` (pause) if true, otherwise to `normalize`.

### `should_continue_after_analysis(state)`

Counts critical errors (those containing "failed" in the message). Routes to `error_handler` if more than 3 critical errors exist, otherwise to `export`.

## Human-in-the-Loop Flow

The pipeline cannot call Ollama directly. Instead, it uses a pause-and-resume pattern.

### Pause Phase

1. `process_documents_node` creates `OllamaRequest` objects with:
   - `request_id`: Unique identifier for tracking
   - `file_id`: Source file identifier
   - `file_path`: Path to the document
   - `extraction_type`: One of `entity_extraction`, `relationship_extraction`, `summary`, `classification`, `sentiment`
   - `prompt_template`: Pre-formatted prompt with a `{content}` placeholder
   - `expected_schema`: JSON Schema for the expected response format
2. Sets `requires_human_input=True`
3. `should_continue_after_processing` routes to `END`, pausing the graph

### Resume Phase

1. The orchestrator polls `GET /api/status/{run_id}` and sees `requires_human_input=true` with pending `ollama_requests`
2. For each request, the orchestrator:
   - Reads the document content
   - Fills the `{content}` placeholder in `prompt_template`
   - Sends the prompt to Ollama
   - Validates the response against `expected_schema`
3. The orchestrator submits responses via `POST /api/ollama-response`
4. The API stores responses and clears `requires_human_input`
5. `resume_pipeline_after_ollama(state, ollama_responses)` is called, which:
   - Merges responses into state
   - Builds a sub-graph: `normalize -> analyze -> export -> report -> END`
   - Invokes the sub-graph from the `normalize` entry point

## Running the Pipeline

### Full Run (Programmatic)

```python
from workflow.graph import run_pipeline

state = run_pipeline({
    "documents": [{"file_path": "path/to/doc.txt"}]
})
```

### Resume After Ollama

```python
from workflow.graph import resume_pipeline_after_ollama

final_state = resume_pipeline_after_ollama(
    paused_state,
    ollama_responses=[
        {
            "request_id": "ollama-req-abc123",
            "extracted_data": {"entities": [...]},
            "confidence": 0.85,
        }
    ],
)
```

### Compile Without Running

```python
from workflow.graph import compile_pipeline

app = compile_pipeline()
# Use app.invoke(state) or app.stream(state) as needed
```
