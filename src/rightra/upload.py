"""Upload token helpers.

The token format matches the PHP helper (``rightra-upload.php``) and the
Laravel package (``UploadToken::mint``):

    X-Rightra-Token: <expiry>.<hmac>
    hmac = HMAC-SHA256("<contentId>|<expiry>", RIGHTRA_UPLOAD_SECRET)

``expiry`` is a unix timestamp. The token is bound to one content id and is
valid until that timestamp. The master secret never reaches the browser.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import time
from typing import Optional

_CONTENT_ID_RE = re.compile(r"^RTR-[A-F0-9]{4}-[A-F0-9]{4}$")
_TOKEN_RE = re.compile(r"^(\d{9,11})\.([a-f0-9]{64})$")

DEFAULT_TTL = 900
_MAX_TTL = 86400  # 24 hours. Anything longer is a bug, not a feature.


def _require_content_id(content_id: str) -> str:
    if not isinstance(content_id, str) or not _CONTENT_ID_RE.match(content_id):
        raise ValueError("content_id must look like RTR-XXXX-XXXX (uppercase hex).")
    return content_id


def _require_secret(secret: str) -> bytes:
    if not isinstance(secret, str) or not secret:
        raise ValueError("secret is required to mint or verify upload tokens.")
    return secret.encode("utf-8")


def _sign(content_id: str, expiry: int, secret: bytes) -> str:
    payload = f"{content_id}|{expiry}".encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def mint_upload_token(
    content_id: str,
    secret: str,
    *,
    ttl: int = DEFAULT_TTL,
    now: Optional[int] = None,
) -> str:
    """Return ``"<expiry>.<hmac>"`` for the given content id.

    Args:
        content_id: A Rightra content id, ``RTR-XXXX-XXXX``.
        secret: ``RIGHTRA_UPLOAD_SECRET``.
        ttl: Seconds the token stays valid. Defaults to 900.
        now: Override the current unix time. Useful in tests.

    Raises:
        ValueError: If inputs are invalid.
    """
    _require_content_id(content_id)
    secret_b = _require_secret(secret)

    if not isinstance(ttl, int) or isinstance(ttl, bool):
        raise ValueError("ttl must be an integer.")
    if ttl <= 0 or ttl > _MAX_TTL:
        raise ValueError(f"ttl must be between 1 and {_MAX_TTL} seconds.")

    current = int(now if now is not None else time.time())
    expiry = current + ttl
    signature = _sign(content_id, expiry, secret_b)
    return f"{expiry}.{signature}"


def verify_upload_token(
    token: str,
    content_id: str,
    secret: str,
    *,
    now: Optional[int] = None,
) -> bool:
    """Return ``True`` if the token is well formed, unexpired, and signed correctly.

    Uses a constant-time comparison so timing does not leak the expected signature.
    """
    if not isinstance(token, str):
        return False
    try:
        _require_content_id(content_id)
        secret_b = _require_secret(secret)
    except ValueError:
        return False

    match = _TOKEN_RE.match(token)
    if not match:
        return False

    expiry = int(match.group(1))
    provided = match.group(2)

    current = int(now if now is not None else time.time())
    if expiry < current:
        return False

    expected = _sign(content_id, expiry, secret_b)
    return hmac.compare_digest(expected, provided)