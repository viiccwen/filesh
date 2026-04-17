from __future__ import annotations


def test_healthcheck_reports_database_reachable(client) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}
