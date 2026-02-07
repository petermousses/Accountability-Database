"""File I/O utilities for the accountability pipeline.

Handles reading/writing JSON, CSV, and text files with atomic writes
and audit trail support.
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def read_json(file_path: str) -> Any:
    """Read and parse a JSON file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Parsed JSON data.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(data: Any, file_path: str, indent: int = 2) -> str:
    """Write data to a JSON file atomically.

    Uses a temp file + rename to prevent partial writes.

    Args:
        data: Data to serialize.
        file_path: Destination path.
        indent: JSON indentation level.

    Returns:
        The file path written to.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, default=str, ensure_ascii=False)
        os.replace(tmp_path, file_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return file_path


def read_csv(file_path: str) -> List[Dict[str, str]]:
    """Read a CSV file as a list of dictionaries.

    Args:
        file_path: Path to the CSV file.

    Returns:
        List of row dictionaries.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_csv(data: List[Dict[str, Any]], file_path: str, fieldnames: Optional[List[str]] = None) -> str:
    """Write data to a CSV file.

    Args:
        data: List of row dictionaries.
        file_path: Destination path.
        fieldnames: Column names. If None, derived from first row keys.

    Returns:
        The file path written to.
    """
    if not data:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        Path(file_path).touch()
        return file_path

    if fieldnames is None:
        fieldnames = list(data[0].keys())

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)

    return file_path


def read_text(file_path: str) -> str:
    """Read a text file.

    Args:
        file_path: Path to the text file.

    Returns:
        File contents as string.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(content: str, file_path: str) -> str:
    """Write text to a file atomically.

    Args:
        content: Text content to write.
        file_path: Destination path.

    Returns:
        The file path written to.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, file_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return file_path


def ensure_directory(dir_path: str) -> str:
    """Ensure a directory exists, creating it if necessary.

    Args:
        dir_path: Directory path.

    Returns:
        The directory path.
    """
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    return dir_path


def store_with_audit(
    data: Any,
    file_path: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Store data with an accompanying audit metadata file.

    Creates both the data file and a .meta.json sidecar with
    timestamp, source info, and any provided metadata.

    Args:
        data: Data to store (will be written as JSON).
        file_path: Destination path for the data.
        metadata: Additional metadata to include in the audit file.

    Returns:
        The data file path.
    """
    write_json(data, file_path)

    audit_data = {
        "file_path": file_path,
        "stored_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": os.path.getsize(file_path),
        **(metadata or {}),
    }

    meta_path = file_path + ".meta.json"
    write_json(audit_data, meta_path)

    return file_path


def list_files(directory: str, extension: Optional[str] = None) -> List[str]:
    """List files in a directory, optionally filtered by extension.

    Args:
        directory: Directory to scan.
        extension: File extension filter (e.g., '.json'). Include the dot.

    Returns:
        List of absolute file paths.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return []

    files = []
    for entry in sorted(dir_path.iterdir()):
        if entry.is_file():
            if extension is None or entry.suffix == extension:
                files.append(str(entry.resolve()))

    return files
