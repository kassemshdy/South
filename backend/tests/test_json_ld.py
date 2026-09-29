"""The schema.org builders behind the pages' JSON-LD."""

from __future__ import annotations

import json
from decimal import Decimal

from app.core.seo import (
    SeoTags,
    business_json_ld,
    inject,
    json_ld_script,
    product_json_ld,
    site_json_ld,
)


def test_owner_text_can_never_close_the_script_tag() -> None:
    script = json_ld_script({"name": "</script><img src=x onerror=alert(1)>&"})
    body = script.removeprefix('<script type="application/ld+json">').removesuffix("</script>")
    assert "<" not in body and ">" not in body and "&" not in body
    assert json.loads(body)["name"] == "</script><img src=x onerror=alert(1)>&"


def test_a_product_with_no_price_has_no_offer() -> None:
    """An offer without a price is invalid; one with a made-up price is worse."""
    data = product_json_ld(
        name="n",
        description=None,
        url="https://x/p",
        image_url=None,
        price=None,
        currency="USD",
        available=True,
        business_name="b",
        business_url="https://x/b",
    )
    assert "offers" not in data
    assert "image" not in data and "description" not in data


def test_a_sold_out_product_says_so() -> None:
    data = product_json_ld(
        name="n",
        description="d",
        url="https://x/p",
        image_url="https://x/i.jpg",
        price=Decimal("150000"),
        currency="LBP",
        available=False,
        business_name="b",
        business_url="https://x/b",
    )
    assert data["offers"]["price"] == "150000.00"
    assert data["offers"]["priceCurrency"] == "LBP"
    assert data["offers"]["availability"] == "https://schema.org/OutOfStock"


def test_a_shop_shows_only_what_it_has() -> None:
    data = business_json_ld(
        name="n",
        description=None,
        url="https://x/b",
        image_url=None,
        telephone=None,
        location_name=None,
        latitude=None,
        longitude=None,
    )
    assert set(data) == {"@context", "@type", "@id", "name", "url"}

    located = business_json_ld(
        name="n",
        description=None,
        url="https://x/b",
        image_url=None,
        telephone="+9613123456",
        location_name="Tyre",
        latitude=33.27,
        longitude=35.2,
        same_as=["https://facebook.com/x"],
    )
    assert located["telephone"] == "+9613123456"
    assert located["address"]["addressLocality"] == "Tyre"
    assert located["geo"] == {"@type": "GeoCoordinates", "latitude": 33.27, "longitude": 35.2}
    assert located["sameAs"] == ["https://facebook.com/x"]


def test_the_site_contact_appears_only_once_it_is_set() -> None:
    organization, _ = site_json_ld(base_url="https://x", logo_url="https://x/l.png")
    assert "contactPoint" not in organization and "sameAs" not in organization

    organization, _ = site_json_ld(
        base_url="https://x",
        logo_url="https://x/l.png",
        same_as=["https://instagram.com/x"],
        telephone="+9613123456",
    )
    assert organization["sameAs"] == ["https://instagram.com/x"]
    assert organization["contactPoint"]["telephone"] == "+9613123456"


def test_inject_writes_each_block_into_the_head() -> None:
    document = "<html><head><title>t</title></head><body></body></html>"
    tags = SeoTags(
        title="t",
        description="d",
        canonical_url="https://x/",
        json_ld=({"@type": "A"}, {"@type": "B"}),
    )
    result = inject(document, tags)
    head = result.split("</head>")[0]
    assert head.count('type="application/ld+json"') == 2
