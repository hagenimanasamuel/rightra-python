"""Rightra API client.

Pure urllib. No requests. Every failure raises RightraError.
"""

from __future__ import annotations

import json
import re
import socket
from typing import Any, Dict, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

from .errors import RightraError

_CONTENT_ID_RE = re.compile(r"^RTR-[A-F0-9]{4}-[A-F0-9]{4}$")
_DEFAULT_BASE = "https://api.oliviuus.com/api/rightra"
_MAX_BODY = 2 * 1024 * 1024


class Client:
    """Client for the Rightra SDK API.

    Args:
        api_key: RIGHTRA_API_KEY. Must start with rk_live_ or rk_test_.
        base_url: API base. Defaults to production.
        timeout: Per-request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE,
        timeout: float = 30.0,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.startswith(("rk_live_", "rk_test_")):
            raise ValueError("api_key must start with rk_live_ or rk_test_.")
        if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://.")
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout must be a positive number.")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        stream_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            if len(data) > _MAX_BODY:
                raise ValueError("Request body exceeds the Rightra 2 MB limit.")

        req = urlrequest.Request(url=url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", "rightra-python/0.1.0")
        if data is not None:
            req.add_header("Content-Type", "application/json")

        try:
            with urlrequest.urlopen(req, timeout=self.timeout) as resp:
                if stream_to:
                    self._stream_to(resp, stream_to)
                    return {"success": True, "path": stream_to}
                raw = resp.read()
                return self._parse(raw, resp.status)
        except urlerror.HTTPError as exc:
            raw = b""
            try:
                raw = exc.read()
            except Exception:
                pass
            parsed = self._safe_json(raw)
            code = parsed.get("code") if isinstance(parsed, dict) else None
            message = (
                parsed.get("message")
                if isinstance(parsed, dict) and isinstance(parsed.get("message"), str)
                else "The Rightra request failed."
            )
            raise RightraError(message, status=exc.code, code=code, body=parsed) from None
        except (urlerror.URLError, socket.timeout, TimeoutError) as exc:
            reason = getattr(exc, "reason", exc)
            raise RightraError(
                "Could not reach the Rightra service.",
                status=0,
                code="NETWORK_ERROR",
                body=str(reason),
            ) from None

    @staticmethod
    def _parse(raw: bytes, status: int) -> Dict[str, Any]:
        if not raw:
            return {"success": True, "status": status}
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RightraError(
                "The Rightra service returned an invalid response.",
                status=status,
                code="INVALID_RESPONSE",
            ) from None
        if not isinstance(parsed, dict):
            raise RightraError(
                "The Rightra service returned an unexpected response.",
                status=status,
                code="INVALID_RESPONSE",
            )
        return parsed

    @staticmethod
    def _safe_json(raw: bytes) -> Any:
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None

    @staticmethod
    def _stream_to(resp, dest_path: str) -> None:
        with open(dest_path, "wb") as handle:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                handle.write(chunk)

    def register_content(
        self,
        *,
        title: str,
        type: str,
        description: Optional[str] = None,
        creator_name: Optional[str] = None,
        rights_holder_name: Optional[str] = None,
        storage_reference: Optional[Dict[str, Any]] = None,
        encryption: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"title": title, "type": type}
        if description is not None:
            body["description"] = description
        if creator_name is not None:
            body["creator_name"] = creator_name
        if rights_holder_name is not None:
            body["rights_holder_name"] = rights_holder_name
        if storage_reference is not None:
            body["storage_reference"] = storage_reference
        if encryption is not None:
            body["encryption"] = encryption
        return self._request("POST", "/sdk/content", body=body)

    def get_content(self, content_id: str) -> Dict[str, Any]:
        self._require_content_id(content_id)
        return self._request("GET", f"/sdk/content/{content_id}")

    def set_encryption_key(
        self,
        content_id: str,
        *,
        key_material: str,
        key_algorithm: str = "AES-256-GCM",
        segment_manifest: Optional[Any] = None,
    ) -> Dict[str, Any]:
        self._require_content_id(content_id)
        body: Dict[str, Any] = {
            "key_material": key_material,
            "key_algorithm": key_algorithm,
        }
        if segment_manifest is not None:
            body["segment_manifest"] = segment_manifest
        return self._request("POST", f"/sdk/content/{content_id}/key", body=body)

    def set_manifest(
        self,
        content_id: str,
        *,
        manifest_url: str,
        storage_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._require_content_id(content_id)
        body: Dict[str, Any] = {"manifest_url": manifest_url}
        if storage_details is not None:
            body["storage_reference"] = storage_details
        return self._request("POST", f"/sdk/content/{content_id}/manifest", body=body)

    def queue_fingerprint(
        self,
        content_id: str,
        *,
        reference_material: str,
        reference_type: str = "audio_sample",
    ) -> Dict[str, Any]:
        self._require_content_id(content_id)
        body = {
            "reference_material": reference_material,
            "reference_type": reference_type,
        }
        return self._request("POST", f"/sdk/content/{content_id}/fingerprint", body=body)

    def create_playback_session(
        self,
        content_id: str,
        *,
        viewer_id: str,
        viewer_label: Optional[str] = None,
        territory: Optional[str] = None,
        client_public_key: Optional[str] = None,
        device: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._require_content_id(content_id)
        if not isinstance(viewer_id, str) or not viewer_id.strip():
            raise ValueError("viewer_id is required. Rightra fails closed without it.")
        viewer: Dict[str, Any] = {"id": viewer_id.strip()}
        if viewer_label:
            viewer["label"] = viewer_label
        body: Dict[str, Any] = {"content_id": content_id, "viewer": viewer}
        if territory:
            body["requested_territory"] = territory.upper()[:2]
        if client_public_key:
            body["client_public_key"] = client_public_key
        if device:
            body["device"] = device
        return self._request("POST", "/sdk/playback-session", body=body)

    def playback_event(
        self,
        *,
        session_id: str,
        event: str,
        seconds_watched: int = 0,
    ) -> Dict[str, Any]:
        if not session_id:
            raise ValueError("session_id is required.")
        body = {
            "session_id": session_id,
            "event": event,
            "seconds_watched": int(seconds_watched),
        }
        return self._request("POST", "/sdk/playback-event", body=body)

    def record_download_attempt(
        self,
        *,
        session_id: str,
        attempt_type: str = "unknown",
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not session_id:
            raise ValueError("session_id is required.")
        body: Dict[str, Any] = {"session_id": session_id, "attempt_type": attempt_type}
        if details is not None:
            body["details"] = details
        return self._request("POST", "/sdk/download-attempt", body=body)

    def request_download(self, session_id: str) -> Dict[str, Any]:
        if not session_id:
            raise ValueError("session_id is required.")
        return self._request("POST", "/sdk/download-request", body={"session_id": session_id})

    def download_status(self, job_id: str) -> Dict[str, Any]:
        if not job_id:
            raise ValueError("job_id is required.")
        return self._request("GET", f"/sdk/download-status/{job_id}")

    def download_file(self, job_id: str, dest_path: str) -> Dict[str, Any]:
        if not job_id:
            raise ValueError("job_id is required.")
        if not dest_path:
            raise ValueError("dest_path is required.")
        return self._request("GET", f"/sdk/download-file/{job_id}", stream_to=dest_path)

    @staticmethod
    def _require_content_id(content_id: str) -> None:
        if not isinstance(content_id, str) or not _CONTENT_ID_RE.match(content_id):
            raise ValueError("content_id must look like RTR-XXXX-XXXX (uppercase hex).")