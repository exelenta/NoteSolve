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


def test_analyzes_uploaded_document_with_fake_provider(client: TestClient) -> None:
    uploaded = client.post(
        "/api/v1/documents",
        files={"file": ("worksheet.png", b"fake-image", "image/png")},
    ).json()
    analyze = client.post(f"/api/v1/jobs/{uploaded['job_id']}/analyze")
    assert analyze.status_code == 202

    job = client.get(f"/api/v1/jobs/{uploaded['job_id']}").json()
    assert job["stage"] == "completed"
    assert job["progress"] == 100

    result = client.get(f"/api/v1/documents/{uploaded['document_id']}/result")
    assert result.status_code == 200
    assert result.json()["provider"] == "fake"
    assert result.json()["result"]["problems"][0]["answer_markdown"] == "$x = 1$"
    assert result.json()["result"]["problems"][0]["verification"]["status"] == "verified"
    assert result.json()["result"]["problems"][0]["verification"]["method"] == (
        "independent_fake_check"
    )


def test_result_returns_conflict_before_analysis(client: TestClient) -> None:
    uploaded = client.post(
        "/api/v1/documents",
        files={"file": ("worksheet.png", b"not-analyzed", "image/png")},
    ).json()
    response = client.get(f"/api/v1/documents/{uploaded['document_id']}/result")
    assert response.status_code == 409


def test_builds_approval_required_obsidian_preview(client: TestClient) -> None:
    uploaded = client.post(
        "/api/v1/documents",
        files={"file": ("algebra-sheet.png", b"vault-preview-image", "image/png")},
    ).json()
    client.post(f"/api/v1/jobs/{uploaded['job_id']}/analyze")

    response = client.get(f"/api/v1/documents/{uploaded['document_id']}/vault-preview")
    assert response.status_code == 200
    change_set = response.json()["change_set"]
    assert change_set["requires_approval"] is True
    operation = change_set["operations"][0]
    assert operation["operation"] == "create"
    assert operation["path"].startswith("NoteSolve/math/")
    assert operation["path"].endswith(".md")
    assert "# math - algebra-sheet" in operation["content"]
    assert "## 문제 1" in operation["content"]
    assert "$x = 1$" in operation["content"]
