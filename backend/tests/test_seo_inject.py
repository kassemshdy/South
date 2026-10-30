"""The head rewrite takes text people typed, so nothing in it may be read as
regex syntax.

A shop, product or profile name with a backslash in it made ``re.sub`` treat
the text as a group reference and raise, and the page answered 500 for as
long as the name stayed.
"""

from __future__ import annotations

from app.core.seo import SeoTags, inject

DOCUMENT = (
    "<html><head><title>x</title>"
    '<meta name="description" content="x">'
    '<meta property="og:title" content="x">'
    '<link rel="canonical" href="x">'
    "</head><body></body></html>"
)


def test_backslashes_in_typed_text_are_written_as_text() -> None:
    tags = SeoTags(
        title="Shop \\q \\1 \\g<0>",
        description="Line \\n with \\2",
        canonical_url="https://example.test/business/a\\b",
    )
    html = inject(DOCUMENT, tags)
    assert "<title>Shop \\q \\1 \\g&lt;0&gt;</title>" in html
    assert 'content="Line \\n with \\2"' in html
    assert 'href="https://example.test/business/a\\b"' in html
