from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.application.ports import (
    FilesRepositoryPort,
    FoldersRepositoryPort,
    SharesRepositoryPort,
    UnitOfWorkPort,
    UsersRepositoryPort,
)
from app.domain.enums import ResourceType
from app.persistence.models import File, Folder, ShareLink, UploadSession, User
from app.repositories import files as file_repository
from app.repositories import folders as folder_repository
from app.repositories import shares as share_repository
from app.repositories import users as user_repository


class SqlAlchemyUsersRepository(UsersRepositoryPort):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, user: User) -> None:
        user_repository.add_user(self.session, user)

    def get_by_email_or_username(self, *, email: str, username: str) -> User | None:
        return user_repository.get_user_by_email_or_username(
            self.session,
            email=email,
            username=username,
        )

    def get_by_identifier(self, identifier: str) -> User | None:
        return user_repository.get_user_by_identifier(self.session, identifier)

    def get_by_username(self, username: str) -> User | None:
        return user_repository.get_user_by_username(self.session, username)

    def get_active_by_id(self, user_id: uuid.UUID) -> User | None:
        return user_repository.get_active_user_by_id(self.session, user_id)


class SqlAlchemyFilesRepository(FilesRepositoryPort):
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_filenames_in_folder(self, folder_id: uuid.UUID) -> set[str]:
        return file_repository.list_filenames_in_folder(self.session, folder_id)

    def list_reserved_filenames_in_folder(self, folder_id: uuid.UUID) -> set[str]:
        return file_repository.list_reserved_filenames_in_folder(self.session, folder_id)

    def add_upload_session(self, upload_session: UploadSession) -> None:
        file_repository.add_upload_session(self.session, upload_session)

    def get_upload_session_by_owner(
        self, upload_session_id: uuid.UUID, owner_id: uuid.UUID
    ) -> UploadSession | None:
        return file_repository.get_upload_session_by_owner(
            self.session,
            upload_session_id,
            owner_id,
        )

    def add_file(self, file: File) -> None:
        file_repository.add_file(self.session, file)

    def get_by_owner(self, file_id: uuid.UUID, owner_id: uuid.UUID) -> File | None:
        return file_repository.get_file_by_owner(self.session, file_id, owner_id)

    def get_by_id(self, file_id: uuid.UUID) -> File | None:
        return file_repository.get_file_by_id(self.session, file_id)

    def list_by_folder_ids(self, folder_ids: list[uuid.UUID]) -> list[File]:
        return file_repository.list_files_by_folder_ids(self.session, folder_ids)


class SqlAlchemyFoldersRepository(FoldersRepositoryPort):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, folder: Folder) -> None:
        folder_repository.add_folder(self.session, folder)

    def get_root(self, user_id: uuid.UUID, root_folder_name: str) -> Folder | None:
        return folder_repository.get_root_folder(self.session, user_id, root_folder_name)

    def get_by_owner(self, folder_id: uuid.UUID, owner_id: uuid.UUID) -> Folder | None:
        return folder_repository.get_folder_by_owner(self.session, folder_id, owner_id)

    def get_by_id(self, folder_id: uuid.UUID) -> Folder | None:
        return folder_repository.get_folder_by_id(self.session, folder_id)

    def get_with_contents_by_owner(
        self,
        folder_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Folder | None:
        return folder_repository.get_folder_with_contents_by_owner(
            self.session,
            folder_id,
            owner_id,
        )

    def list_descendant_folder_ids(self, owner_id: uuid.UUID, path_prefix: str) -> list[uuid.UUID]:
        return folder_repository.list_descendant_folder_ids(self.session, owner_id, path_prefix)

    def list_descendant_folders(self, owner_id: uuid.UUID, path_prefix: str) -> list[Folder]:
        return folder_repository.list_descendant_folders(self.session, owner_id, path_prefix)

    def list_upload_sessions_by_folder_ids(
        self,
        folder_ids: list[uuid.UUID],
    ) -> list[UploadSession]:
        return folder_repository.list_upload_sessions_by_folder_ids(self.session, folder_ids)


class SqlAlchemySharesRepository(SharesRepositoryPort):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active_for_resource(
        self,
        resource_type: ResourceType,
        resource_id: uuid.UUID,
    ) -> ShareLink | None:
        return share_repository.get_active_share_for_resource(
            self.session,
            resource_type,
            resource_id,
        )

    def add_share_link(self, share_link: ShareLink) -> None:
        share_repository.add_share_link(self.session, share_link)

    def get_active_users_by_emails(self, emails: list[str]) -> list[User]:
        return share_repository.get_active_users_by_emails(self.session, emails)

    def get_by_token_hash(self, token_hash: str) -> ShareLink | None:
        return share_repository.get_share_by_token_hash(self.session, token_hash)

    def get_shared_file(self, file_id: uuid.UUID) -> File | None:
        return share_repository.get_shared_file(self.session, file_id)

    def get_shared_folder(self, folder_id: uuid.UUID) -> Folder | None:
        return share_repository.get_shared_folder(self.session, folder_id)


class SqlAlchemyUnitOfWork(UnitOfWorkPort):
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = SqlAlchemyUsersRepository(session)
        self.files = SqlAlchemyFilesRepository(session)
        self.folders = SqlAlchemyFoldersRepository(session)
        self.shares = SqlAlchemySharesRepository(session)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def refresh(self, instance: object) -> None:
        self.session.refresh(instance)

    def flush(self) -> None:
        self.session.flush()

    def add(self, instance: object) -> None:
        self.session.add(instance)

    def delete(self, instance: object) -> None:
        self.session.delete(instance)
