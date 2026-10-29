"""A job applicant's CV: checked like an ID scan, stored where nobody browses.

The bytes are validated by :class:`~app.services.verification.
VerificationDocumentService` (PDF, JPEG or PNG by their real magic number,
within the document size limit) before any row exists, so a bad file
refuses the application rather than leaving one with nothing attached.
"""

from __future__ import annotations

import logging
import uuid

from app.core.config import Settings
from app.services.verification import DOCUMENT_EXTENSIONS, VerificationDocumentService
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)

FOLDER = "job-cv"
#: The ID scan an employer sends with a job they offer.
EMPLOYER_ID_FOLDER = "job-employer-id"
#: Hold strangers' CVs and ID scans; the media mount refuses them
#: (``app.main.PRIVATE_MEDIA_FOLDERS``).
STORAGE_FOLDERS = frozenset({FOLDER, EMPLOYER_ID_FOLDER})


class JobCvService:
    def __init__(self, storage: StorageBackend, settings: Settings) -> None:
        self._storage = storage
        self._documents = VerificationDocumentService(storage, settings)

    def validate(self, data: bytes) -> str:
        """The content type the bytes really are, or the 413/415 refusal."""
        return self._documents.validate(data)

    def store(
        self, *, job_id: uuid.UUID, data: bytes, content_type: str, folder: str = FOLDER
    ) -> str:
        key = f"{folder}/{job_id}/{uuid.uuid4().hex}.{DOCUMENT_EXTENSIONS[content_type]}"
        self._storage.save(key=key, data=data, content_type=content_type)
        logger.info("Stored job application CV", extra={"storage_key": key})
        return key

    def read(self, key: str) -> bytes:
        return self._storage.read(key)

    def delete(self, key: str | None) -> None:
        if key:
            self._storage.delete(key)
