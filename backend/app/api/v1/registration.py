"""Public registration: apply for a listing without an account.

The counterpart to the assisted-listing offer the site already makes. An
applicant fills the form, an administrator audits it, and credentials are
handed over afterwards — see app/services/registration.py for why the
application is stored as the listing itself.

Both routes answer the same message whatever happened, including when the
number already has an account. An endpoint that answered differently would be
a way to ask which numbers are registered.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.dependencies import AppSettings, ClientIp, DbSession
from app.core.i18n import translate
from app.schemas.registration import (
    BusinessRegistrationIn,
    RegistrationOut,
    TalentRegistrationIn,
)
from app.services.registration import RegistrationService

router = APIRouter(tags=["registration"])


@router.post(
    "/register/business",
    response_model=RegistrationOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def register_business(
    payload: BusinessRegistrationIn,
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
) -> RegistrationOut:
    """Apply to list a business. 202: received, not yet published."""
    RegistrationService(db, settings).register_business(payload, client_ip=client_ip)
    return RegistrationOut(message=translate("registration.received"))


@router.post(
    "/register/talent",
    response_model=RegistrationOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def register_talent(
    payload: TalentRegistrationIn,
    db: DbSession,
    settings: AppSettings,
    client_ip: ClientIp,
) -> RegistrationOut:
    """Apply to list a talent profile."""
    RegistrationService(db, settings).register_talent(payload, client_ip=client_ip)
    return RegistrationOut(message=translate("registration.received"))
