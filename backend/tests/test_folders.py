from __future__ import annotations

from sqlalchemy import select

from app.models import Folder, User
from tests_helpers import register_and_login


def test_register_creates_root_folder(client, session) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "root@example.com",
            "username": "root-user",
            "nickname": "Root",
            "password": "secret123",
        },
    )

    assert register_response.status_code == 201
    user = session.scalar(select(User).where(User.username == "root-user"))
    assert user is not None
    root_folder = session.scalar(
        select(Folder).where(Folder.owner_id == user.id, Folder.parent_id.is_(None))
    )
    assert root_folder is not None
    assert root_folder.name == "/"
    assert root_folder.path_cache == "/"


def test_get_root_folder_returns_existing_root(client) -> None:
    headers = register_and_login(client, "root2@example.com", "root-user-2")

    response = client.get("/api/folders/root", headers=headers)

    assert response.status_code == 200
    assert response.json()["name"] == "/"
    assert response.json()["path_cache"] == "/"


def test_create_folder_defaults_to_root_parent(client) -> None:
    headers = register_and_login(client, "folder@example.com", "folder-user")

    root_response = client.get("/api/folders/root", headers=headers)
    create_response = client.post("/api/folders", headers=headers, json={"name": "docs"})

    assert create_response.status_code == 201
    assert create_response.json()["parent_id"] == root_response.json()["id"]
    assert create_response.json()["path_cache"] == "/docs"


def test_create_nested_folder_and_list_contents(client) -> None:
    headers = register_and_login(client, "nested@example.com", "nested-user")
    parent_response = client.post("/api/folders", headers=headers, json={"name": "projects"})
    child_response = client.post(
        "/api/folders",
        headers=headers,
        json={"name": "2026", "parent_id": parent_response.json()["id"]},
    )

    contents_response = client.get(
        f"/api/folders/{parent_response.json()['id']}/contents",
        headers=headers,
    )

    assert child_response.status_code == 201
    assert child_response.json()["path_cache"] == "/projects/2026"
    assert contents_response.status_code == 200
    assert [item["name"] for item in contents_response.json()["folders"]] == ["2026"]


def test_create_folder_rejects_duplicate_sibling_name(client) -> None:
    headers = register_and_login(client, "dup-folder@example.com", "dup-folder-user")

    first_response = client.post("/api/folders", headers=headers, json={"name": "shared"})
    second_response = client.post("/api/folders", headers=headers, json={"name": "shared"})

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Folder name already exists in this location"


def test_create_folder_rejects_reserved_root_name(client) -> None:
    headers = register_and_login(client, "reserved@example.com", "reserved-user")

    response = client.post("/api/folders", headers=headers, json={"name": "/"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Folder name is reserved"


def test_create_folder_rejects_missing_parent(client) -> None:
    headers = register_and_login(client, "missing-parent@example.com", "missing-parent-user")

    response = client.post(
        "/api/folders",
        headers=headers,
        json={"name": "docs", "parent_id": "46a32477-04c8-4f43-badb-4b7f60c4f303"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Folder not found"


def test_folder_access_is_isolated_per_owner(client) -> None:
    owner_headers = register_and_login(client, "owner@example.com", "owner-user")
    intruder_headers = register_and_login(client, "intruder@example.com", "intruder-user")
    folder_response = client.post("/api/folders", headers=owner_headers, json={"name": "private"})

    response = client.get(
        f"/api/folders/{folder_response.json()['id']}",
        headers=intruder_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Folder not found"


def test_delete_root_folder_is_forbidden(client) -> None:
    headers = register_and_login(client, "root-delete@example.com", "root-delete-user")
    root_response = client.get("/api/folders/root", headers=headers)

    response = client.delete(f"/api/folders/{root_response.json()['id']}", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Root folder cannot be deleted"


def test_delete_folder_removes_resource(client) -> None:
    headers = register_and_login(client, "delete@example.com", "delete-user")
    folder_response = client.post("/api/folders", headers=headers, json={"name": "trash"})

    delete_response = client.delete(f"/api/folders/{folder_response.json()['id']}", headers=headers)
    get_response = client.get(f"/api/folders/{folder_response.json()['id']}", headers=headers)

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_rename_folder_updates_subtree_paths(client) -> None:
    headers = register_and_login(client, "rename-folder@example.com", "rename-folder-user")
    parent_response = client.post("/api/folders", headers=headers, json={"name": "projects"})
    child_response = client.post(
        "/api/folders",
        headers=headers,
        json={"name": "2026", "parent_id": parent_response.json()["id"]},
    )

    rename_response = client.patch(
        f"/api/folders/{parent_response.json()['id']}",
        headers=headers,
        json={"name": "archives"},
    )
    child_get_response = client.get(f"/api/folders/{child_response.json()['id']}", headers=headers)

    assert rename_response.status_code == 200
    assert rename_response.json()["name"] == "archives"
    assert rename_response.json()["path_cache"] == "/archives"
    assert child_get_response.status_code == 200
    assert child_get_response.json()["path_cache"] == "/archives/2026"


def test_rename_root_folder_is_forbidden(client) -> None:
    headers = register_and_login(client, "rename-root@example.com", "rename-root-user")
    root_response = client.get("/api/folders/root", headers=headers)

    rename_response = client.patch(
        f"/api/folders/{root_response.json()['id']}",
        headers=headers,
        json={"name": "new-root"},
    )

    assert rename_response.status_code == 400
    assert rename_response.json()["detail"] == "Root folder cannot be renamed"
