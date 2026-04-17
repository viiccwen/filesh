from __future__ import annotations

from app.core.config import settings


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
