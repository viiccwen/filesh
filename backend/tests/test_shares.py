from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import ResourceType, ShareLink
from app.services.shares import hash_share_token
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


def test_email_invitation_share_requires_registered_invitee(client) -> None:
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

    assert response.status_code == 400
    assert "must be registered" in response.json()["detail"]


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


def test_share_get_update_returns_redacted_url_for_owner(client) -> None:
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
    assert get_response.json()["share_url"] == "/s/[redacted]"
    assert patch_response.status_code == 200
    assert patch_response.json()["share_mode"] == "USER_ONLY"
    assert patch_response.json()["resource_type"] == ResourceType.FOLDER
