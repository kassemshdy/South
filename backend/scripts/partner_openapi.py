"""Write the partner API's OpenAPI file from the code.

``docs/partner-api-v1.openapi.json`` is what partners' developers import
(Postman, Insomnia, client generators). It is generated, never edited by
hand: this script takes the app's own OpenAPI document, keeps only the
``/api/partner/`` routes and the schemas they reach, and adds what FastAPI
cannot know -- the production server, the bearer-key scheme and the error
responses the routes really give. ``tests/test_partner_openapi.py`` fails
when the committed file and this output differ, so a change to the feed
cannot ship without its spec.

    python -m scripts.partner_openapi            # rewrite docs/partner-api-v1.openapi.json
    python -m scripts.partner_openapi --check    # exit 1 if it is out of date
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from app.main import create_app

OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "partner-api-v1.openapi.json"
PREFIX = "/api/partner/"

#: Internal schema names, as partners should read them.
RENAMES = {
    "PartnerPage_PartnerStoreOut_": "StorePage",
    "PartnerPage_PartnerProductOut_": "ProductPage",
    "PartnerStoreOut": "Store",
    "PartnerProductOut": "Product",
    "CategoryOut": "Category",
    "LocationOut": "Location",
}

ROUTES = {
    "/api/partner/v1/stores": (
        "List stores",
        "list_stores",
        "Approved stores, ordered by (updated_at, id), paged by cursor.",
        "stores:read",
    ),
    "/api/partner/v1/stores/{slug}": (
        "Get a store",
        "get_store",
        "One approved store by slug (percent-encoded).",
        "stores:read",
    ),
    "/api/partner/v1/products": (
        "List products",
        "list_products",
        "Available products of approved stores, ordered by (updated_at, id), paged by cursor.",
        "products:read",
    ),
}

PARAMETERS = {
    "updated_since": "ISO 8601 timestamp. Only rows changed at or after this time.",
    "cursor": "Opaque. Pass back next_cursor from the previous page.",
    "limit": "Page size, 1 to 200.",
}

ERROR = {
    "type": "object",
    "required": ["error"],
    "properties": {
        "error": {
            "type": "object",
            "required": ["code", "message"],
            "properties": {
                "code": {"type": "string", "description": "Stable, machine-readable error code."},
                "message": {
                    "type": "string",
                    "description": "Human-readable, in the language of Accept-Language "
                    "(Arabic by default, English with `en`).",
                },
                "details": {
                    "type": "object",
                    "description": "Extra data for some errors: retry_after_seconds on 429, "
                    "fields on validation_error.",
                    "additionalProperties": True,
                },
            },
        }
    },
}


def _error(description: str, code: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/Error"},
                "example": {"error": {"code": code, "message": "..."}},
            }
        },
    }


def _errors(path: str) -> dict[str, Any]:
    errors = {
        "401": _error("Missing, wrong or revoked API key.", "bad_api_key"),
        "403": _error("The key does not have the scope this route needs.", "scope_missing"),
        "429": {
            **_error("Rate limit exceeded.", "rate_limited"),
            "headers": {
                "Retry-After": {
                    "schema": {"type": "integer"},
                    "description": "Seconds until the key may call again.",
                }
            },
        },
    }
    if path.endswith("{slug}"):
        errors["404"] = _error("No approved store with this slug.", "not_found")
    else:
        errors["422"] = _error("Invalid parameter or cursor.", "bad_cursor")
    return errors


def _referenced(node: Any, schemas: dict[str, Any], found: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and value.startswith("#/components/schemas/"):
                name = value.rsplit("/", 1)[-1]
                # ``Error`` is ours, added after; everything else is FastAPI's.
                if name not in found and name in schemas:
                    found.add(name)
                    _referenced(schemas[name], schemas, found)
            else:
                _referenced(value, schemas, found)
    elif isinstance(node, list):
        for item in node:
            _referenced(item, schemas, found)


def build() -> dict[str, Any]:
    spec = create_app().openapi()
    paths = {k: copy.deepcopy(v) for k, v in spec["paths"].items() if k.startswith(PREFIX)}
    if set(paths) != set(ROUTES):
        raise SystemExit(f"partner routes changed: {sorted(paths)}; update ROUTES here")
    for path, operations in paths.items():
        summary, operation_id, description, scope = ROUTES[path]
        operation = operations["get"]
        operation.update(
            summary=summary,
            operationId=operation_id,
            description=f"{description} Requires scope `{scope}`.",
            security=[{"PartnerKey": []}],
            tags=["Partner API v1"],
        )
        responses = {"200": operation["responses"]["200"]}
        responses.update(_errors(path))
        operation["responses"] = responses
        for parameter in operation.get("parameters", []):
            if parameter["name"] in PARAMETERS:
                parameter["description"] = PARAMETERS[parameter["name"]]

    schemas = spec["components"]["schemas"]
    found: set[str] = set()
    _referenced(paths, schemas, found)
    components = {name: copy.deepcopy(schemas[name]) for name in sorted(found)}
    for name in ("PartnerStoreOut", "CategoryOut", "LocationOut"):
        components[name].pop("description", None)
    for field in ("logo_thumb_url", "cover_thumb_url"):
        components["PartnerStoreOut"]["properties"][field]["description"] = (
            "Reserved; always null in v1."
        )
    components["Error"] = ERROR

    document = {
        "openapi": "3.1.0",
        "info": {
            "title": "Janoubona Partner API",
            "version": "1.0.0",
            "description": "Read-only feed of Janoubona's approved stores and available "
            "products, with each store's Shopify storefront and buy links. It carries only "
            "what a visitor to janoubona.net can already read. Reference: "
            "docs/PARTNER_API.md.",
        },
        "servers": [{"url": "https://www.janoubona.net", "description": "Production"}],
        "tags": [{"name": "Partner API v1"}],
        "paths": paths,
        "components": {
            "schemas": components,
            "securitySchemes": {
                "PartnerKey": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Per-partner key starting jnb_, issued by Janoubona. "
                    "Keep it server-side.",
                }
            },
        },
    }
    text = json.dumps(document, indent=2, ensure_ascii=False, sort_keys=False)
    for old, new in RENAMES.items():
        text = text.replace(old, new)
    result: dict[str, Any] = json.loads(text)
    return result


def render() -> str:
    return json.dumps(build(), indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="exit 1 if the file is stale")
    args = parser.parse_args(argv)
    text = render()
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != text:
            print(f"{OUTPUT} is out of date; run python -m scripts.partner_openapi")
            return 1
        return 0
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
