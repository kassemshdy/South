"""Public registration: apply for a listing without an account.

The counterpart to the assisted-listing offer the site already makes. An
applicant fills the form, an administrator audits it, and credentials are
handed over afterwards — see app/services/registration.py for why the
application is stored as the listing itself.

Both routes answer the same message whatever happened, including when the
number already has an account. An endpoint that answered differently would be
a way to ask which numbers are registered.

## Why these take multipart rather than JSON

An application carries the applicant's ID scan, and the reviewer is deciding
whether this is a real person from the South — asking for the document after
the audit puts the decision before the evidence. There is no account to upload
it to yet, so the file arrives with the application.

That does *not* make an anonymous upload endpoint. The file is only ever
accepted as part of an application that succeeds: it passes the same captcha
and the same rate limits as the rest of the form, it is refused before
anything is created if it is too large or is not a document, and it is written
against the account the application creates, in that application's
transaction. There is nothing here to point a script at on its own.

The application itself stays JSON, in one form field, rather than being
flattened into form fields — it is a nested shape, and flattening it would
mean a second definition of every field and a second place for the two to
drift. A pydantic failure is re-raised as the validation error FastAPI would
have produced from a JSON body, so the per-field sentences the forms show
are unchanged.
"""

from __future__ import annotations

import json
from typing import Annotated, TypeVar

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

from app.core.dependencies import AppSettings, ClientIp, DbSession
from app.core.i18n import translate
from app.schemas.registration import (
    BusinessRegistrationIn,
    RegistrationOut,
    TalentRegistrationIn,
)
from app.services.registration import ApplicantDocument, RegistrationService

router = APIRouter(tags=["registration"])

ModelT = TypeVar("ModelT", bound=BaseModel)

#: The form field the JSON application arrives in.
ApplicationField = Annotated[
    str, Form(description="The application itself, as a JSON object")
]
#: The applicant's ID scan. Optional at the API — whether a form insists on it
#: is the form's business, and an administrator can still ask for one later.
DocumentField = Annotated[
    UploadFile | None, File(description="A national ID, passport, or similar document")
]


def _parse(model: type[ModelT], raw: str) -> ModelT:
    """The application, or the 422 a JSON body would have produced.

    ``loc`` is prefixed with ``body`` so it matches what FastAPI reports for a
    JSON request: the error renderer drops the first element, so without it
    every field would lose the name of the block it sits in.
    """
    try:
        return model.model_validate_json(raw)
    except ValidationError as exc:
        raise RequestValidationError(
            [{**error, "loc": ("body", *error["loc"])} for error in exc.errors()]
        ) from exc
    except json.JSONDecodeError as exc:
        raise RequestValidationError(
            [{"type": "json_invalid", "loc": ("body",), "msg": "Invalid JSON", "input": raw}]
        ) from exc


def _document(file: UploadFile | None) -> ApplicantDocument | None:
    if file is None:
        return None
    data = file.file.read()
    if not data:
        return None
    return ApplicantDocument(data=data, original_filename=file.filename)


@router.post(
    "/register/business",
    response_model=RegistrationOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def register_business(
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
    application: ApplicationField,
    document: DocumentField = None,
) -> RegistrationOut:
    """Apply to list a business. 202: received, not yet published."""
    RegistrationService(db, settings).register_business(
        _parse(BusinessRegistrationIn, application),
        client_ip=client_ip,
        document=_document(document),
    )
    return RegistrationOut(message=translate("registration.received"))


@router.post(
    "/register/talent",
    response_model=RegistrationOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def register_talent(
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
    application: ApplicationField,
    document: DocumentField = None,
) -> RegistrationOut:
    """Apply to list a talent profile."""
    RegistrationService(db, settings).register_talent(
        _parse(TalentRegistrationIn, application),
        client_ip=client_ip,
        document=_document(document),
    )
    return RegistrationOut(message=translate("registration.received"))
