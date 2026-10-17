"""Exception types for the Rightra Python package."""

from __future__ import annotations

from typing import Any, Optional


class RightraError(Exception):
    """Raised for every Rightra failure.

    Attributes:
        status: HTTP status code. 0 for network or transport failures.
        code: Rightra error code when the server provided one, else None.
        message: A sentence safe to show a user.
        body: Parsed response body when available, else None.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int = 0,
        code: Optional[str] = None,
        body: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.body = body

    def __repr__(self) -> str:
        return f"RightraError(status={self.status!r}, code={self.code!r}, message={self.message!r})"