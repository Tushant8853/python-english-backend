"""HTTP status codes and user-facing messages."""

from typing import Final

HTTP_OK: Final[int] = 200
HTTP_BAD_REQUEST: Final[int] = 400
HTTP_UNAUTHORIZED: Final[int] = 401
HTTP_NOT_FOUND: Final[int] = 404
HTTP_INTERNAL_SERVER_ERROR: Final[int] = 500
HTTP_SERVICE_UNAVAILABLE: Final[int] = 503

ONBOARDING_PROFILE_OPTIONS: Final[frozenset[str]] = frozenset(
    {
        "Working Professional",
        "Parent (Teaching Your Child)",
        "Job Seeker",
        "Student",
        "Beginner (Just Starting Out)",
    }
)

MESSAGES: Final[dict[str, dict[str, str]]] = {
    "HEALTH": {
        "SUCCESS": "English Guru Backend is running",
    },
    "ERRORS": {
        "NOT_FOUND": "Resource not found",
        "INTERNAL": "An unexpected error occurred",
    },
}
