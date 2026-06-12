"""Business exceptions raised by services, mapped to HTTP responses in main.py.

Services stay HTTP-agnostic: they raise these instead of HTTPException.
"""


class AppError(Exception):
    """Base business error. `message` is safe to expose to the client (French)."""

    status_code = 500

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class InvalidStateError(AppError):
    status_code = 400


class LLMUnavailableError(AppError):
    """Raised when the LLM provider is down after retries."""

    status_code = 503


class EmbeddingUnavailableError(AppError):
    """Raised when the embedding provider is down or not configured."""

    status_code = 503
