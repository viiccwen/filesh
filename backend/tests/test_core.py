from __future__ import annotations

from datetime import timedelta

import jwt
from fastapi import Response
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import (
    clear_refresh_cookie,
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
    hash_password,
    set_refresh_cookie,
    verify_password,
)
from app.schemas.auth import RegisterRequest


def test_cors_origins_parses_csv_values() -> None:
    config = Settings(BACKEND_CORS_ORIGINS=" http://localhost:5173, https://example.com ,,")

    assert config.cors_origins == ["http://localhost:5173", "https://example.com"]


def test_password_hashing_roundtrip_and_failure() -> None:
    password_hash = hash_password("secret123")

    assert password_hash != "secret123"
    assert verify_password("secret123", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_decode_token_rejects_wrong_type() -> None:
    token = create_refresh_token("user-1")

    try:
        decode_token(token, expected_type="access")
    except jwt.InvalidTokenError as exc:
        assert "Unexpected token type" in str(exc)
    else:
        raise AssertionError("decode_token should reject mismatched token types")


def test_create_token_preserves_extra_claims() -> None:
    token = create_token(
        subject="user-1",
        token_type="access",
        expires_delta=timedelta(minutes=5),
        extra_claims={"scope": "files:read"},
    )

    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-1"
    assert payload["scope"] == "files:read"


def test_refresh_cookie_helpers_write_headers() -> None:
    response = Response()
    refresh_token = create_access_token("user-1")

    set_refresh_cookie(response, refresh_token)
    assert "set-cookie" in response.headers

    clear_refresh_cookie(response)
    set_cookie_headers = response.headers.getlist("set-cookie")
    assert any("Max-Age=0" in header for header in set_cookie_headers)


def test_register_request_enforces_password_length() -> None:
    try:
        RegisterRequest(
            email="short@example.com",
            username="short-user",
            nickname="Short",
            password="12345",
        )
    except ValidationError as exc:
        assert "at least 6 characters" in str(exc)
    else:
        raise AssertionError("RegisterRequest should reject short passwords")
