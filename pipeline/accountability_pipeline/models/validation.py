"""Schema validation utilities for the accountability pipeline.

Provides validation functions that check data against Pydantic models
and return structured error reports.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Type

from pydantic import BaseModel, ValidationError

from accountability_pipeline.models.schemas import (
    AgentModel,
    EmployeeModel,
    IncidentModel,
    RelationshipModel,
    SourceModel,
    ViolationModel,
)

# Map of schema type strings to their Pydantic model classes
SCHEMA_MAP: Dict[str, Type[BaseModel]] = {
    "agent": AgentModel,
    "violation": ViolationModel,
    "incident": IncidentModel,
    "employee": EmployeeModel,
    "source": SourceModel,
    "relationship": RelationshipModel,
}


def validate_record(data: Dict[str, Any], schema_type: str) -> Tuple[bool, List[str]]:
    """Validate a single record against its schema.

    Args:
        data: Dictionary of record data.
        schema_type: One of 'agent', 'violation', 'incident', 'employee', 'source', 'relationship'.

    Returns:
        Tuple of (is_valid, list_of_error_messages).

    Raises:
        ValueError: If schema_type is not recognized.
    """
    model_class = SCHEMA_MAP.get(schema_type)
    if model_class is None:
        raise ValueError(f"Unknown schema type: {schema_type!r}. Must be one of: {list(SCHEMA_MAP.keys())}")

    try:
        model_class.model_validate(data)
        return True, []
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            errors.append(f"{loc}: {err['msg']}")
        return False, errors


def validate_batch(records: List[Dict[str, Any]], schema_type: str) -> Tuple[List[Dict], List[Dict]]:
    """Validate a batch of records, separating valid from invalid.

    Args:
        records: List of record dictionaries.
        schema_type: Schema type to validate against.

    Returns:
        Tuple of (valid_records, invalid_records_with_errors).
        Each invalid record is a dict with 'record' and 'errors' keys.
    """
    valid = []
    invalid = []

    for record in records:
        is_valid, errors = validate_record(record, schema_type)
        if is_valid:
            valid.append(record)
        else:
            invalid.append({"record": record, "errors": errors})

    return valid, invalid


def check_referential_integrity(
    agents: List[Dict],
    violations: List[Dict],
    incidents: List[Dict],
    relationships: List[Dict],
) -> Tuple[bool, List[str]]:
    """Check that all relationship endpoints reference existing entities.

    Args:
        agents: List of agent records.
        violations: List of violation records.
        incidents: List of incident records.
        relationships: List of relationship records.

    Returns:
        Tuple of (all_valid, list_of_integrity_errors).
    """
    known_ids = set()
    for collection in [agents, violations, incidents]:
        for record in collection:
            record_id = record.get("id")
            if record_id:
                known_ids.add(record_id)

    errors = []
    for rel in relationships:
        source_id = rel.get("source_id")
        target_id = rel.get("target_id")

        if source_id and source_id not in known_ids:
            errors.append(f"Relationship references unknown source_id: {source_id}")
        if target_id and target_id not in known_ids:
            errors.append(f"Relationship references unknown target_id: {target_id}")

    return len(errors) == 0, errors


def get_schema_fields(schema_type: str) -> Dict[str, Any]:
    """Get the field definitions for a schema type.

    Args:
        schema_type: Schema type name.

    Returns:
        Dictionary mapping field names to their JSON schema info.

    Raises:
        ValueError: If schema_type is not recognized.
    """
    model_class = SCHEMA_MAP.get(schema_type)
    if model_class is None:
        raise ValueError(f"Unknown schema type: {schema_type!r}. Must be one of: {list(SCHEMA_MAP.keys())}")

    return model_class.model_json_schema()
