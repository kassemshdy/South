"""S3-compatible object storage.

Works against AWS S3, Cloudflare R2, Backblaze B2 and MinIO — anything speaking
the S3 API — by pointing S3_ENDPOINT_URL at the right host. boto3 is imported
lazily so the dependency is only needed when this backend is actually selected.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings
from app.storage.base import StoredFile

logger = logging.getLogger(__name__)


class S3Storage:
    name = "s3"

    def __init__(self, settings: Settings) -> None:
        if not settings.s3_bucket:
            raise RuntimeError("S3_BUCKET must be set when STORAGE_BACKEND=s3")

        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError as exc:  # pragma: no cover - depends on deployment
            raise RuntimeError(
                "STORAGE_BACKEND=s3 requires boto3. Install it with: pip install boto3"
            ) from exc

        self._client_error = ClientError
        self._bucket = settings.s3_bucket
        self._public_base = (settings.s3_public_base_url or "").rstrip("/")
        self._client: Any = boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )

    def save(self, *, key: str, data: bytes, content_type: str) -> StoredFile:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
        return StoredFile(
            key=key, url=self.url_for(key), size_bytes=len(data), content_type=content_type
        )

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception:  # pragma: no cover - network failure path
            logger.exception("Failed to delete object from S3", extra={"storage_key": key})

    def url_for(self, key: str) -> str:
        if self._public_base:
            return f"{self._public_base}/{key.lstrip('/')}"
        return f"https://{self._bucket}.s3.amazonaws.com/{key.lstrip('/')}"

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except self._client_error as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                return False
            raise

    def read(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()
