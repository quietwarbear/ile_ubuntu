"""Cloudflare Stream for uploaded lesson video (items I4 phase 2 and I5).

Why: lesson video used to be a single MP4 behind a short presigned S3 link.
Long recordings (2+ hours) stutter on phones, and there were no captions.
Stream transcodes to HLS, plays adaptively, and can generate captions.

Everything here is behind configuration. While any required variable is
unset, ``enabled()`` is False and the app keeps using the S3 / local video
path exactly as before; nothing in this module is called.

    CF_ACCOUNT_ID               Cloudflare account id (required)
    CF_STREAM_API_TOKEN         API token with Stream edit permission (required)
    CF_STREAM_CUSTOMER_CODE     the <CODE> in customer-<CODE>.cloudflarestream.com (required)
    CF_STREAM_SIGNING_KEY_ID    id returned by POST /stream/keys (required)
    CF_STREAM_SIGNING_KEY_PEM   the "pem" value from that call, as returned (base64) (required)
    CF_STREAM_AUTO_CAPTIONS     language for automatic captions once a video is
                                ready (default "en"; empty turns it off)
    CF_STREAM_MAX_DURATION      longest accepted upload, seconds (default 21600 = 6 h)
    CF_STREAM_TOKEN_TTL         base playback-token lifetime, seconds (default 600)

Playback is never public: every video is created with requireSignedURLs, and
viewers get a token signed here, after the same access rule as every other
file (file_access.can_access). Each token is bound to one video. Cloudflare
does not document whether an expired token stops a video that is already
playing, so a token lasts the base TTL plus the video's own length (capped at
MAX_PLAYBACK_TTL): long enough to watch once, then useless.
"""

import base64
import logging
import os
import re
import time
from typing import Optional

import httpx
import jwt

log = logging.getLogger(__name__)

API_BASE = "https://api.cloudflare.com/client/v4"
MAX_PLAYBACK_TTL = 6 * 3600
CAPTION_LANGUAGES = ("en", "es", "fr", "pt", "de", "it", "nl", "pl", "cs", "ru", "ja", "ko")
LANG_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$")
MAX_VTT_BYTES = 10 * 1024 * 1024


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def account_id() -> str:
    return _env("CF_ACCOUNT_ID")


def _token() -> str:
    return _env("CF_STREAM_API_TOKEN")


def customer_code() -> str:
    return _env("CF_STREAM_CUSTOMER_CODE")


def _key_id() -> str:
    return _env("CF_STREAM_SIGNING_KEY_ID")


def _key_pem() -> str:
    """Cloudflare hands the PEM over base64-encoded; accept it either way."""
    raw = _env("CF_STREAM_SIGNING_KEY_PEM")
    if not raw or "BEGIN" in raw:
        return raw.replace("\\n", "\n")
    try:
        return base64.b64decode(raw).decode()
    except Exception:
        return ""


def enabled() -> bool:
    return all((account_id(), _token(), customer_code(), _key_id(), _key_pem()))


def auto_caption_language() -> str:
    lang = _env("CF_STREAM_AUTO_CAPTIONS", "en")
    return lang if lang in CAPTION_LANGUAGES else ""


def max_duration() -> int:
    try:
        return max(60, int(_env("CF_STREAM_MAX_DURATION", "21600")))
    except ValueError:
        return 21600


def base_token_ttl() -> int:
    try:
        return max(60, min(int(_env("CF_STREAM_TOKEN_TTL", "600")), MAX_PLAYBACK_TTL))
    except ValueError:
        return 600


class StreamError(Exception):
    pass


# --- HTTP (one seam, replaced in tests) -------------------------------------

def _request(method: str, path: str, **kwargs) -> httpx.Response:
    headers = {"Authorization": f"Bearer {_token()}", **kwargs.pop("headers", {})}
    url = f"{API_BASE}/accounts/{account_id()}/stream{path}"
    return httpx.request(method, url, headers=headers, timeout=30, **kwargs)


def _result(resp: httpx.Response):
    try:
        body = resp.json()
    except ValueError:
        body = {}
    if resp.status_code >= 400 or body.get("success") is False:
        errors = body.get("errors") or [{"message": resp.text[:200]}]
        raise StreamError(f"Cloudflare Stream {resp.status_code}: {errors[0].get('message', '')}")
    return body.get("result")


# --- uploads ----------------------------------------------------------------

def _tus_metadata(pairs: dict) -> str:
    out = []
    for key, value in pairs.items():
        if value is None:
            out.append(key)                       # flag, e.g. requiresignedurls
        else:
            out.append(f"{key} {base64.b64encode(str(value).encode()).decode()}")
    return ",".join(out)


def create_upload(size: int, name: str) -> dict:
    """A one-time resumable (tus) upload URL the browser sends the file to
    directly, so video never passes through this server. Works for any size
    (the simple direct-upload API stops at 200 MB)."""
    resp = _request(
        "POST", "?direct_user=true",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": str(int(size)),
            "Upload-Metadata": _tus_metadata({
                "maxDurationSeconds": max_duration(),
                "requiresignedurls": None,
                "name": (name or "lesson video")[:200],
            }),
        },
    )
    if resp.status_code >= 400:
        _result(resp)
    upload_url = resp.headers.get("location")
    uid = resp.headers.get("stream-media-id")
    if not upload_url or not uid:
        raise StreamError("Cloudflare Stream did not return an upload URL")
    return {"upload_url": upload_url, "uid": uid}


def copy_from_url(url: str, name: str) -> str:
    """Have Stream fetch a video from a URL (used by the migration script)."""
    result = _result(_request("POST", "/copy", json={
        "url": url, "meta": {"name": name}, "requireSignedURLs": True,
    }))
    return result["uid"]


def video(uid: str) -> dict:
    return _result(_request("GET", f"/{uid}")) or {}


def require_signed(uid: str) -> None:
    _result(_request("POST", f"/{uid}", json={"uid": uid, "requireSignedURLs": True}))


def delete_video(uid: str) -> None:
    resp = _request("DELETE", f"/{uid}")
    if resp.status_code not in (200, 204, 404):
        _result(resp)


def summarize(details: dict) -> dict:
    """The parts of a Stream video record the app keeps."""
    status = details.get("status") or {}
    ready = bool(details.get("readyToStream"))
    state = "ready" if ready else (status.get("state") or "processing")
    out = {"stream_state": state, "stream_ready": ready}
    if details.get("duration") and details["duration"] > 0:
        out["duration_seconds"] = float(details["duration"])
    if status.get("errorReasonText"):
        out["stream_error"] = status["errorReasonText"]
    out["stream_signed"] = bool(details.get("requireSignedURLs"))
    return out


# --- captions (I5) ----------------------------------------------------------

def check_language(lang: str) -> str:
    if not LANG_RE.match(lang or ""):
        raise ValueError("Language must be a code such as en or es")
    return lang


def list_captions(uid: str) -> list:
    return _result(_request("GET", f"/{uid}/captions")) or []


def generate_captions(uid: str, lang: str) -> dict:
    if lang not in CAPTION_LANGUAGES:
        raise ValueError(f"Automatic captions support: {', '.join(CAPTION_LANGUAGES)}")
    return _result(_request("POST", f"/{uid}/captions/{lang}/generate")) or {}


def get_vtt(uid: str, lang: str) -> str:
    resp = _request("GET", f"/{uid}/captions/{check_language(lang)}/vtt")
    if resp.status_code >= 400:
        _result(resp)
    return resp.text


def valid_vtt(text: str) -> str:
    if not isinstance(text, str) or not text.lstrip("﻿").startswith("WEBVTT"):
        raise ValueError("Captions must be a WebVTT file (it starts with WEBVTT)")
    if len(text.encode()) > MAX_VTT_BYTES:
        raise ValueError("Caption file is larger than 10 MB")
    return text


def put_vtt(uid: str, lang: str, text: str) -> dict:
    files = {"file": (f"{lang}.vtt", valid_vtt(text).encode(), "text/vtt")}
    return _result(_request("PUT", f"/{uid}/captions/{check_language(lang)}", files=files)) or {}


def delete_captions(uid: str, lang: str) -> None:
    resp = _request("DELETE", f"/{uid}/captions/{check_language(lang)}")
    if resp.status_code not in (200, 204, 404):
        _result(resp)


# --- playback ---------------------------------------------------------------

def playback_ttl(duration_seconds: Optional[float]) -> int:
    extra = int(duration_seconds or 0)
    return min(base_token_ttl() + extra, MAX_PLAYBACK_TTL)


def sign(uid: str, ttl: int, now: Optional[float] = None) -> dict:
    now = int(now or time.time())
    exp = now + int(ttl)
    token = jwt.encode(
        {"sub": uid, "kid": _key_id(), "nbf": now - 30, "exp": exp},
        _key_pem(), algorithm="RS256", headers={"kid": _key_id()},
    )
    return {"token": token, "expires_at": exp}


def playback(uid: str, duration_seconds: Optional[float] = None) -> dict:
    """Signed player and HLS URLs for one viewer. Captions are not turned on
    by default (no defaultTextTrack); the player's CC button toggles them."""
    signed = sign(uid, playback_ttl(duration_seconds))
    host = f"https://customer-{customer_code()}.cloudflarestream.com/{signed['token']}"
    return {
        "iframe_url": f"{host}/iframe?preload=metadata",
        "hls_url": f"{host}/manifest/video.m3u8",
        "expires_at": signed["expires_at"],
    }
