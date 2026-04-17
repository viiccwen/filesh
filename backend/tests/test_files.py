from __future__ import annotations

import uuid

from sqlalchemy import select

from app.application.shared.files import resolve_filename_collision
from app.models import File, UploadSession, UploadSessionStatus
from tests_helpers import register_and_login


def test_upload_init_finalize_and_get_file(client, session) -> None:
    headers = register_and_login(client, "file@example.com", "file-user")
    root_response = client.get("/api/folders/root", headers=headers)

    init_response = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={
            "folder_id": root_response.json()["id"],
            "filename": "report.pdf",
            "content_type": "application/pdf",
            "expected_size": 128,
        },
    )
    assert init_response.status_code == 201
    content_response = client.post(
        f"/api/files/upload/{init_response.json()['session_id']}/content",
        headers=headers,
        files={"file": ("report.pdf", b"pdf-content", "application/pdf")},
    )
    assert content_response.status_code == 204

    finalize_response = client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={
            "upload_session_id": init_response.json()["session_id"],
            "size_bytes": 11,
            "checksum_sha256": "a" * 64,
        },
    )
    assert finalize_response.status_code == 200
    assert finalize_response.json()["stored_filename"] == "report.pdf"
    assert finalize_response.json()["status"] == "ACTIVE"

    file_response = client.get(
        f"/api/files/{finalize_response.json()['id']}",
        headers=headers,
    )
    assert file_response.status_code == 200
    assert file_response.json()["checksum_sha256"] == "a" * 64
    download_response = client.get(
        f"/api/files/{finalize_response.json()['id']}/download",
        headers=headers,
    )
    assert download_response.status_code == 200
    assert download_response.content == b"pdf-content"

    upload_session = session.scalar(
        select(UploadSession).where(
            UploadSession.id == uuid.UUID(init_response.json()["session_id"])
        )
    )
    assert upload_session is not None
    assert upload_session.status is UploadSessionStatus.FINALIZED


def test_upload_init_auto_renames_on_collision(client, session) -> None:
    headers = register_and_login(client, "rename@example.com", "rename-user")
    root_response = client.get("/api/folders/root", headers=headers)
    folder_id = uuid.UUID(root_response.json()["id"])

    first_init = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={"folder_id": str(folder_id), "filename": "report.pdf", "expected_size": 64},
    )
    client.post(
        f"/api/files/upload/{first_init.json()['session_id']}/content",
        headers=headers,
        files={"file": ("report.pdf", b"x" * 64, "application/pdf")},
    )
    client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={"upload_session_id": first_init.json()["session_id"], "size_bytes": 64},
    )

    second_init = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={"folder_id": str(folder_id), "filename": "report.pdf", "expected_size": 64},
    )

    assert second_init.status_code == 201
    assert second_init.json()["resolved_filename"] == "report (1).pdf"
    assert resolve_filename_collision(session, folder_id, "report.pdf") == "report (2).pdf"


def test_upload_fail_marks_session_failed(client, session) -> None:
    headers = register_and_login(client, "fail@example.com", "fail-user")
    root_response = client.get("/api/folders/root", headers=headers)

    init_response = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={
            "folder_id": root_response.json()["id"],
            "filename": "broken.txt",
            "expected_size": 10,
        },
    )
    fail_response = client.post(
        "/api/files/upload/fail",
        headers=headers,
        json={
            "upload_session_id": init_response.json()["session_id"],
            "failure_reason": "network error",
        },
    )

    assert fail_response.status_code == 204
    upload_session = session.scalar(
        select(UploadSession).where(
            UploadSession.id == uuid.UUID(init_response.json()["session_id"])
        )
    )
    assert upload_session is not None
    assert upload_session.status is UploadSessionStatus.FAILED
    assert upload_session.failure_reason == "network error"


def test_upload_finalize_rejects_missing_uploaded_content(client) -> None:
    headers = register_and_login(client, "missing-content@example.com", "missing-content-user")
    root_response = client.get("/api/folders/root", headers=headers)
    init_response = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={"folder_id": root_response.json()["id"], "filename": "file.txt", "expected_size": 10},
    )

    response = client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={"upload_session_id": init_response.json()["session_id"], "size_bytes": 10},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Upload content not received"


def test_upload_finalize_rejects_failed_session(client) -> None:
    headers = register_and_login(client, "failed-finalize@example.com", "failed-finalize-user")
    root_response = client.get("/api/folders/root", headers=headers)
    init_response = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={"folder_id": root_response.json()["id"], "filename": "file.txt", "expected_size": 10},
    )
    client.post(
        "/api/files/upload/fail",
        headers=headers,
        json={
            "upload_session_id": init_response.json()["session_id"],
            "failure_reason": "oops",
        },
    )

    response = client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={"upload_session_id": init_response.json()["session_id"], "size_bytes": 10},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Upload session already failed"


def test_upload_finalize_rejects_second_finalize(client) -> None:
    headers = register_and_login(client, "repeat@example.com", "repeat-user")
    root_response = client.get("/api/folders/root", headers=headers)
    init_response = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={"folder_id": root_response.json()["id"], "filename": "file.txt", "expected_size": 10},
    )
    client.post(
        f"/api/files/upload/{init_response.json()['session_id']}/content",
        headers=headers,
        files={"file": ("file.txt", b"0123456789", "text/plain")},
    )
    first_finalize = client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={"upload_session_id": init_response.json()["session_id"], "size_bytes": 10},
    )
    second_finalize = client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={"upload_session_id": init_response.json()["session_id"], "size_bytes": 10},
    )

    assert first_finalize.status_code == 200
    assert second_finalize.status_code == 409
    assert second_finalize.json()["detail"] == "Upload session already finalized"


def test_file_access_is_isolated_per_owner(client) -> None:
    owner_headers = register_and_login(client, "owner-file@example.com", "owner-file-user")
    intruder_headers = register_and_login(client, "intruder-file@example.com", "intruder-file-user")
    root_response = client.get("/api/folders/root", headers=owner_headers)
    init_response = client.post(
        "/api/files/upload/init",
        headers=owner_headers,
        json={
            "folder_id": root_response.json()["id"],
            "filename": "secret.txt",
            "expected_size": 11,
        },
    )
    client.post(
        f"/api/files/upload/{init_response.json()['session_id']}/content",
        headers=owner_headers,
        files={"file": ("secret.txt", b"secret-data", "text/plain")},
    )
    finalize_response = client.post(
        "/api/files/upload/finalize",
        headers=owner_headers,
        json={"upload_session_id": init_response.json()["session_id"], "size_bytes": 11},
    )

    response = client.get(
        f"/api/files/{finalize_response.json()['id']}",
        headers=intruder_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_delete_file_removes_resource_and_folder_contents_shows_file(client, session) -> None:
    headers = register_and_login(client, "delete-file@example.com", "delete-file-user")
    root_response = client.get("/api/folders/root", headers=headers)
    folder_id = uuid.UUID(root_response.json()["id"])
    init_response = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={"folder_id": str(folder_id), "filename": "notes.txt", "expected_size": 20},
    )
    client.post(
        f"/api/files/upload/{init_response.json()['session_id']}/content",
        headers=headers,
        files={"file": ("notes.txt", b"notes-content", "text/plain")},
    )
    finalize_response = client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={"upload_session_id": init_response.json()["session_id"], "size_bytes": 13},
    )

    contents_response = client.get(f"/api/folders/{folder_id}/contents", headers=headers)
    assert [item["stored_filename"] for item in contents_response.json()["files"]] == ["notes.txt"]

    delete_response = client.delete(f"/api/files/{finalize_response.json()['id']}", headers=headers)
    get_response = client.get(f"/api/files/{finalize_response.json()['id']}", headers=headers)

    assert delete_response.status_code == 204
    assert get_response.status_code == 404
    assert (
        session.scalar(select(File).where(File.id == uuid.UUID(finalize_response.json()["id"])))
        is None
    )


def test_rename_file_updates_visible_name(client) -> None:
    headers = register_and_login(client, "rename-file@example.com", "rename-file-user")
    root_response = client.get("/api/folders/root", headers=headers)
    init_response = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={"folder_id": root_response.json()["id"], "filename": "draft.txt", "expected_size": 5},
    )
    client.post(
        f"/api/files/upload/{init_response.json()['session_id']}/content",
        headers=headers,
        files={"file": ("draft.txt", b"hello", "text/plain")},
    )
    finalize_response = client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={"upload_session_id": init_response.json()["session_id"], "size_bytes": 5},
    )

    rename_response = client.patch(
        f"/api/files/{finalize_response.json()['id']}",
        headers=headers,
        json={"filename": "report.txt"},
    )
    contents_response = client.get(
        f"/api/folders/{root_response.json()['id']}/contents",
        headers=headers,
    )

    assert rename_response.status_code == 200
    assert rename_response.json()["stored_filename"] == "report.txt"
    assert rename_response.json()["original_filename"] == "report.txt"
    assert rename_response.json()["version"] == 2
    assert [item["stored_filename"] for item in contents_response.json()["files"]] == ["report.txt"]


def test_rename_file_rejects_duplicate_sibling_name(client) -> None:
    headers = register_and_login(client, "rename-dupe@example.com", "rename-dupe-user")
    root_response = client.get("/api/folders/root", headers=headers)

    first_init = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={"folder_id": root_response.json()["id"], "filename": "one.txt", "expected_size": 3},
    )
    client.post(
        f"/api/files/upload/{first_init.json()['session_id']}/content",
        headers=headers,
        files={"file": ("one.txt", b"one", "text/plain")},
    )
    first_finalize = client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={"upload_session_id": first_init.json()["session_id"], "size_bytes": 3},
    )

    second_init = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={"folder_id": root_response.json()["id"], "filename": "two.txt", "expected_size": 3},
    )
    client.post(
        f"/api/files/upload/{second_init.json()['session_id']}/content",
        headers=headers,
        files={"file": ("two.txt", b"two", "text/plain")},
    )
    second_finalize = client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={"upload_session_id": second_init.json()["session_id"], "size_bytes": 3},
    )

    rename_response = client.patch(
        f"/api/files/{second_finalize.json()['id']}",
        headers=headers,
        json={"filename": "one.txt"},
    )

    assert first_finalize.status_code == 200
    assert rename_response.status_code == 409
    assert rename_response.json()["detail"] == "File name already exists in this location"
