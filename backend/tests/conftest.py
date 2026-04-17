from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_db_session
from app.core.storage import ObjectStorage, StoredObject
from app.dependencies.storage import get_object_storage
from app.main import app
from app.models.base import Base


class InMemoryObjectStorage(ObjectStorage):
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], tuple[bytes, str | None]] = {}

    def put_object(
        self,
        bucket: str,
        object_key: str,
        data: bytes,
        content_type: str | None,
    ) -> None:
        self.objects[(bucket, object_key)] = (data, content_type)

    def get_object(self, bucket: str, object_key: str) -> StoredObject:
        data, content_type = self.objects[(bucket, object_key)]
        return StoredObject(data=data, content_type=content_type)

    def delete_object(self, bucket: str, object_key: str) -> None:
        self.objects.pop((bucket, object_key), None)

    def object_exists(self, bucket: str, object_key: str) -> bool:
        return (bucket, object_key) in self.objects


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(engine)

    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    object_storage = InMemoryObjectStorage()

    def override_get_db_session() -> Iterator[Session]:
        yield session

    def override_get_object_storage() -> InMemoryObjectStorage:
        return object_storage

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_object_storage] = override_get_object_storage
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
