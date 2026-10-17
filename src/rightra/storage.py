"""Presigned PUT URL helpers for S3 and Cloudflare R2.

Pure Python. No boto3, no botocore, no aws-sdk. Signs with SigV4 using
hmac and hashlib from the standard library.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Dict, Optional
from urllib.parse import quote, urlencode

_ALGO = "AWS4-HMAC-SHA256"
_SERVICE = "s3"
_MAX_EXPIRES = 604800


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_expires(expires: int) -> None:
    if not isinstance(expires, int) or isinstance(expires, bool):
        raise ValueError("expires must be an integer number of seconds.")
    if expires <= 0 or expires > _MAX_EXPIRES:
        raise ValueError(f"expires must be between 1 and {_MAX_EXPIRES} seconds.")


def _encode_key(key: str) -> str:
    return "/".join(quote(segment, safe="-_.~") for segment in key.split("/"))


def _signing_key(secret_key: str, date_stamp: str, region: str) -> bytes:
    k_date = _hmac(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, _SERVICE)
    return _hmac(k_service, "aws4_request")


def _build_presigned_url(
    *,
    scheme: str,
    host: str,
    bucket: str,
    key: str,
    access_key: str,
    secret_key: str,
    region: str,
    expires: int,
    content_type: Optional[str],
    now: Optional[datetime],
) -> str:
    _validate_expires(expires)
    if not access_key or not secret_key:
        raise ValueError("access_key and secret_key are required.")
    if not bucket or not key:
        raise ValueError("bucket and key are required.")

    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    amz_date = moment.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = moment.strftime("%Y%m%d")

    canonical_uri = "/" + _encode_key(key)
    canonical_headers = f"host:{host}\n"
    signed_headers = "host"

    query: Dict[str, str] = {
        "X-Amz-Algorithm": _ALGO,
        "X-Amz-Credential": f"{access_key}/{date_stamp}/{region}/{_SERVICE}/aws4_request",
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(expires),
        "X-Amz-SignedHeaders": signed_headers,
    }
    if content_type:
        query["response-content-type"] = content_type

    canonical_query = urlencode(sorted(query.items()), quote_via=quote, safe="-_.~")

    canonical_request = "\n".join(
        [
            "PUT",
            canonical_uri,
            canonical_query,
            canonical_headers,
            signed_headers,
            "UNSIGNED-PAYLOAD",
        ]
    )

    credential_scope = f"{date_stamp}/{region}/{_SERVICE}/aws4_request"
    string_to_sign = "\n".join(
        [
            _ALGO,
            amz_date,
            credential_scope,
            _sha256_hex(canonical_request.encode("utf-8")),
        ]
    )

    key_b = _signing_key(secret_key, date_stamp, region)
    signature = hmac.new(key_b, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    final_query = canonical_query + "&X-Amz-Signature=" + signature
    return f"{scheme}://{host}{canonical_uri}?{final_query}"


def sign_s3_put(
    *,
    access_key: str,
    secret_key: str,
    bucket: str,
    key: str,
    region: str = "us-east-1",
    expires: int = 900,
    content_type: Optional[str] = None,
    now: Optional[datetime] = None,
) -> str:
    """Return a presigned S3 PUT URL."""
    host = f"{bucket}.s3.{region}.amazonaws.com"
    return _build_presigned_url(
        scheme="https",
        host=host,
        bucket=bucket,
        key=key,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        expires=expires,
        content_type=content_type,
        now=now,
    )


def sign_r2_put(
    *,
    account_id: str,
    access_key: str,
    secret_key: str,
    bucket: str,
    key: str,
    expires: int = 900,
    content_type: Optional[str] = None,
    now: Optional[datetime] = None,
) -> str:
    """Return a presigned Cloudflare R2 PUT URL."""
    if not account_id:
        raise ValueError("account_id is required for R2.")
    host = f"{account_id}.r2.cloudflarestorage.com"
    return _build_presigned_url(
        scheme="https",
        host=host,
        bucket=bucket,
        key=f"{bucket}/{key}",
        access_key=access_key,
        secret_key=secret_key,
        region="auto",
        expires=expires,
        content_type=content_type,
        now=now,
    )