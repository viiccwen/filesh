from __future__ import annotations


def register_and_login(client, email: str, username: str) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": username,
            "nickname": username.title(),
            "password": "secret123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"identifier": email, "password": "secret123"},
    )
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}
