"""Arabic text normalization used for search indexing and matching.

Searching Arabic naively fails on everyday spelling variance: أحمد/احمد,
حلويّات/حلويات, بلدة/بلده. Normalizing both the stored haystack and the incoming
query removes that class of misses without any language-specific database
configuration.
"""

from __future__ import annotations

import re
import unicodedata

# Harakat (fatha, damma, kasra, shadda, sukun, tanwin) and the tatweel filler.
_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_ALEF_VARIANTS = re.compile(r"[آأإٱ]")  # آ أ إ ٱ
_WHITESPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)
_ARABIC_INDIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize_arabic(text: str | None) -> str:
    """Fold Arabic orthographic variance into a comparable form."""
    if not text:
        return ""

    result = unicodedata.normalize("NFKC", text)
    result = result.translate(_ARABIC_INDIC_DIGITS)
    result = _DIACRITICS.sub("", result)
    result = _ALEF_VARIANTS.sub("ا", result)  # → ا
    result = result.replace("ة", "ه")  # ة → ه
    result = result.replace("ى", "ي")  # ى → ي
    result = result.replace("ؤ", "و")  # ؤ → و
    result = result.replace("ئ", "ي")  # ئ → ي
    result = _PUNCTUATION.sub(" ", result)
    result = _WHITESPACE.sub(" ", result)
    return result.strip().lower()


def build_search_text(*parts: str | None) -> str:
    """Join the searchable fields of a record into one normalized haystack."""
    normalized = [normalize_arabic(part) for part in parts if part]
    return " ".join(part for part in normalized if part)
