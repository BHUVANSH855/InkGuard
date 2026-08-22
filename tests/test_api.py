"""Tests for InkGuard Flask API endpoints."""

import os
import sys
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    with flask_app.test_client() as c:
        yield c


class TestHealthEndpoint:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.get_json()["name"] == "InkGuard"


class TestCheckEndpoint:
    def test_returns_200(self, client):
        r = client.post("/check", json={"text": "I have a dog."})
        assert r.status_code == 200

    def test_required_keys(self, client):
        r = client.post("/check", json={"text": "i is going home."})
        d = r.get_json()
        for k in (
            "corrected",
            "highlighted",
            "errors",
            "score",
            "grade",
            "word_count",
            "error_count",
            "skipped_regions",
        ):
            assert k in d, f"Missing key: {k}"

    def test_empty_text_400(self, client):
        assert client.post("/check", json={"text": ""}).status_code == 400

    def test_no_body_400(self, client):
        assert client.post("/check", json={}).status_code == 400

    def test_clean_text_score_100(self, client):
        d = client.post(
            "/check", json={"text": "The server is running correctly."}
        ).get_json()
        assert d["score"] == 100

    def test_errors_detected(self, client):
        d = client.post("/check", json={"text": "i is going home."}).get_json()
        assert d["error_count"] > 0

    def test_technical_regions_reported(self, client):
        text = "Run `python app.py --port 5000` to start.\n```bash\ncode\n```"
        d = client.post("/check", json={"text": text}).get_json()
        assert d["skipped_regions"] >= 1


class TestBatchEndpoint:
    def test_returns_200(self, client):
        r = client.post(
            "/batch", json={"documents": [{"id": "a", "text": "I have a dog."}]}
        )
        assert r.status_code == 200

    def test_summary_keys(self, client):
        d = client.post(
            "/batch",
            json={
                "documents": [
                    {"id": "a", "text": "Good text."},
                    {"id": "b", "text": "i is bad."},
                ]
            },
        ).get_json()
        assert "summary" in d
        for k in ("total_documents", "checked", "total_errors", "average_score"):
            assert k in d["summary"]

    def test_empty_docs_400(self, client):
        assert client.post("/batch", json={"documents": []}).status_code == 400

    def test_caps_at_50(self, client):
        docs = [{"id": str(i), "text": "I have a dog."} for i in range(60)]
        d = client.post("/batch", json={"documents": docs}).get_json()
        assert len(d["results"]) <= 50

    def test_skips_empty_text(self, client):
        d = client.post(
            "/batch",
            json={
                "documents": [
                    {"id": "a", "text": "Good text."},
                    {"id": "b", "text": ""},
                ]
            },
        ).get_json()
        skipped = [r for r in d["results"] if r.get("skipped")]
        assert len(skipped) == 1


class TestUploadEndpoint:
    def test_txt_upload(self, client):
        r = client.post(
            "/upload",
            data={"file": (BytesIO(b"I have a dog."), "test.txt")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 200
        assert r.get_json()["filename"] == "test.txt"

    def test_no_file_400(self, client):
        r = client.post("/upload", data={}, content_type="multipart/form-data")
        assert r.status_code == 400

    def test_md_upload_skips_code(self, client):
        content = b"Good docs.\n```python\ni is bad code\n```\nMore good text."
        r = client.post(
            "/upload",
            data={"file": (BytesIO(content), "README.md")},
            content_type="multipart/form-data",
        )
        d = r.get_json()
        assert d["skipped_regions"] >= 1


class TestExportEndpoint:
    def test_returns_json(self, client):
        r = client.post("/export", json={"text": "I have a dog."})
        assert r.status_code == 200
        d = r.get_json()
        assert "generated_at" in d
        assert d["generated_at"].endswith("Z")


class TestLandingPage:
    def test_index_200(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"InkGuard" in r.data


class TestDashboardAuth:
    def test_dashboard_redirects_unauthenticated(self, client):
        r = client.get("/dashboard")
        assert r.status_code == 302

    def test_login_page_200(self, client):
        r = client.get("/dashboard/login")
        assert r.status_code == 200
