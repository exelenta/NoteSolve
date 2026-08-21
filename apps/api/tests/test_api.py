from pathlib import Path

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["service"] == "notesolve-api"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_rejects_untrusted_host(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Host": "attacker.example"})
    assert response.status_code == 400


def test_local_ip_web_origin_is_allowed(client: TestClient) -> None:
    response = client.options(
        "/api/v1/documents",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


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


def test_uploads_multiple_pages_and_accepts_study_options(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents",
        files=[
            ("file", ("page-1.png", b"first", "image/png")),
            ("file", ("page-2.png", b"second", "image/png")),
        ],
    )
    assert response.status_code == 201
    analyze = client.post(
        f"/api/v1/jobs/{response.json()['job_id']}/analyze",
        json={
            "subject_hint": "history",
            "language": "ko",
            "help_level": "detailed",
            "output_style": "source_faithful",
            "custom_instruction": "연표를 유지해줘",
        },
    )
    assert analyze.status_code == 202
    result = client.get(
        f"/api/v1/documents/{response.json()['document_id']}/result"
    ).json()
    assert result["result"]["document"]["subject"] == "history"


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
    assert result.json()["usage"]["total_tokens"] == 0


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


def _analyzed_document(client: TestClient, content: bytes) -> dict[str, str]:
    uploaded = client.post(
        "/api/v1/documents",
        files={"file": ("algebra.png", content, "image/png")},
    ).json()
    client.post(f"/api/v1/jobs/{uploaded['job_id']}/analyze")
    return uploaded


def test_persists_applies_and_rolls_back_vault_change_set(client: TestClient) -> None:
    uploaded = _analyzed_document(client, b"apply-and-rollback")
    created = client.post(
        f"/api/v1/documents/{uploaded['document_id']}/vault-change-sets"
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "pending"
    change_set_id = payload["change_set"]["id"]
    relative_path = payload["change_set"]["operations"][0]["path"]
    vault_file = Path(client.notesolve_vault_dir) / relative_path
    assert not vault_file.exists()

    applied = client.post(f"/api/v1/vault-change-sets/{change_set_id}/apply")
    assert applied.status_code == 200
    assert applied.json()["status"] == "applied"
    assert vault_file.exists()
    assert "## 문제 1" in vault_file.read_text(encoding="utf-8")

    rolled_back = client.post(f"/api/v1/vault-change-sets/{change_set_id}/rollback")
    assert rolled_back.status_code == 200
    assert rolled_back.json()["status"] == "rolled_back"
    assert not vault_file.exists()


def test_vault_apply_detects_change_after_preview(client: TestClient) -> None:
    uploaded = _analyzed_document(client, b"conflict")
    created = client.post(
        f"/api/v1/documents/{uploaded['document_id']}/vault-change-sets"
    ).json()
    change_set_id = created["change_set"]["id"]
    relative_path = created["change_set"]["operations"][0]["path"]
    vault_file = Path(client.notesolve_vault_dir) / relative_path
    vault_file.parent.mkdir(parents=True, exist_ok=True)
    vault_file.write_text("external edit", encoding="utf-8")

    response = client.post(f"/api/v1/vault-change-sets/{change_set_id}/apply")
    assert response.status_code == 409
    persisted = client.get(f"/api/v1/vault-change-sets/{change_set_id}").json()
    assert persisted["status"] == "conflict"
    assert vault_file.read_text(encoding="utf-8") == "external edit"


def test_vault_rollback_restores_previous_file(client: TestClient) -> None:
    uploaded = _analyzed_document(client, b"restore-previous")
    preview = client.get(
        f"/api/v1/documents/{uploaded['document_id']}/vault-preview"
    ).json()
    relative_path = preview["change_set"]["operations"][0]["path"]
    vault_file = Path(client.notesolve_vault_dir) / relative_path
    vault_file.parent.mkdir(parents=True, exist_ok=True)
    vault_file.write_text("previous note", encoding="utf-8")

    created = client.post(
        f"/api/v1/documents/{uploaded['document_id']}/vault-change-sets"
    ).json()
    change_set_id = created["change_set"]["id"]
    client.post(f"/api/v1/vault-change-sets/{change_set_id}/apply")
    assert vault_file.read_text(encoding="utf-8") != "previous note"

    response = client.post(f"/api/v1/vault-change-sets/{change_set_id}/rollback")
    assert response.status_code == 200
    assert vault_file.read_text(encoding="utf-8") == "previous note"


def test_agent_edit_job_proposes_approval_required_update(client: TestClient) -> None:
    uploaded = _analyzed_document(client, b"agent-edit")
    created = client.post(
        f"/api/v1/documents/{uploaded['document_id']}/vault-change-sets"
    ).json()
    initial_change_set_id = created["change_set"]["id"]
    applied = client.post(
        f"/api/v1/vault-change-sets/{initial_change_set_id}/apply"
    ).json()
    path = applied["change_set"]["operations"][0]["path"]
    vault_file = Path(client.notesolve_vault_dir) / path  # type: ignore[attr-defined]
    original = vault_file.read_text(encoding="utf-8")

    requested = client.post(
        f"/api/v1/vault-change-sets/{initial_change_set_id}/edit-proposals",
        json={"instruction": "풀이 끝에 핵심 요약을 추가해줘"},
    )
    assert requested.status_code == 202
    job = client.get(f"/api/v1/agent-edit-jobs/{requested.json()['job_id']}").json()
    assert job["status"] == "completed"
    assert job["usage"]["total_tokens"] == 0
    assert vault_file.read_text(encoding="utf-8") == original

    proposal = client.get(
        f"/api/v1/vault-change-sets/{job['result_change_set_id']}"
    ).json()
    assert proposal["status"] == "pending"
    operation = proposal["change_set"]["operations"][0]
    assert operation["operation"] == "update"
    assert operation["path"] == path
    assert "풀이 끝에 핵심 요약을 추가해줘" in operation["content"]

    client.post(
        f"/api/v1/vault-change-sets/{job['result_change_set_id']}/apply"
    )
    assert "풀이 끝에 핵심 요약을 추가해줘" in vault_file.read_text(encoding="utf-8")
