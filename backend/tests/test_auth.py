from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.models import User


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
