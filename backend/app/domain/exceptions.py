from __future__ import annotations


class AppError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ValidationError(AppError):
    pass


class AuthenticationError(AppError):
    pass


class AuthorizationError(AppError):
    pass


class NotFoundError(AppError):
    pass


class ConflictError(AppError):
    pass


class GoneError(AppError):
    pass
