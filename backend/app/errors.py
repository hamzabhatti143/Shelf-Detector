from app.constants import (
    ERR_AUDIT_NOT_FOUND,
    ERR_BLURRY,
    ERR_IMAGE_NOT_FOUND,
    ERR_INVALID_IMAGE,
    ERR_INVALID_VIDEO,
    ERR_JOB_NOT_FOUND,
    ERR_NOT_IMAGE,
    ERR_NOT_VIDEO,
)


class AppError(Exception):
    status_code: int = 400
    default_message: str = "Request failed."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class InvalidImageError(AppError):
    status_code = 422
    default_message = ERR_INVALID_IMAGE


class UnsupportedMediaError(AppError):
    status_code = 415
    default_message = ERR_NOT_IMAGE


class PayloadTooLargeError(AppError):
    status_code = 413


class ImageTooBlurryError(AppError):
    status_code = 422
    default_message = ERR_BLURRY


class UnknownStoreError(AppError):
    status_code = 422


class AuditNotFoundError(AppError):
    status_code = 404
    default_message = ERR_AUDIT_NOT_FOUND


class ImageNotFoundError(AppError):
    status_code = 404
    default_message = ERR_IMAGE_NOT_FOUND


class UnsupportedVideoError(AppError):
    status_code = 415
    default_message = ERR_NOT_VIDEO


class InvalidVideoError(AppError):
    status_code = 422
    default_message = ERR_INVALID_VIDEO


class JobNotFoundError(AppError):
    status_code = 404
    default_message = ERR_JOB_NOT_FOUND