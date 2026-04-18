from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.application.shared.shares import hash_share_token
from app.domain.enums import ResourceType
from app.persistence.models import ShareLink
from tests_helpers import register_and_login


def test_create_guest_folder_share_and_access_contents(client) -> None:
    headers = register_and_login(client, "share@example.com", "share-user")
    folder_response = client.post("/api/folders", headers=headers, json={"name": "public"})
    client.post(
        "/api/folders",
        headers=headers,
        json={"name": "nested", "parent_id": folder_response.json()["id"]},
    )

    share_response = client.post(
        f"/api/folders/{folder_response.json()['id']}/share",
        headers=headers,
        json={
            "share_mode": "GUEST",
            "permission_level": "VIEW_DOWNLOAD",
            "expiry": "never",
            "invitation_emails": [],
        },
    )

    assert share_response.status_code == 201
    token = share_response.json()["share_url"].split("/s/")[1]

    access_response = client.get(f"/s/{token}")
    contents_response = client.get(f"/s/{token}/contents")

    assert access_response.status_code == 200
    assert access_response.json()["resource_type"] == "FOLDER"
    assert contents_response.status_code == 200
    assert [item["name"] for item in contents_response.json()["folders"]] == ["nested"]


def test_user_only_share_requires_authenticated_user(client) -> None:
    headers = register_and_login(client, "useronly@example.com", "useronly-user")
    folder_response = client.post("/api/folders", headers=headers, json={"name": "members"})
    share_response = client.post(
        f"/api/folders/{folder_response.json()['id']}/share",
        headers=headers,
        json={
            "share_mode": "USER_ONLY",
            "permission_level": "VIEW_DOWNLOAD",
            "expiry": "never",
            "invitation_emails": [],
        },
    )
    token = share_response.json()["share_url"].split("/s/")[1]

    unauthorized_response = client.get(f"/s/{token}")
    second_headers = register_and_login(client, "member@example.com", "member-user")
    authorized_response = client.get(f"/s/{token}", headers=second_headers)

    assert unauthorized_response.status_code == 403
    assert authorized_response.status_code == 200


def test_email_invitation_share_allows_pending_invitee_until_registration(client) -> None:
    headers = register_and_login(client, "owner-share@example.com", "owner-share-user")
    folder_response = client.post("/api/folders", headers=headers, json={"name": "invite-only"})

    response = client.post(
        f"/api/folders/{folder_response.json()['id']}/share",
        headers=headers,
        json={
            "share_mode": "EMAIL_INVITATION",
            "permission_level": "VIEW_DOWNLOAD",
            "expiry": "never",
            "invitation_emails": ["missing@example.com"],
        },
    )
    token = response.json()["share_url"].split("/s/")[1]

    unauthorized_response = client.get(f"/s/{token}")
    invited_headers = register_and_login(client, "missing@example.com", "missing-user")
    authorized_response = client.get(f"/s/{token}", headers=invited_headers)

    assert response.status_code == 201
    assert response.json()["invitation_emails"] == ["missing@example.com"]
    assert unauthorized_response.status_code == 403
    assert authorized_response.status_code == 200


def test_email_invitation_share_allows_only_invited_user(client) -> None:
    owner_headers = register_and_login(client, "owner2@example.com", "owner2-user")
    invited_headers = register_and_login(client, "invited@example.com", "invited-user")
    other_headers = register_and_login(client, "other@example.com", "other-user")
    file_folder = client.get("/api/folders/root", headers=owner_headers)
    init_response = client.post(
        "/api/files/upload/init",
        headers=owner_headers,
        json={"folder_id": file_folder.json()["id"], "filename": "doc.txt", "expected_size": 10},
    )
    client.post(
        f"/api/files/upload/{init_response.json()['session_id']}/content",
        headers=owner_headers,
        files={"file": ("doc.txt", b"share-data", "text/plain")},
    )
    finalize_response = client.post(
        "/api/files/upload/finalize",
        headers=owner_headers,
        json={"upload_session_id": init_response.json()["session_id"], "size_bytes": 10},
    )

    share_response = client.post(
        f"/api/files/{finalize_response.json()['id']}/share",
        headers=owner_headers,
        json={
            "share_mode": "EMAIL_INVITATION",
            "permission_level": "VIEW_DOWNLOAD",
            "expiry": "never",
            "invitation_emails": ["invited@example.com"],
        },
    )
    token = share_response.json()["share_url"].split("/s/")[1]

    invited_response = client.get(f"/s/{token}", headers=invited_headers)
    other_response = client.get(f"/s/{token}", headers=other_headers)

    assert invited_response.status_code == 200
    assert invited_response.json()["file"]["stored_filename"] == "doc.txt"
    assert other_response.status_code == 403

    download_response = client.get(f"/s/{token}/download", headers=invited_headers)
    assert download_response.status_code == 200
    assert download_response.content == b"share-data"


def test_share_revoke_and_duplicate_active_share(client) -> None:
    headers = register_and_login(client, "dup-share@example.com", "dup-share-user")
    folder_response = client.post("/api/folders", headers=headers, json={"name": "shared"})

    first_share = client.post(
        f"/api/folders/{folder_response.json()['id']}/share",
        headers=headers,
        json={
            "share_mode": "GUEST",
            "permission_level": "VIEW_DOWNLOAD",
            "expiry": "never",
            "invitation_emails": [],
        },
    )
    duplicate_share = client.post(
        f"/api/folders/{folder_response.json()['id']}/share",
        headers=headers,
        json={
            "share_mode": "GUEST",
            "permission_level": "VIEW_DOWNLOAD",
            "expiry": "never",
            "invitation_emails": [],
        },
    )
    token = first_share.json()["share_url"].split("/s/")[1]
    revoke_response = client.delete(
        f"/api/folders/{folder_response.json()['id']}/share",
        headers=headers,
    )
    access_response = client.get(f"/s/{token}")

    assert first_share.status_code == 201
    assert duplicate_share.status_code == 409
    assert revoke_response.status_code == 204
    assert access_response.status_code == 404


def test_expired_share_returns_gone(client, session) -> None:
    headers = register_and_login(client, "expired@example.com", "expired-user")
    folder_response = client.post("/api/folders", headers=headers, json={"name": "timebox"})
    share_response = client.post(
        f"/api/folders/{folder_response.json()['id']}/share",
        headers=headers,
        json={
            "share_mode": "GUEST",
            "permission_level": "VIEW_DOWNLOAD",
            "expiry": "hour",
            "invitation_emails": [],
        },
    )
    token = share_response.json()["share_url"].split("/s/")[1]
    share_link = session.scalar(
        select(ShareLink).where(ShareLink.token_hash == hash_share_token(token))
    )
    assert share_link is not None
    share_link.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()

    response = client.get(f"/s/{token}")

    assert response.status_code == 410


def test_share_get_update_returns_active_url_for_owner(client, session) -> None:
    headers = register_and_login(client, "owner-view@example.com", "owner-view-user")
    folder_response = client.post("/api/folders", headers=headers, json={"name": "inspect"})
    create_response = client.post(
        f"/api/folders/{folder_response.json()['id']}/share",
        headers=headers,
        json={
            "share_mode": "GUEST",
            "permission_level": "VIEW_DOWNLOAD",
            "expiry": "never",
            "invitation_emails": [],
        },
    )
    create_token = create_response.json()["share_url"].split("/s/")[1]
    share_link = session.scalar(
        select(ShareLink).where(ShareLink.token_hash == hash_share_token(create_token))
    )

    get_response = client.get(f"/api/folders/{folder_response.json()['id']}/share", headers=headers)
    patch_response = client.patch(
        f"/api/folders/{folder_response.json()['id']}/share",
        headers=headers,
        json={
            "share_mode": "USER_ONLY",
            "permission_level": "UPLOAD",
            "expiry": "day",
            "invitation_emails": [],
        },
    )

    assert create_response.status_code == 201
    assert get_response.status_code == 200
    assert share_link is not None
    assert share_link.token_ciphertext is not None
    assert create_token not in share_link.token_ciphertext
    assert get_response.json()["share_url"] == create_response.json()["share_url"]
    assert patch_response.status_code == 200
    assert patch_response.json()["share_mode"] == "USER_ONLY"
    assert patch_response.json()["resource_type"] == ResourceType.FOLDER
    assert patch_response.json()["share_url"] == create_response.json()["share_url"]


def test_folder_share_upload_permission_allows_creating_subfolder(client) -> None:
    headers = register_and_login(client, "upload-share@example.com", "upload-share-user")
    folder_response = client.post("/api/folders", headers=headers, json={"name": "dropbox"})
    share_response = client.post(
        f"/api/folders/{folder_response.json()['id']}/share",
        headers=headers,
        json={
            "share_mode": "GUEST",
            "permission_level": "UPLOAD",
            "expiry": "never",
            "invitation_emails": [],
        },
    )
    token = share_response.json()["share_url"].split("/s/")[1]

    create_response = client.post(
        f"/s/{token}/folders",
        json={"name": "guest-child"},
    )
    contents_response = client.get(f"/s/{token}/contents")

    assert create_response.status_code == 201
    assert create_response.json()["path_cache"] == "/dropbox/guest-child"
    assert [item["name"] for item in contents_response.json()["folders"]] == ["guest-child"]


def test_folder_share_upload_permission_allows_uploading_file(client) -> None:
    headers = register_and_login(client, "upload-file-share@example.com", "upload-file-share-user")
    folder_response = client.post("/api/folders", headers=headers, json={"name": "incoming"})
    share_response = client.post(
        f"/api/folders/{folder_response.json()['id']}/share",
        headers=headers,
        json={
            "share_mode": "GUEST",
            "permission_level": "UPLOAD",
            "expiry": "never",
            "invitation_emails": [],
        },
    )
    token = share_response.json()["share_url"].split("/s/")[1]

    upload_response = client.post(
        f"/s/{token}/files",
        files={"file": ("guest-note.txt", b"hello from guest", "text/plain")},
    )
    contents_response = client.get(f"/s/{token}/contents")
    file_id = upload_response.json()["id"]
    download_response = client.get(f"/s/{token}/files/{file_id}/download")

    assert upload_response.status_code == 201
    assert upload_response.json()["stored_filename"] == "guest-note.txt"
    assert contents_response.status_code == 200
    assert [item["stored_filename"] for item in contents_response.json()["files"]] == [
        "guest-note.txt"
    ]
    assert download_response.status_code == 200
    assert download_response.content == b"hello from guest"


def test_folder_share_without_upload_permission_rejects_file_upload(client) -> None:
    headers = register_and_login(client, "upload-denied@example.com", "upload-denied-user")
    folder_response = client.post("/api/folders", headers=headers, json={"name": "readonly"})
    share_response = client.post(
        f"/api/folders/{folder_response.json()['id']}/share",
        headers=headers,
        json={
            "share_mode": "GUEST",
            "permission_level": "VIEW_DOWNLOAD",
            "expiry": "never",
            "invitation_emails": [],
        },
    )
    token = share_response.json()["share_url"].split("/s/")[1]

    upload_response = client.post(
        f"/s/{token}/files",
        files={"file": ("blocked.txt", b"nope", "text/plain")},
    )

    assert upload_response.status_code == 403


def test_file_share_overrides_folder_share_policy(client) -> None:
    owner_headers = register_and_login(client, "matrix-owner@example.com", "matrix-owner-user")
    invited_headers = register_and_login(
        client,
        "matrix-invited@example.com",
        "matrix-invited-user",
    )
    other_headers = register_and_login(client, "matrix-other@example.com", "matrix-other-user")

    folder_response = client.post(
        "/api/folders",
        headers=owner_headers,
        json={"name": "shared-root"},
    )
    init_response = client.post(
        "/api/files/upload/init",
        headers=owner_headers,
        json={
            "folder_id": folder_response.json()["id"],
            "filename": "matrix.txt",
            "expected_size": 6,
        },
    )
    client.post(
        f"/api/files/upload/{init_response.json()['session_id']}/content",
        headers=owner_headers,
        files={"file": ("matrix.txt", b"secret", "text/plain")},
    )
    finalize_response = client.post(
        "/api/files/upload/finalize",
        headers=owner_headers,
        json={"upload_session_id": init_response.json()["session_id"], "size_bytes": 6},
    )

    folder_share = client.post(
        f"/api/folders/{folder_response.json()['id']}/share",
        headers=owner_headers,
        json={
            "share_mode": "GUEST",
            "permission_level": "VIEW_DOWNLOAD",
            "expiry": "never",
            "invitation_emails": [],
        },
    )
    file_share = client.post(
        f"/api/files/{finalize_response.json()['id']}/share",
        headers=owner_headers,
        json={
            "share_mode": "EMAIL_INVITATION",
            "permission_level": "DELETE",
            "expiry": "never",
            "invitation_emails": ["matrix-invited@example.com"],
        },
    )
    token = folder_share.json()["share_url"].split("/s/")[1]

    guest_metadata = client.get(f"/s/{token}/files/{finalize_response.json()['id']}")
    invited_metadata = client.get(
        f"/s/{token}/files/{finalize_response.json()['id']}",
        headers=invited_headers,
    )
    other_metadata = client.get(
        f"/s/{token}/files/{finalize_response.json()['id']}",
        headers=other_headers,
    )
    delete_response = client.delete(
        f"/s/{token}/files/{finalize_response.json()['id']}",
        headers=invited_headers,
    )

    assert folder_share.status_code == 201
    assert file_share.status_code == 201
    assert guest_metadata.status_code == 403
    assert invited_metadata.status_code == 200
    assert other_metadata.status_code == 403
    assert delete_response.status_code == 204
