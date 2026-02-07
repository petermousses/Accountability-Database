"""Tests for file handler utilities."""

import json
import os

import pytest

from accountability_pipeline.utils.file_handler import (
    ensure_directory,
    list_files,
    read_csv,
    read_json,
    read_text,
    store_with_audit,
    write_csv,
    write_json,
    write_text,
)


class TestWriteAndReadJson:
    def test_round_trip(self, tmp_dir):
        data = {"key": "value", "nested": {"a": 1}}
        path = os.path.join(tmp_dir, "test.json")
        write_json(data, path)
        result = read_json(path)
        assert result == data

    def test_creates_parent_dirs(self, tmp_dir):
        path = os.path.join(tmp_dir, "sub", "dir", "test.json")
        write_json({"test": True}, path)
        assert os.path.exists(path)

    def test_handles_dates(self, tmp_dir):
        from datetime import datetime
        data = {"time": datetime(2025, 1, 1)}
        path = os.path.join(tmp_dir, "dates.json")
        write_json(data, path)
        result = read_json(path)
        assert result["time"] == "2025-01-01 00:00:00"

    def test_read_nonexistent(self, tmp_dir):
        with pytest.raises(FileNotFoundError):
            read_json(os.path.join(tmp_dir, "missing.json"))


class TestWriteAndReadCsv:
    def test_round_trip(self, tmp_dir):
        data = [
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"},
        ]
        path = os.path.join(tmp_dir, "test.csv")
        write_csv(data, path)
        result = read_csv(path)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"

    def test_empty_data(self, tmp_dir):
        path = os.path.join(tmp_dir, "empty.csv")
        write_csv([], path)
        assert os.path.exists(path)

    def test_custom_fieldnames(self, tmp_dir):
        data = [{"a": "1", "b": "2", "c": "3"}]
        path = os.path.join(tmp_dir, "custom.csv")
        write_csv(data, path, fieldnames=["a", "b"])
        result = read_csv(path)
        assert "a" in result[0]
        assert "b" in result[0]
        assert "c" not in result[0]


class TestWriteAndReadText:
    def test_round_trip(self, tmp_dir):
        content = "Hello, world!\nLine two."
        path = os.path.join(tmp_dir, "test.txt")
        write_text(content, path)
        result = read_text(path)
        assert result == content

    def test_unicode(self, tmp_dir):
        content = "Unicode: é à ü ñ 中文"
        path = os.path.join(tmp_dir, "unicode.txt")
        write_text(content, path)
        result = read_text(path)
        assert result == content

    def test_creates_parent_dirs(self, tmp_dir):
        path = os.path.join(tmp_dir, "new", "dir", "file.txt")
        write_text("test", path)
        assert os.path.exists(path)


class TestEnsureDirectory:
    def test_creates_new(self, tmp_dir):
        path = os.path.join(tmp_dir, "new_dir")
        result = ensure_directory(path)
        assert os.path.isdir(result)

    def test_existing_dir(self, tmp_dir):
        result = ensure_directory(tmp_dir)
        assert result == tmp_dir

    def test_nested(self, tmp_dir):
        path = os.path.join(tmp_dir, "a", "b", "c")
        ensure_directory(path)
        assert os.path.isdir(path)


class TestStoreWithAudit:
    def test_creates_data_and_meta(self, tmp_dir):
        data = {"test": "data"}
        path = os.path.join(tmp_dir, "audit_test.json")
        store_with_audit(data, path, metadata={"source": "test"})

        assert os.path.exists(path)
        assert os.path.exists(path + ".meta.json")

        meta = read_json(path + ".meta.json")
        assert meta["source"] == "test"
        assert "stored_at" in meta
        assert "size_bytes" in meta

    def test_without_metadata(self, tmp_dir):
        path = os.path.join(tmp_dir, "no_meta.json")
        store_with_audit({"x": 1}, path)
        assert os.path.exists(path + ".meta.json")


class TestListFiles:
    def test_list_all(self, tmp_dir):
        for name in ["a.txt", "b.json", "c.txt"]:
            write_text("content", os.path.join(tmp_dir, name))
        files = list_files(tmp_dir)
        assert len(files) == 3

    def test_filter_by_extension(self, tmp_dir):
        for name in ["a.txt", "b.json", "c.txt"]:
            write_text("content", os.path.join(tmp_dir, name))
        files = list_files(tmp_dir, extension=".txt")
        assert len(files) == 2

    def test_empty_directory(self, tmp_dir):
        files = list_files(tmp_dir)
        assert files == []

    def test_nonexistent_directory(self, tmp_dir):
        files = list_files(os.path.join(tmp_dir, "nonexistent"))
        assert files == []
