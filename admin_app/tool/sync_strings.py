"""Write the admin app's ARB catalogs from the web frontend's catalogs.

The app introduces no copy of its own: every string it shows is one the
owners already chose for the web admin, copied here by key. Change the
wording in ``frontend/src/i18n/locales/{ar,en}.json`` and run this again;
``backend/tests/test_i18n.py`` fails when the two drift apart.

    python3 admin_app/tool/sync_strings.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
FRONTEND_LOCALES = REPO_ROOT / "frontend" / "src" / "i18n" / "locales"
ARB_DIR = APP_ROOT / "lib" / "l10n"

#: The web catalog keys the app uses. Add a key here, run the script, and
#: it is available as ``AppLocalizations.of(context).<arbKey>``.
KEYS = [
    "admin.approve",
    "admin.reject",
    "admin.reactivate",
    "admin.suspend",
    "admin.rejectReasonLabel",
    "admin.rejectReasonPlaceholder",
    "admin.rejectionReasonTitle",
    "admin.statusUpdated",
    "admin.navDashboard",
    "admin.navBusinesses",
    "admin.navTalent",
    "admin.navFeedback",
    "admin.reviewRequests",
    "admin.queueEmpty",
    "admin.queueEmptyDescription",
    "admin.listEmptyTitle",
    "admin.listEmptyDescription",
    "admin.talentListEmptyTitle",
    "admin.searchPlaceholder",
    "admin.talentSearchPlaceholder",
    "admin.filterAll",
    "admin.filterPending",
    "admin.filterApproved",
    "admin.filterRejected",
    "admin.filterSuspended",
    "admin.filterDrafts",
    "admin.ownerTitle",
    "admin.ownerName",
    "admin.ownerAccount",
    "admin.ownerPersonalPhone",
    "admin.submittedAt",
    "admin.approvedByStaff",
    "admin.statTotal",
    "admin.statApproved",
    "admin.statRejected",
    "admin.statSuspended",
    "admin.statDrafts",
    "admin.statUsers",
    "admin.statAdmins",
    "admin.statItems",
    "admin.pendingLabel",
    "admin.pendingTalentLabel",
    "admin.pendingTestimonialsLabel",
    "adminShops.call",
    "status.DRAFT",
    "status.PENDING_REVIEW",
    "status.APPROVED",
    "status.REJECTED",
    "status.SUSPENDED",
    "feedback.status.BACKLOG",
    "feedback.status.TODO",
    "feedback.status.IN_PROGRESS",
    "feedback.status.NEEDS_FEEDBACK",
    "feedback.status.NEEDS_APPROVAL",
    "feedback.status.APPROVED",
    "feedback.status.DONE",
    "feedback.priority.LOW",
    "feedback.priority.MEDIUM",
    "feedback.priority.HIGH",
    "feedback.priority.URGENT",
    "feedback.priorityLabel",
    "feedback.assigneeLabel",
    "feedback.unassigned",
    "feedback.descriptionLabel",
    "feedback.commentsLabel",
    "feedback.noComments",
    "feedback.addCommentLabel",
    "feedback.addCommentPlaceholder",
    "feedback.addCommentAction",
    "feedback.moveFailed",
    "feedback.ticketDetails",
    "feedback.sentBy",
    "feedback.reportedFrom",
    "feedback.board.search",
    "feedback.board.total",
    "login.welcome",
    "login.passwordTitle",
    "login.identifierLabel",
    "login.passwordLabel",
    "login.signIn",
    "login.verifyFailed",
    "login.showPassword",
    "login.hidePassword",
    "nav.adminPanel",
    "nav.signOut",
    "nav.localeArabic",
    "nav.localeEnglish",
    "common.cancel",
    "common.confirm",
    "common.notSet",
    "states.loading",
    "states.errorTitle",
    "states.errorFallback",
    "states.retry",
]

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def arb_key(web_key: str) -> str:
    """``feedback.board.total`` -> ``feedbackBoardTotal``."""
    head, *rest = web_key.split(".")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def build(locale: str, catalog: dict[str, str], template: bool) -> dict[str, object]:
    arb: dict[str, object] = {"@@locale": locale}
    for key in KEYS:
        value = catalog[key]
        name = arb_key(key)
        arb[name] = value
        if template:
            meta: dict[str, object] = {"description": f"Web catalog key {key}"}
            names = sorted(set(_PLACEHOLDER.findall(value)))
            if names:
                meta["placeholders"] = {n: {"type": "String"} for n in names}
            arb[f"@{name}"] = meta
    return arb


def expected() -> dict[str, dict[str, object]]:
    out = {}
    for locale in ("ar", "en"):
        catalog = json.loads((FRONTEND_LOCALES / f"{locale}.json").read_text(encoding="utf-8"))
        out[locale] = build(locale, catalog, template=locale == "ar")
    return out


def main() -> None:
    ARB_DIR.mkdir(parents=True, exist_ok=True)
    for locale, arb in expected().items():
        path = ARB_DIR / f"app_{locale}.arb"
        path.write_text(json.dumps(arb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(REPO_ROOT)} ({len(KEYS)} strings)")


if __name__ == "__main__":
    main()
