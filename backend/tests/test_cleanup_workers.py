from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models import File, UploadSession
from app.workers.cleanup import handle_cleanup_event
from tests_helpers import register_and_login


def test_upload_failed_event_is_cleaned_by_worker(
    client,
    session,
    object_storage,
    event_publisher,
) -> None:
    headers = register_and_login(client, "cleanup-upload@example.com", "cleanup-upload-user")
    root_response = client.get("/api/folders/root", headers=headers)
    init_response = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={
            "folder_id": root_response.json()["id"],
            "filename": "temp.txt",
            "expected_size": 4,
        },
    )
    upload_session_id = init_response.json()["session_id"]
    client.post(
        f"/api/files/upload/{upload_session_id}/content",
        headers=headers,
        files={"file": ("temp.txt", b"temp", "text/plain")},
    )

    upload_session = session.scalar(
        select(UploadSession).where(UploadSession.id == uuid.UUID(upload_session_id))
    )
    assert upload_session is not None
    assert object_storage.object_exists("files", upload_session.object_key)

    fail_response = client.post(
        "/api/files/upload/fail",
        headers=headers,
        json={
            "upload_session_id": upload_session_id,
            "failure_reason": "cancelled",
        },
    )

    assert fail_response.status_code == 204
    assert event_publisher.events[-1].payload["event_type"] == "upload.failed"

    handle_cleanup_event(event_publisher.events[-1].payload, object_storage)

    assert not object_storage.object_exists("files", upload_session.object_key)


def test_folder_delete_event_cleans_nested_objects(
    client,
    session,
    object_storage,
    event_publisher,
) -> None:
    headers = register_and_login(client, "cleanup-folder@example.com", "cleanup-folder-user")
    folder_response = client.post("/api/folders", headers=headers, json={"name": "trash"})

    init_response = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={
            "folder_id": folder_response.json()["id"],
            "filename": "trash.txt",
            "expected_size": 5,
        },
    )
    client.post(
        f"/api/files/upload/{init_response.json()['session_id']}/content",
        headers=headers,
        files={"file": ("trash.txt", b"trash", "text/plain")},
    )
    finalize_response = client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={"upload_session_id": init_response.json()["session_id"], "size_bytes": 5},
    )

    file = session.scalar(select(File).where(File.id == uuid.UUID(finalize_response.json()["id"])))
    assert file is not None
    assert object_storage.object_exists(file.storage_bucket, file.object_key)

    delete_response = client.delete(f"/api/folders/{folder_response.json()['id']}", headers=headers)

    assert delete_response.status_code == 204
    assert event_publisher.events[-1].payload["event_type"] == "folder.delete_requested"

    handle_cleanup_event(event_publisher.events[-1].payload, object_storage)

    assert not object_storage.object_exists(file.storage_bucket, file.object_key)
