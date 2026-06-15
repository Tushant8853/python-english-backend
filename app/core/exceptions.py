"""Application-level errors mapped to HTTP responses."""


class AppError(Exception):
    """Operational error with an HTTP status code and safe client message."""

    def __init__(self, message: str, status_code: int, *, is_operational: bool = True) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.is_operational = is_operational
