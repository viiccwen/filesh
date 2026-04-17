from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.persistence.models import File, User
from app.workers.cleanup import handle_cleanup_event


def test_register_login_refresh_and_get_me(client) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "vic@example.com",
            "username": "vic",
            "nickname": "Vic",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == "vic@example.com"

    login_response = client.post(
        "/api/auth/login",
        json={"identifier": "vic@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["token_type"] == "bearer"
    assert login_body["user"]["username"] == "vic"
    assert settings.refresh_token_cookie_name in login_response.cookies

    me_response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {login_body['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["nickname"] == "Vic"

    refresh_response = client.post("/api/auth/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["token_type"] == "bearer"
    assert settings.refresh_token_cookie_name in refresh_response.cookies


def test_register_rejects_duplicate_email(client) -> None:
    payload = {
        "email": "dup@example.com",
        "username": "dup-user",
        "nickname": "Dup",
        "password": "secret123",
    }

    first_response = client.post("/api/auth/register", json=payload)
    second_response = client.post(
        "/api/auth/register",
        json={**payload, "username": "dup-user-2"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Email already registered"


def test_login_rejects_invalid_password(client) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "wrong@example.com",
            "username": "wrong-user",
            "nickname": "Wrong",
            "password": "secret123",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={"identifier": "wrong-user", "password": "badpass123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_register_rejects_duplicate_username(client) -> None:
    first_payload = {
        "email": "first@example.com",
        "username": "shared-user",
        "nickname": "First",
        "password": "secret123",
    }
    second_payload = {
        "email": "second@example.com",
        "username": "shared-user",
        "nickname": "Second",
        "password": "secret123",
    }

    first_response = client.post("/api/auth/register", json=first_payload)
    second_response = client.post("/api/auth/register", json=second_payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Username taken"


def test_refresh_rejects_missing_cookie(client) -> None:
    response = client.post("/api/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token missing"


def test_refresh_rejects_invalid_cookie(client) -> None:
    client.cookies.set(settings.refresh_token_cookie_name, "bad-token")
    response = client.post("/api/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token"


def test_logout_clears_refresh_cookie(client) -> None:
    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["message"] == "Logged out"
    assert f"{settings.refresh_token_cookie_name}=" in response.headers["set-cookie"]


def test_get_me_requires_authentication(client) -> None:
    response = client.get("/api/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_get_me_rejects_invalid_access_token(client) -> None:
    response = client.get("/api/users/me", headers={"Authorization": "Bearer bad-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid access token"


def test_get_me_rejects_missing_user(client) -> None:
    access_token = create_access_token(str(uuid.uuid4()))

    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "User not found"


def test_update_me_updates_username_and_nickname(client) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "edit-me@example.com",
            "username": "edit-me",
            "nickname": "Edit Me",
            "password": "secret123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"identifier": "edit-me@example.com", "password": "secret123"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    update_response = client.patch(
        "/api/users/me",
        headers=headers,
        json={"username": "edited-user", "nickname": "Edited Nick"},
    )
    me_response = client.get("/api/users/me", headers=headers)

    assert update_response.status_code == 200
    assert update_response.json()["username"] == "edited-user"
    assert update_response.json()["nickname"] == "Edited Nick"
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "edited-user"


def test_update_me_rejects_duplicate_username(client) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "first-user@example.com",
            "username": "first-user",
            "nickname": "First",
            "password": "secret123",
        },
    )
    client.post(
        "/api/auth/register",
        json={
            "email": "second-user@example.com",
            "username": "second-user",
            "nickname": "Second",
            "password": "secret123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"identifier": "second-user@example.com", "password": "secret123"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    update_response = client.patch(
        "/api/users/me",
        headers=headers,
        json={"username": "first-user", "nickname": "Still Second"},
    )

    assert update_response.status_code == 409
    assert update_response.json()["detail"] == "Username taken"


def test_change_password_updates_credentials(client) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "password-edit@example.com",
            "username": "password-edit",
            "nickname": "Password Edit",
            "password": "secret123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"identifier": "password-edit@example.com", "password": "secret123"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    change_response = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "secret123", "new_password": "newsecret123"},
    )
    old_login_response = client.post(
        "/api/auth/login",
        json={"identifier": "password-edit@example.com", "password": "secret123"},
    )
    new_login_response = client.post(
        "/api/auth/login",
        json={"identifier": "password-edit@example.com", "password": "newsecret123"},
    )

    assert change_response.status_code == 200
    assert change_response.json()["message"] == "Password updated"
    assert old_login_response.status_code == 401
    assert new_login_response.status_code == 200


def test_change_password_rejects_incorrect_current_password(client) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "wrong-current@example.com",
            "username": "wrong-current",
            "nickname": "Wrong Current",
            "password": "secret123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"identifier": "wrong-current@example.com", "password": "secret123"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    change_response = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "badpass123", "new_password": "newsecret123"},
    )

    assert change_response.status_code == 401
    assert change_response.json()["detail"] == "Current password is incorrect"


def test_change_password_rejects_same_password(client) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "same-password@example.com",
            "username": "same-password",
            "nickname": "Same Password",
            "password": "secret123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"identifier": "same-password@example.com", "password": "secret123"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    change_response = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "secret123", "new_password": "secret123"},
    )

    assert change_response.status_code == 400
    assert (
        change_response.json()["detail"] == "New password must be different from current password"
    )


def test_login_rejects_inactive_user(client, session) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "inactive@example.com",
            "username": "inactive-user",
            "nickname": "Inactive",
            "password": "secret123",
        },
    )
    user = session.scalar(select(User).where(User.username == "inactive-user"))
    assert user is not None
    user.is_active = False
    session.commit()

    response = client.post(
        "/api/auth/login",
        json={"identifier": "inactive-user", "password": "secret123"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User is inactive"


def test_delete_account_removes_user_and_publishes_cleanup_event(
    client,
    session,
    object_storage,
    event_publisher,
) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "delete-me@example.com",
            "username": "delete-me",
            "nickname": "Delete Me",
            "password": "secret123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"identifier": "delete-me@example.com", "password": "secret123"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
    root_response = client.get("/api/folders/root", headers=headers)
    init_response = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={
            "folder_id": root_response.json()["id"],
            "filename": "account.txt",
            "expected_size": 7,
        },
    )
    client.post(
        f"/api/files/upload/{init_response.json()['session_id']}/content",
        headers=headers,
        files={"file": ("account.txt", b"cleanup", "text/plain")},
    )
    finalize_response = client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={"upload_session_id": init_response.json()["session_id"], "size_bytes": 7},
    )

    file = session.scalar(select(File).where(File.id == uuid.UUID(finalize_response.json()["id"])))
    assert file is not None
    assert object_storage.object_exists(file.storage_bucket, file.object_key)

    delete_response = client.delete("/api/auth/me", headers=headers)

    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Account deleted"
    assert f"{settings.refresh_token_cookie_name}=" in delete_response.headers["set-cookie"]
    assert session.scalar(select(User).where(User.email == "delete-me@example.com")) is None
    assert event_publisher.events[-1].payload["event_type"] == "account.delete_requested"

    handle_cleanup_event(event_publisher.events[-1].payload, object_storage)

    assert not object_storage.object_exists(file.storage_bucket, file.object_key)


def test_delete_account_requires_authentication(client) -> None:
    response = client.delete("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"
