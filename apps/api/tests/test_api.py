from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["service"] == "notesolve-api"


def test_upload_and_job_status(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("worksheet.png", b"fake-png-content", "image/png")},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "ingested"
    assert payload["duplicate"] is False

    job = client.get(f"/api/v1/jobs/{payload['job_id']}")
    assert job.status_code == 200
    assert job.json()["document_id"] == payload["document_id"]


def test_duplicate_upload_reuses_document(client: TestClient) -> None:
    files = {"file": ("worksheet.png", b"same-file", "image/png")}
    first = client.post("/api/v1/documents", files=files).json()
    second = client.post("/api/v1/documents", files=files).json()
    assert second["duplicate"] is True
    assert second["document_id"] == first["document_id"]


def test_rejects_unsupported_content_type(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415


def test_rejects_large_upload(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("large.png", b"x" * (1024 * 1024 + 1), "image/png")},
    )
    assert response.status_code == 413
