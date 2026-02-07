"""Integration tests for the FastAPI backend."""

import io
import os

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestUploadEndpoint:
    def test_upload_single_file(self, client):
        file_content = b"Test document content about Agent John Smith."
        files = [("files", ("test.txt", io.BytesIO(file_content), "text/plain"))]
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["document_count"] == 1
        assert data["run_id"].startswith("run-")
        assert data["status"] == "uploaded"

    def test_upload_multiple_files(self, client):
        files = [
            ("files", ("doc1.txt", io.BytesIO(b"Content 1"), "text/plain")),
            ("files", ("doc2.csv", io.BytesIO(b"name,value\na,1"), "text/csv")),
        ]
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200
        assert response.json()["document_count"] == 2


class TestStatusEndpoint:
    def test_status_after_upload(self, client):
        files = [("files", ("test.txt", io.BytesIO(b"test"), "text/plain"))]
        upload_resp = client.post("/api/upload", files=files)
        run_id = upload_resp.json()["run_id"]

        status_resp = client.get(f"/api/status/{run_id}")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["run_id"] == run_id
        assert data["completed"] is False

    def test_status_not_found(self, client):
        response = client.get("/api/status/nonexistent-id")
        assert response.status_code == 404


class TestOllamaResponseEndpoint:
    def test_submit_response(self, client):
        # First upload
        files = [("files", ("test.txt", io.BytesIO(b"test"), "text/plain"))]
        upload_resp = client.post("/api/upload", files=files)
        run_id = upload_resp.json()["run_id"]

        # Manually set requires_human_input for testing
        from api.routes import _pipeline_runs
        _pipeline_runs[run_id]["requires_human_input"] = True

        # Submit Ollama response
        response = client.post("/api/ollama-response", json={
            "run_id": run_id,
            "responses": [{"request_id": "req-001", "extracted_data": {"entities": []}}],
        })
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_submit_when_not_waiting(self, client):
        files = [("files", ("test.txt", io.BytesIO(b"test"), "text/plain"))]
        upload_resp = client.post("/api/upload", files=files)
        run_id = upload_resp.json()["run_id"]

        response = client.post("/api/ollama-response", json={
            "run_id": run_id,
            "responses": [],
        })
        assert response.status_code == 400


class TestResultsEndpoint:
    def test_results_after_upload(self, client):
        files = [("files", ("test.txt", io.BytesIO(b"test"), "text/plain"))]
        upload_resp = client.post("/api/upload", files=files)
        run_id = upload_resp.json()["run_id"]

        response = client.get(f"/api/results/{run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id

    def test_results_not_found(self, client):
        response = client.get("/api/results/nonexistent-id")
        assert response.status_code == 404


class TestFOIAEndpoint:
    def test_generate_foia(self, client, tmp_dir, monkeypatch):
        monkeypatch.setenv("PIPELINE_FOIA_OUTPUT_DIR", tmp_dir)
        response = client.post("/api/foia/generate", json={
            "agencies": ["ICE"],
            "subject": "Test request",
        })
        assert response.status_code == 200
        data = response.json()
        assert "ICE" in data["files"]
        assert data["tracker_path"] != ""

    def test_generate_foia_multiple(self, client, tmp_dir, monkeypatch):
        monkeypatch.setenv("PIPELINE_FOIA_OUTPUT_DIR", tmp_dir)
        response = client.post("/api/foia/generate", json={
            "agencies": ["ICE", "CBP"],
        })
        assert response.status_code == 200
        assert len(response.json()["files"]) == 2


class TestHistoryEndpoint:
    def test_empty_history(self, client):
        # Clear existing runs first
        from api.routes import _pipeline_runs
        _pipeline_runs.clear()

        response = client.get("/api/history")
        assert response.status_code == 200
        assert response.json() == []

    def test_history_after_uploads(self, client):
        from api.routes import _pipeline_runs
        _pipeline_runs.clear()

        for i in range(3):
            files = [("files", (f"doc{i}.txt", io.BytesIO(b"test"), "text/plain"))]
            client.post("/api/upload", files=files)

        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
