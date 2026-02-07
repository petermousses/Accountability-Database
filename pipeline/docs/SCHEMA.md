# Schema Reference

All models are defined in `accountability_pipeline/models/schemas.py` using Pydantic v2. They mirror the Neo4j graph schema and extend it with pipeline-specific types.

## Enums

### VerificationStatus

Verification status for agents and incidents.

| Value | String |
|-------|--------|
| `CONFIRMED` | `"Confirmed"` |
| `SUSPECTED` | `"Suspected"` |
| `OUT_OF_FRAME` | `"Out of Frame"` |

### SeverityLevel

Severity levels for violations.

| Value | String |
|-------|--------|
| `CRITICAL` | `"critical"` |
| `SEVERE` | `"severe"` |
| `MODERATE` | `"moderate"` |
| `MILD` | `"mild"` |

### ViolationType

Types of violations tracked in the system.

| Value | String |
|-------|--------|
| `EXECUTION` | `"execution"` |
| `MURDER` | `"murder"` |
| `ABUSE` | `"abuse"` |
| `ASSAULT` | `"assault"` |
| `HARASSMENT` | `"harassment"` |
| `NEGLIGENCE` | `"negligence"` |
| `MISCONDUCT` | `"misconduct"` |
| `FRAUD` | `"fraud"` |
| `CIVIL_RIGHTS` | `"civil_rights"` |
| `OTHER` | `"other"` |

### EmployeeStatus

Employment status.

| Value | String |
|-------|--------|
| `ACTIVE` | `"Active"` |
| `INACTIVE` | `"Inactive"` |
| `TERMINATED` | `"Terminated"` |

### SourceType

Types of evidence sources.

| Value | String |
|-------|--------|
| `FOIA` | `"FOIA"` |
| `NEWS` | `"news"` |
| `REPORT` | `"report"` |
| `TESTIMONY` | `"testimony"` |
| `COURT_RECORD` | `"court_record"` |
| `INTERNAL_DOCUMENT` | `"internal_document"` |
| `WHISTLEBLOWER` | `"whistleblower"` |
| `OTHER` | `"other"` |

### RelationshipType

Neo4j relationship types.

| Value | String |
|-------|--------|
| `COMMITTED` | `"COMMITTED"` |
| `INVOLVED_IN` | `"INVOLVED_IN"` |
| `DOCUMENTED_BY` | `"DOCUMENTED_BY"` |
| `RELATED_TO` | `"RELATED_TO"` |
| `EMPLOYED_AS` | `"EMPLOYED_AS"` |

### ContentType

Document content types the pipeline can process.

| Value | String |
|-------|--------|
| `EMAIL` | `"email"` |
| `TEXT` | `"text"` |
| `CSV` | `"csv"` |
| `PDF` | `"pdf"` |
| `JSON` | `"json"` |
| `HTML` | `"html"` |

### ProcessingStatus

Pipeline document processing status.

| Value | String |
|-------|--------|
| `PENDING` | `"pending"` |
| `PROCESSING` | `"processing"` |
| `AWAITING_OLLAMA` | `"awaiting_ollama"` |
| `PROCESSED` | `"processed"` |
| `FAILED` | `"failed"` |

### ExtractionType

Types of extraction Ollama can perform.

| Value | String |
|-------|--------|
| `ENTITY_EXTRACTION` | `"entity_extraction"` |
| `RELATIONSHIP_EXTRACTION` | `"relationship_extraction"` |
| `SUMMARY` | `"summary"` |
| `CLASSIFICATION` | `"classification"` |
| `SENTIMENT` | `"sentiment"` |

## Neo4j Node Models

These models map directly to Neo4j node labels.

### AgentModel

ICE agent involved in violations. Maps to Neo4j `:Agent` node.

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `id` | `str` | No | Auto-generated `"agent-{uuid12}"` | | Unique identifier |
| `name` | `str` | **Yes** | | `min_length=1`, `max_length=500`, auto-stripped | Agent full name |
| `badge_number` | `str` or `null` | No | `None` | | Badge or employee ID |
| `amount_paid` | `float` or `null` | No | `None` | `>= 0` | Salary or settlement amount |
| `address` | `str` or `null` | No | `None` | | Known address |
| `status` | `VerificationStatus` | No | `VerificationStatus.SUSPECTED` | | Verification status |
| `created_at` | `datetime` | No | UTC now | | Record creation timestamp |
| `updated_at` | `datetime` | No | UTC now | | Last update timestamp |
| `notes` | `str` or `null` | No | `None` | | Additional notes |

**Validators**: `strip_name` -- strips leading/trailing whitespace from `name`.

### ViolationModel

Documented violation. Maps to Neo4j `:Violation` node.

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `id` | `str` | No | Auto-generated `"violation-{uuid12}"` | | Unique identifier |
| `type` | `ViolationType` | **Yes** | | Must be valid enum value | Category of violation |
| `description` | `str` | **Yes** | | `min_length=1` | Detailed description |
| `date` | `date` or `null` | No | `None` | | Date of violation |
| `location` | `str` or `null` | No | `None` | | Location where it occurred |
| `victim_count` | `int` or `null` | No | `None` | `>= 0` | Number of victims |
| `severity` | `SeverityLevel` | No | `SeverityLevel.MODERATE` | | Severity classification |
| `created_at` | `datetime` | No | UTC now | | Record creation timestamp |
| `updated_at` | `datetime` | No | UTC now | | Last update timestamp |

### IncidentModel

Specific incident linking violations to agents. Maps to Neo4j `:Incident` node.

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `id` | `str` | No | Auto-generated `"incident-{uuid12}"` | | Unique identifier |
| `description` | `str` | **Yes** | | `min_length=1` | Incident description |
| `date` | `date` or `null` | No | `None` | | Date of incident |
| `location` | `str` or `null` | No | `None` | | Location |
| `verification_status` | `VerificationStatus` | No | `VerificationStatus.SUSPECTED` | | Verification level |
| `source_types` | `List[str]` | No | `[]` | | Types of sources documenting this incident |
| `created_at` | `datetime` | No | UTC now | | Record creation timestamp |
| `updated_at` | `datetime` | No | UTC now | | Last update timestamp |

### EmployeeModel

ICE employee registry entry. Maps to Neo4j `:Employee` node.

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `id` | `str` | No | Auto-generated `"employee-{uuid12}"` | | Unique identifier |
| `name` | `str` | **Yes** | | `min_length=1`, `max_length=500`, auto-stripped | Employee name |
| `badge_number` | `str` or `null` | No | `None` | | Badge or ID number |
| `department` | `str` or `null` | No | `None` | | Department name |
| `title` | `str` or `null` | No | `None` | | Job title |
| `hire_date` | `date` or `null` | No | `None` | | Date of hire |
| `location` | `str` or `null` | No | `None` | | Work location |
| `status` | `EmployeeStatus` | No | `EmployeeStatus.ACTIVE` | | Employment status |

**Validators**: `strip_name` -- strips leading/trailing whitespace from `name`.

### SourceModel

Evidence/documentation source. Maps to Neo4j `:Source` node.

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `id` | `str` | No | Auto-generated `"source-{uuid12}"` | | Unique identifier |
| `type` | `SourceType` | **Yes** | | Must be valid enum value | Source category |
| `title` | `str` | **Yes** | | `min_length=1` | Source title |
| `url` | `str` or `null` | No | `None` | | Source URL |
| `content` | `str` or `null` | No | `None` | | Raw source content |
| `date` | `date` or `null` | No | `None` | | Publication/receipt date |
| `credibility_score` | `float` | No | `0.5` | `0.0 <= x <= 1.0` | Credibility rating |

### RelationshipModel

Relationship between two nodes. Maps to Neo4j relationships.

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `source_id` | `str` | **Yes** | | | ID of the source node |
| `target_id` | `str` | **Yes** | | Must differ from `source_id` | ID of the target node |
| `relationship_type` | `RelationshipType` | **Yes** | | Must be valid enum value | Neo4j relationship type |
| `properties` | `Dict[str, Any]` | No | `{}` | | Additional relationship properties |

**Validators**: `ids_must_differ` -- model validator that raises `ValueError` if `source_id == target_id`.

## Pipeline-Specific Models

### OllamaRequest

Structured request for Ollama analysis, created by the pipeline for the LLM orchestrator to fulfill.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `request_id` | `str` | No | Auto-generated `"ollama-req-{uuid12}"` | Unique request identifier |
| `file_id` | `str` | **Yes** | | Source file identifier |
| `file_path` | `str` | **Yes** | | Path to the document |
| `extraction_type` | `ExtractionType` | **Yes** | | Type of analysis requested |
| `prompt_template` | `str` | **Yes** | | Prompt with `{content}` placeholder |
| `context` | `str` or `null` | No | `None` | Additional context for analysis |
| `expected_schema` | `Dict` or `null` | No | `None` | JSON Schema for the expected response |
| `created_at` | `datetime` | No | UTC now | Request creation timestamp |

### OllamaResponse

Response from Ollama analysis, submitted by the orchestrator.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `request_id` | `str` | **Yes** | | Matches the corresponding `OllamaRequest.request_id` |
| `extracted_data` | `Dict[str, Any]` | No | `{}` | Structured extraction results |
| `confidence` | `float` | No | `0.0` | Confidence score (`0.0`-`1.0`) |
| `raw_response` | `str` or `null` | No | `None` | Raw LLM response text |
| `processing_time_ms` | `int` or `null` | No | `None` | Processing duration in milliseconds |
| `error` | `str` or `null` | No | `None` | Error message if extraction failed |

**Properties**: `success` -- returns `True` if `error is None` and `extracted_data` is non-empty.

### PipelineDocument

Document being processed through the pipeline.

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `file_id` | `str` | No | Auto-generated `"doc-{uuid12}"` | | Unique document identifier |
| `file_path` | `str` | **Yes** | | | Path to the file |
| `file_name` | `str` | No | `""` | Auto-derived from `file_path` | File name |
| `content_type` | `ContentType` | No | `ContentType.TEXT` | | Detected content type |
| `raw_content` | `str` or `null` | No | `None` | | Extracted text content |
| `extracted_entities` | `Dict[str, List[Dict]]` | No | `{}` | | Extracted entity data |
| `processing_status` | `ProcessingStatus` | No | `ProcessingStatus.PENDING` | | Current processing state |
| `errors` | `List[str]` | No | `[]` | | Processing error messages |
| `created_at` | `datetime` | No | UTC now | | Document creation timestamp |

**Validators**: `set_file_name` -- model validator that derives `file_name` from `file_path` if not provided.

## Aggregate Models

### PipelineResult

Complete result from a pipeline run.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `run_id` | `str` | Auto-generated `"run-{uuid12}"` | Pipeline run identifier |
| `agents` | `List[AgentModel]` | `[]` | Extracted agents |
| `violations` | `List[ViolationModel]` | `[]` | Extracted violations |
| `incidents` | `List[IncidentModel]` | `[]` | Extracted incidents |
| `employees` | `List[EmployeeModel]` | `[]` | Extracted employees |
| `sources` | `List[SourceModel]` | `[]` | Evidence sources |
| `relationships` | `List[RelationshipModel]` | `[]` | Entity relationships |
| `analysis_report` | `Dict` or `null` | `None` | Analysis findings |
| `errors` | `List[str]` | `[]` | Pipeline errors |
| `created_at` | `datetime` | UTC now | Run start time |
| `completed_at` | `datetime` or `null` | `None` | Run completion time |

### FOIARequest

Generated FOIA request letter.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `request_id` | `str` | Auto-generated `"foia-{uuid12}"` | Request identifier |
| `agency` | `str` | **Required** | Agency code (e.g., `"ICE"`) |
| `subject` | `str` | **Required** | Request subject |
| `date_range_start` | `date` or `null` | `None` | Records start date |
| `date_range_end` | `date` or `null` | `None` | Records end date |
| `description` | `str` | **Required** | Detailed records description |
| `letter_content` | `str` | `""` | Generated letter text |
| `status` | `str` | `"draft"` | Request status |
| `created_at` | `datetime` | UTC now | Creation timestamp |

## Validation Module

Located in `accountability_pipeline/models/validation.py`.

### SCHEMA_MAP

Maps schema type strings to model classes:

| Key | Model Class |
|-----|-------------|
| `"agent"` | `AgentModel` |
| `"violation"` | `ViolationModel` |
| `"incident"` | `IncidentModel` |
| `"employee"` | `EmployeeModel` |
| `"source"` | `SourceModel` |
| `"relationship"` | `RelationshipModel` |

### Functions

**`validate_record(data, schema_type) -> Tuple[bool, List[str]]`**

Validates a single record dictionary against its Pydantic model. Returns `(is_valid, error_messages)`.

**`validate_batch(records, schema_type) -> Tuple[List[Dict], List[Dict]]`**

Validates a list of records, returning `(valid_records, invalid_records_with_errors)`.

**`check_referential_integrity(agents, violations, incidents, relationships) -> Tuple[bool, List[str]]`**

Verifies all relationship `source_id` and `target_id` values reference existing entity IDs.

**`get_schema_fields(schema_type) -> Dict[str, Any]`**

Returns the JSON Schema representation of a model via `model_json_schema()`.
