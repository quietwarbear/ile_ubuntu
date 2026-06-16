"""Object storage (S3 / Cloudflare R2 / any S3-compatible) for course file uploads.

Why this exists: uploads used to be written to a relative ``uploads/`` directory, which on
Railway is ephemeral container disk — every redeploy wiped newly uploaded files. This module
stores files in a durable bucket instead. boto3 is already a dependency.

Config is via environment variables so the same code works for AWS S3, Cloudflare R2,
Backblaze B2, MinIO, etc.:

    S3_BUCKET             bucket name (required to enable S3)
    S3_ACCESS_KEY_ID      access key (falls back to AWS_ACCESS_KEY_ID)
    S3_SECRET_ACCESS_KEY  secret key (falls back to AWS_SECRET_ACCESS_KEY)
    S3_ENDPOINT_URL       custom endpoint — set for R2/B2/MinIO; omit for AWS S3
    S3_REGION             region (default us-east-1; R2 uses "auto")
    S3_PREFIX             key prefix inside the bucket (default "uploads")
    S3_PRESIGN_TTL        presigned-URL lifetime in seconds (default 3600)

If S3_BUCKET / creds are not set, ``s3_enabled()`` returns False and the file routes fall
back to local disk (fine for local dev; NOT durable on Railway).
"""

import os

_BUCKET = os.environ.get("S3_BUCKET", "").strip()
_ENDPOINT = (os.environ.get("S3_ENDPOINT_URL", "").strip() or None)
_REGION = os.environ.get("S3_REGION", "us-east-1").strip() or "us-east-1"
_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY_ID") or os.environ.get("AWS_ACCESS_KEY_ID", "")
_SECRET_KEY = os.environ.get("S3_SECRET_ACCESS_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY", "")
_PREFIX = os.environ.get("S3_PREFIX", "uploads").strip().strip("/")
_PRESIGN_TTL = int(os.environ.get("S3_PRESIGN_TTL", "3600"))

_client = None


def s3_enabled() -> bool:
    """True when a bucket and credentials are configured."""
    return bool(_BUCKET and _ACCESS_KEY and _SECRET_KEY)


def bucket() -> str:
    return _BUCKET


def _get_client():
    global _client
    if _client is None:
        import boto3  # imported lazily so the app boots even if S3 isn't configured
        _client = boto3.client(
            "s3",
            endpoint_url=_ENDPOINT,
            region_name=_REGION,
            aws_access_key_id=_ACCESS_KEY,
            aws_secret_access_key=_SECRET_KEY,
        )
    return _client


def build_key(filename: str) -> str:
    """Namespaced object key inside the bucket, e.g. uploads/<uuid>.pdf."""
    return f"{_PREFIX}/{filename}" if _PREFIX else filename


def upload_fileobj(fileobj, key: str, content_type: str) -> None:
    """Stream a file-like object to the bucket (no full read into memory)."""
    extra = {"ContentType": content_type} if content_type else {}
    _get_client().upload_fileobj(fileobj, _BUCKET, key, ExtraArgs=extra)


def presigned_get(key: str, filename: str, content_type: str, inline: bool = True) -> str:
    """A short-lived URL to GET the object. Forces the right content-type and
    inline-vs-attachment disposition so PDFs/images render in an <iframe>/<img>
    while documents download."""
    disposition = "inline" if inline else "attachment"
    safe_name = (filename or "file").replace('"', "")
    params = {
        "Bucket": _BUCKET,
        "Key": key,
        "ResponseContentDisposition": f'{disposition}; filename="{safe_name}"',
    }
    if content_type:
        params["ResponseContentType"] = content_type
    return _get_client().generate_presigned_url("get_object", Params=params, ExpiresIn=_PRESIGN_TTL)


def delete_object(key: str) -> None:
    """Best-effort delete; never raises so a Mongo cleanup can still proceed."""
    try:
        _get_client().delete_object(Bucket=_BUCKET, Key=key)
    except Exception:
        pass
