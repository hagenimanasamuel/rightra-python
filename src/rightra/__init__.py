"""Rightra server-side helpers for Python.

Public surface:

- Client for the Rightra API.
- mint_upload_token and verify_upload_token for the PHP upload helper.
- sign_s3_put and sign_r2_put for direct-to-bucket uploads.
- RightraError for every failure.

No framework imports. Django and Flask users import the same module.
"""

from __future__ import annotations

from .client import Client
from .errors import RightraError
from .storage import sign_r2_put, sign_s3_put
from .upload import DEFAULT_TTL as UPLOAD_TOKEN_DEFAULT_TTL
from .upload import mint_upload_token, verify_upload_token

__version__ = "0.1.0"
__all__ = [
    "Client",
    "RightraError",
    "UPLOAD_TOKEN_DEFAULT_TTL",
    "mint_upload_token",
    "verify_upload_token",
    "sign_s3_put",
    "sign_r2_put",
]