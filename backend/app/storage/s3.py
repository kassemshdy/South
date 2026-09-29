"""S3-compatible object storage.

Works against AWS S3, Cloudflare R2, Backblaze B2, MinIO and Railway buckets --
anything speaking the S3 API -- by pointing S3_ENDPOINT_URL at the right host.
boto3 is imported lazily so the dependency is only needed when this backend is
actually selected.

**With no S3_PUBLIC_BASE_URL the bucket stays private** and a file's URL is the
site's own ``/media/<key>``, which the API answers by reading the object (see
``_mount_media`` in ``app.main``). That is the mode for a private bucket such
as Railway's: the URLs already stored in the database keep working, and the
private folders (ID scans, CVs, official papers, ticket attachments) stay
refused on ``/media`` exactly as they are on local disk -- a public bucket URL
would hand every one of them to anyone who learned its name.
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
            from botocore.config import Config
            from botocore.exceptions import ClientError
        except ImportError as exc:  # pragma: no cover - depends on deployment
            raise RuntimeError(
                "STORAGE_BACKEND=s3 requires boto3. Install it with: pip install boto3"
            ) from exc

        self._client_error = ClientError
        self._bucket = settings.s3_bucket
        self._public_base = (settings.s3_public_base_url or "").rstrip("/")
        self._prefix = settings.storage_public_prefix.rstrip("/")
        self._client: Any = boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            config=Config(s3={"addressing_style": settings.s3_addressing_style}),
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
        # Private bucket: served through the API's own /media route.
        return f"{self._prefix}/{key.lstrip('/')}"

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except self._client_error as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                return False
            raise

    def read(self, key: str) -> bytes:
        """The object's bytes; ``FileNotFoundError`` when there is none, the
        same as local disk, so callers need not know which backend they have."""
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except self._client_error as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                raise FileNotFoundError(key) from exc
            raise
        body: bytes = response["Body"].read()
        return body

    def keys(self) -> set[str]:
        """Every key in the bucket, in one paginated listing."""
        found: set[str] = set()
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket):
            for item in page.get("Contents", []):
                found.add(item["Key"])
        return found
