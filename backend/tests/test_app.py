from __future__ import annotations


def test_root_reports_service_status(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["service"] == "backend"
    assert response.json()["status"] == "ok"
