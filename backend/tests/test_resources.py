from __future__ import annotations

from tests_helpers import register_and_login


def upload_file(
    client,
    headers: dict[str, str],
    folder_id: str,
    filename: str,
    content: bytes,
    content_type: str,
) -> None:
    init_response = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={
            "folder_id": folder_id,
            "filename": filename,
            "content_type": content_type,
            "expected_size": len(content),
        },
    )
    assert init_response.status_code == 201

    content_response = client.post(
        f"/api/files/upload/{init_response.json()['session_id']}/content",
        headers=headers,
        files={"file": (filename, content, content_type)},
    )
    assert content_response.status_code == 204

    finalize_response = client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={
            "upload_session_id": init_response.json()["session_id"],
            "size_bytes": len(content),
        },
    )
    assert finalize_response.status_code == 200


def test_search_resources_returns_paginated_results(client) -> None:
    headers = register_and_login(client, "search@example.com", "search-user")
    root_response = client.get("/api/folders/root", headers=headers)
    root_id = root_response.json()["id"]

    client.post("/api/folders", headers=headers, json={"name": "zeta"})
    client.post("/api/folders", headers=headers, json={"name": "alpha"})
    upload_file(
        client,
        headers,
        root_id,
        "budget.xlsx",
        b"budget-data",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    upload_file(client, headers, root_id, "roadmap.md", b"roadmap-data", "text/markdown")

    first_page_response = client.get(
        "/api/resources/search",
        headers=headers,
        params={
            "parent_id": root_id,
            "sort_by": "name",
            "order": "asc",
            "page": 1,
            "page_size": 2,
        },
    )
    second_page_response = client.get(
        "/api/resources/search",
        headers=headers,
        params={
            "parent_id": root_id,
            "sort_by": "name",
            "order": "asc",
            "page": 2,
            "page_size": 2,
        },
    )

    assert first_page_response.status_code == 200
    assert first_page_response.json()["pagination"] == {
        "page": 1,
        "page_size": 2,
        "total_items": 4,
        "total_pages": 2,
    }
    assert [
        (
            item["item_type"],
            item["folder"]["name"]
            if item["item_type"] == "FOLDER"
            else item["file"]["stored_filename"],
        )
        for item in first_page_response.json()["items"]
    ] == [("FOLDER", "alpha"), ("FILE", "budget.xlsx")]

    assert second_page_response.status_code == 200
    assert [
        (
            item["item_type"],
            item["folder"]["name"]
            if item["item_type"] == "FOLDER"
            else item["file"]["stored_filename"],
        )
        for item in second_page_response.json()["items"]
    ] == [("FILE", "roadmap.md"), ("FOLDER", "zeta")]


def test_search_resources_filters_and_sorts_files_by_size(client) -> None:
    headers = register_and_login(client, "resource-filter@example.com", "resource-filter-user")
    root_response = client.get("/api/folders/root", headers=headers)
    root_id = root_response.json()["id"]

    upload_file(client, headers, root_id, "report-2025.pdf", b"short", "application/pdf")
    upload_file(
        client,
        headers,
        root_id,
        "report-2026.pdf",
        b"much-longer-report",
        "application/pdf",
    )
    upload_file(client, headers, root_id, "notes.txt", b"memo", "text/plain")

    response = client.get(
        "/api/resources/search",
        headers=headers,
        params={
            "parent_id": root_id,
            "q": "report",
            "type": "FILE",
            "sort_by": "size",
            "order": "desc",
            "page": 1,
            "page_size": 8,
        },
    )

    assert response.status_code == 200
    assert response.json()["pagination"] == {
        "page": 1,
        "page_size": 8,
        "total_items": 2,
        "total_pages": 1,
    }
    assert [item["file"]["stored_filename"] for item in response.json()["items"]] == [
        "report-2026.pdf",
        "report-2025.pdf",
    ]
