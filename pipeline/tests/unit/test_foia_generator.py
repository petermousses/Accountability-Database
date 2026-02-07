"""Tests for FOIA request generation."""

import os

import pytest

from accountability_pipeline.core.foia_generator import (
    DEFAULT_AGENCIES,
    create_foia_request_objects,
    create_foia_tracker_csv,
    generate_foia_requests,
)
from accountability_pipeline.utils.file_handler import read_csv, read_text


class TestGenerateFoiaRequests:
    def test_single_agency(self, tmp_dir):
        result = generate_foia_requests(["ICE"], tmp_dir)
        assert "ICE" in result
        assert os.path.exists(result["ICE"])

        content = read_text(result["ICE"])
        assert "Freedom of Information Act" in content
        assert "Immigration and Customs Enforcement" in content

    def test_multiple_agencies(self, tmp_dir):
        result = generate_foia_requests(["ICE", "CBP", "DHS"], tmp_dir)
        assert len(result) == 3
        assert all(os.path.exists(p) for p in result.values())

    def test_unknown_agency(self, tmp_dir):
        result = generate_foia_requests(["UNKNOWN"], tmp_dir)
        assert "UNKNOWN" in result
        content = read_text(result["UNKNOWN"])
        assert "UNKNOWN" in content

    def test_case_insensitive_agency(self, tmp_dir):
        result = generate_foia_requests(["ice"], tmp_dir)
        assert "ICE" in result

    def test_custom_description(self, tmp_dir):
        result = generate_foia_requests(
            ["ICE"], tmp_dir, description="Specific records about X"
        )
        content = read_text(result["ICE"])
        assert "Specific records about X" in content

    def test_custom_requester_info(self, tmp_dir):
        result = generate_foia_requests(
            ["ICE"], tmp_dir,
            requester_info={"name": "Test Person", "email": "test@test.com"},
        )
        content = read_text(result["ICE"])
        assert "Test Person" in content

    def test_with_date_range(self, tmp_dir):
        from datetime import date
        result = generate_foia_requests(
            ["ICE"], tmp_dir,
            date_range_start=date(2024, 1, 1),
            date_range_end=date(2025, 12, 31),
        )
        content = read_text(result["ICE"])
        assert "2024-01-01" in content
        assert "2025-12-31" in content


class TestCreateFoiaTrackerCsv:
    def test_creates_tracker(self, tmp_dir):
        path = os.path.join(tmp_dir, "tracker.csv")
        result = create_foia_tracker_csv(path)
        assert result == path
        assert os.path.exists(path)

        rows = read_csv(path)
        assert len(rows) == 1  # Example row
        assert "request_id" in rows[0]
        assert "agency" in rows[0]
        assert "status" in rows[0]


class TestCreateFoiaRequestObjects:
    def test_create_objects(self):
        requests = create_foia_request_objects(
            agencies=["ICE", "CBP"],
            subject="Test subject",
            description="Test description",
        )
        assert len(requests) == 2
        assert requests[0].agency == "ICE"
        assert requests[1].agency == "CBP"
        assert all(r.request_id.startswith("foia-") for r in requests)

    def test_with_dates(self):
        from datetime import date
        requests = create_foia_request_objects(
            agencies=["ICE"],
            subject="Test",
            description="Test",
            date_range_start=date(2024, 1, 1),
            date_range_end=date(2025, 1, 1),
        )
        assert requests[0].date_range_start.isoformat() == "2024-01-01"
