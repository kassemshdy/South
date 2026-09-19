"""Localization: catalogs, negotiation, and the no-Arabic-in-code guard."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationError
from app.core.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    LazyJoin,
    LazyText,
    resolve_locale,
    translate,
)
from app.core.urls import normalize_social_url
from app.core.validation_messages import _PARAMS as VALIDATION_TYPES
from app.core.validation_messages import field_errors
from app.models.enums import SocialPlatform
from app.schemas.item import BusinessItemIn
from tests.samples import ar

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
LOCALES_DIR = BACKEND_ROOT / "app" / "locales"
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
FRONTEND_E2E = REPO_ROOT / "frontend" / "e2e"
FRONTEND_LOCALES = FRONTEND_SRC / "i18n" / "locales"

# Arabic, Arabic Supplement and the Arabic presentation-form blocks.
ARABIC = re.compile("[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")


def _catalog(locale: str) -> dict[str, str]:
    return json.loads((LOCALES_DIR / f"{locale}.json").read_text(encoding="utf-8"))


def test_every_locale_has_the_same_keys() -> None:
    """A missing key in one language would silently fall back at runtime."""
    catalogs = {locale: set(_catalog(locale)) for locale in SUPPORTED_LOCALES}
    reference = catalogs[DEFAULT_LOCALE]

    for locale, keys in catalogs.items():
        assert keys == reference, (
            f"{locale}.json differs from {DEFAULT_LOCALE}.json: "
            f"missing={sorted(reference - keys)} extra={sorted(keys - reference)}"
        )


def test_placeholders_match_across_locales() -> None:
    """`{name}` in one language must exist in every other, or format() breaks."""
    placeholder = re.compile(r"\{(\w+)\}")
    reference = _catalog(DEFAULT_LOCALE)

    for locale in SUPPORTED_LOCALES:
        if locale == DEFAULT_LOCALE:
            continue
        for key, template in _catalog(locale).items():
            assert set(placeholder.findall(template)) == set(
                placeholder.findall(reference[key])
            ), f"{locale}.json '{key}' has different placeholders"


def test_english_catalog_contains_no_arabic() -> None:
    for key, value in _catalog("en").items():
        assert not ARABIC.search(value), f"en.json '{key}' still contains Arabic"


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("en-US,en;q=0.9", "en"),
        ("ar-LB,ar;q=0.9,en;q=0.8", "ar"),
        ("en;q=0.4,ar;q=0.9", "ar"),
        ("fr-FR", DEFAULT_LOCALE),
        ("", DEFAULT_LOCALE),
        (None, DEFAULT_LOCALE),
    ],
)
def test_locale_negotiation(header: str | None, expected: str) -> None:
    assert resolve_locale(header) == expected


def test_translate_interpolates_and_falls_back() -> None:
    assert "10" in translate("image.gallery_limit", "en", max=10)
    # An unknown key returns the key rather than raising or rendering blank.
    assert translate("no.such.key", "en") == "no.such.key"


def test_lazy_params_resolve_in_the_reader_locale() -> None:
    """Regression: a label resolved at raise time leaked Arabic into English."""
    error = ValidationError(
        "url.invalid_social_host", params={"platform": LazyText("platform.instagram")}
    )

    assert "Instagram" in error.message("en")
    assert not ARABIC.search(error.message("en"))
    assert ARABIC.search(error.message("ar"))


def test_lazy_join_uses_the_translated_separator() -> None:
    joined = LazyJoin(("business.field.name", "business.field.logo"))

    english = joined.resolve("en")
    assert english == "business name, business logo"
    assert not ARABIC.search(english)


def test_error_messages_follow_the_accept_language_header(
    client: TestClient,
) -> None:
    arabic = client.get("/api/businesses/does-not-exist")
    english = client.get(
        "/api/businesses/does-not-exist", headers={"Accept-Language": "en-GB,en;q=0.9"}
    )

    assert arabic.status_code == english.status_code == 404
    # The machine-readable code is stable across languages; only wording changes.
    assert arabic.json()["error"]["code"] == english.json()["error"]["code"]
    assert ARABIC.search(arabic.json()["error"]["message"])
    assert not ARABIC.search(english.json()["error"]["message"])


def _field_messages(response) -> list[str]:
    return [field["message"] for field in response.json()["error"]["details"]["fields"]]


def test_validation_errors_are_translated(client: TestClient) -> None:
    """Both halves, because for a long time only one was checked.

    The original version of this test asserted that the *English* response
    carried no Arabic -- which passed while every field message was pydantic's
    own untranslated English, in both languages. An Arabic reader filling in
    a form was told "String should have at least 6 characters".
    """
    arabic = client.post("/api/auth/login", json={"identifier": "", "password": ""})
    english = client.post(
        "/api/auth/login",
        json={"identifier": "", "password": ""},
        headers={"Accept-Language": "en"},
    )

    assert arabic.status_code == english.status_code == 422
    # The envelope *and* the per-field sentence, which is the part that broke.
    assert ARABIC.search(arabic.json()["error"]["message"])
    assert all(ARABIC.search(message) for message in _field_messages(arabic))
    assert not ARABIC.search(json.dumps(english.json(), ensure_ascii=False))
    # The field name is an identifier the form matches inputs on, so it stays
    # the same in both languages.
    assert (
        arabic.json()["error"]["details"]["fields"][0]["field"]
        == english.json()["error"]["details"]["fields"][0]["field"]
        == "identifier"
    )


def test_a_missing_field_is_reported_in_the_readers_language(client: TestClient) -> None:
    arabic = client.post("/api/auth/login", json={})
    assert arabic.status_code == 422
    assert all(ARABIC.search(message) for message in _field_messages(arabic))


def test_a_parse_failure_never_leaks_pydantics_own_explanation(
    client: TestClient,
) -> None:
    """pydantic puts an English sentence in ``ctx['error']`` for a failed
    parse -- the UUID one explains ``urn:uuid:`` prefixes. A mapping that
    passed the whole context through would smuggle back exactly the English
    this is meant to remove."""
    response = client.post(
        "/api/businesses/does-not-exist/orders",
        json={
            "customer_name": ar("order.customer"),
            "customer_phone": "03990100",
            "lines": [{"item_id": "not-a-uuid", "quantity": 1}],
        },
    )

    assert response.status_code == 422
    messages = _field_messages(response)
    assert all(ARABIC.search(message) for message in messages)
    assert not any("urn:uuid" in message for message in messages)


def test_a_message_raised_by_our_own_validator_survives_intact() -> None:
    """Several ``@field_validator``s here raise ``ValueError(translate(...))``,
    so the sentence is already in the reader's language and must be passed
    through rather than replaced. Only pydantic's "Value error, " prefix has
    to come off.

    Asserted against ``BusinessItemIn`` directly: the alternative is a whole
    owned-business fixture to reach one branch of a pure function.
    """
    expected = translate("item.title_required")

    with pytest.raises(PydanticValidationError) as raised:
        BusinessItemIn(title="   ")

    messages = [field["message"] for field in field_errors(raised.value.errors())]
    assert expected in messages
    assert not any(message.startswith("Value error") for message in messages)


def test_every_mapped_validation_type_has_a_sentence_in_every_locale() -> None:
    """The mapping and the catalogs have to move together: adding a pydantic
    error type without wording for it silently reintroduces the generic
    fallback for a case somebody bothered to enumerate."""
    for kind in VALIDATION_TYPES:
        key = f"validation.{kind}"
        for locale in SUPPORTED_LOCALES:
            assert key in _catalog(locale), f"{key} missing from {locale}.json"


def _arabic_offenders(root: Path, suffixes: set[str], exempt: set[Path]) -> list[str]:
    offenders: list[str] = []
    skip_parts = {".venv", "__pycache__", "alembic", "node_modules", "dist"}

    for path in root.rglob("*"):
        if path.suffix not in suffixes or not path.is_file():
            continue
        if any(part in skip_parts for part in path.parts):
            continue
        if any(str(path).startswith(str(directory)) for directory in exempt):
            continue
        if path.name == "test_i18n.py":  # this file defines the Arabic pattern
            continue

        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if ARABIC.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{number}")
    return offenders


def test_backend_source_contains_no_arabic_text() -> None:
    """The point of the whole exercise: strings live in catalogs, not in code.

    Catalogs, seed content and test fixtures are data files and are exempt;
    everything else must be free of Arabic so that translating the product never
    means editing Python.
    """
    offenders = _arabic_offenders(
        BACKEND_ROOT,
        {".py"},
        {LOCALES_DIR, BACKEND_ROOT / "scripts" / "data", BACKEND_ROOT / "tests" / "fixtures"},
    )
    assert not offenders, "Arabic text found outside resource files: " + ", ".join(offenders)


@pytest.mark.skipif(not FRONTEND_SRC.exists(), reason="frontend sources not present")
def test_frontend_source_contains_no_arabic_text() -> None:
    """Same rule on the client: components render keys, never literals."""
    offenders = _arabic_offenders(FRONTEND_SRC, {".ts", ".tsx"}, {FRONTEND_LOCALES})
    assert not offenders, "Arabic text found outside resource files: " + ", ".join(offenders)


@pytest.mark.skipif(not FRONTEND_E2E.exists(), reason="e2e suite not present")
def test_e2e_suite_contains_no_arabic_text() -> None:
    """The acceptance test asserts on catalog values and fixture data, never on
    Arabic typed into the test itself — so renaming a key fails the test rather
    than letting it assert against stale copy."""
    offenders = _arabic_offenders(FRONTEND_E2E, {".ts"}, {FRONTEND_E2E / "fixtures"})
    assert not offenders, "Arabic text found outside resource files: " + ", ".join(offenders)


@pytest.mark.skipif(not FRONTEND_LOCALES.exists(), reason="frontend catalogs not present")
def test_frontend_catalogs_match() -> None:
    """A key present in one language and missing from another breaks the build,
    but only if the catalogs are actually kept in step."""
    catalogs = {
        name: set(json.loads((FRONTEND_LOCALES / f"{name}.json").read_text(encoding="utf-8")))
        for name in ("ar", "en")
    }
    assert catalogs["ar"] == catalogs["en"], (
        f"frontend catalogs differ: missing={sorted(catalogs['ar'] - catalogs['en'])} "
        f"extra={sorted(catalogs['en'] - catalogs['ar'])}"
    )


@pytest.mark.skipif(not FRONTEND_LOCALES.exists(), reason="frontend catalogs not present")
def test_readiness_keys_exist_in_the_frontend_catalogs() -> None:
    """The readiness endpoints hand the client *keys*, not sentences.

    ``/businesses/{id}/readiness`` and ``/my/talent/readiness`` return catalog
    keys so the reader's locale decides the wording — which only works if the
    frontend can actually resolve them. A key added to a service's requirement
    list and not mirrored into the frontend catalogs renders as the raw key
    (``business.field.logo``) in the owner's face, so it is caught here rather
    than in a screenshot.
    """
    emitted = {
        key
        for module in ("business.py", "talent.py")
        for key in re.findall(
            r'"((?:business|talent)\.field\.\w+)"',
            (BACKEND_ROOT / "app" / "services" / module).read_text(encoding="utf-8"),
        )
    }
    assert emitted, "no readiness keys found — has the requirement list moved?"

    backend = set(_catalog(DEFAULT_LOCALE))
    frontend = set(
        json.loads((FRONTEND_LOCALES / f"{DEFAULT_LOCALE}.json").read_text(encoding="utf-8"))
    )

    assert not (emitted - backend), (
        f"readiness keys missing from the backend catalog: {sorted(emitted - backend)}"
    )
    assert not (emitted - frontend), (
        "readiness keys missing from the frontend catalogs: "
        f"{sorted(emitted - frontend)}. Mirror them into frontend/src/i18n/locales/."
    )


# Language names are the one thing an English catalog states in another
# language. Every language picker does this — a person who switched by mistake
# and cannot read where they landed still recognises the name of their own
# language, which a translated "Arabic" would deny them. Narrow and explicit,
# so the check below keeps its teeth for genuinely untranslated strings.
_ENDONYM_KEYS = frozenset({"nav.localeArabic"})


@pytest.mark.skipif(not FRONTEND_LOCALES.exists(), reason="frontend catalogs not present")
def test_frontend_english_catalog_contains_no_arabic() -> None:
    english = json.loads((FRONTEND_LOCALES / "en.json").read_text(encoding="utf-8"))
    for key, value in english.items():
        if key in _ENDONYM_KEYS:
            continue
        assert not ARABIC.search(value), f"frontend en.json '{key}' still contains Arabic"


@pytest.mark.skipif(not FRONTEND_LOCALES.exists(), reason="frontend catalogs not present")
def test_every_endonym_exception_is_still_used() -> None:
    """An exception that outlives its key silently widens the guard above."""
    english = json.loads((FRONTEND_LOCALES / "en.json").read_text(encoding="utf-8"))
    missing = _ENDONYM_KEYS - set(english)
    assert not missing, f"stale endonym exceptions, remove them: {sorted(missing)}"


def test_staging_is_hardened_like_production_bar_one_thing() -> None:
    """The demo password is the only shortcut staging is allowed."""
    Settings(
        app_env="staging",
        secret_key="a-real-secret",
        seed_owner_password="demo-password",
    ).enforce_production_safety()

    weak = Settings(
        app_env="staging",
        secret_key="dev-insecure-secret-change-me",
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        weak.enforce_production_safety()


def test_domain_error_carries_a_key_not_a_sentence() -> None:
    error = NotFoundError("business.not_found")
    assert error.message_key == "business.not_found"
    assert error.message("en") == "Business not found."


def test_social_url_error_is_localized() -> None:
    with pytest.raises(ValidationError) as caught:
        normalize_social_url(SocialPlatform.FACEBOOK, "https://evil.example.com")

    assert "Facebook" in caught.value.message("en")
