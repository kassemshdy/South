"""Arabic text normalization used for search indexing and matching.

Searching Arabic naively fails on everyday spelling variance. The same name is
written with or without hamza on the alef, with teh marbuta or plain heh, with
or without the short-vowel marks that most people omit. Normalizing both the
stored haystack and the incoming query removes that class of misses without any
language-specific database configuration.

The characters below are the algorithm itself rather than translatable text, so
they are written as named Unicode code points: the intent stays readable, and no
Arabic glyph is embedded in source.
"""

from __future__ import annotations

import re
import unicodedata

# --- Letters that vary in everyday spelling ---------------------------------
ALEF = "\u0627"
ALEF_MADDA = "\u0622"
ALEF_HAMZA_ABOVE = "\u0623"
ALEF_HAMZA_BELOW = "\u0625"
ALEF_WASLA = "\u0671"
TEH_MARBUTA = "\u0629"
HEH = "\u0647"
ALEF_MAKSURA = "\u0649"
YEH = "\u064A"
WAW_HAMZA = "\u0624"
WAW = "\u0648"
YEH_HAMZA = "\u0626"
TATWEEL = "\u0640"  # the kashida stretching character

# Harakat and other combining marks: fatha/damma/kasra, tanwin, shadda, sukun,
# plus the Quranic annotation ranges, all of which are optional in writing.
_DIACRITIC_RANGES = (
    "\u0610-\u061A",
    "\u064B-\u065F",
    "\u0670",
    "\u06D6-\u06ED",
)
_DIACRITICS = re.compile(f"[{''.join(_DIACRITIC_RANGES)}{TATWEEL}]")

_ALEF_VARIANTS = re.compile(f"[{ALEF_MADDA}{ALEF_HAMZA_ABOVE}{ALEF_HAMZA_BELOW}{ALEF_WASLA}]")

# Arabic-Indic (U+0660..U+0669) and Extended Arabic-Indic (U+06F0..U+06F9).
_ARABIC_INDIC = "".join(chr(0x0660 + n) for n in range(10))
_EXTENDED_ARABIC_INDIC = "".join(chr(0x06F0 + n) for n in range(10))
_ARABIC_INDIC_DIGITS = str.maketrans(
    _ARABIC_INDIC + _EXTENDED_ARABIC_INDIC, "0123456789" * 2
)

# Letter folds applied after the alef variants above.
_LETTER_FOLDS = {
    TEH_MARBUTA: HEH,
    ALEF_MAKSURA: YEH,
    WAW_HAMZA: WAW,
    YEH_HAMZA: YEH,
}

_WHITESPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_arabic(text: str | None) -> str:
    """Fold Arabic orthographic variance into a comparable form."""
    if not text:
        return ""

    result = unicodedata.normalize("NFKC", text)
    result = result.translate(_ARABIC_INDIC_DIGITS)
    result = _DIACRITICS.sub("", result)
    result = _ALEF_VARIANTS.sub(ALEF, result)
    for source, target in _LETTER_FOLDS.items():
        result = result.replace(source, target)
    result = _PUNCTUATION.sub(" ", result)
    result = _WHITESPACE.sub(" ", result)
    return result.strip().lower()


def build_search_text(*parts: str | None) -> str:
    """Join the searchable fields of a record into one normalized haystack."""
    normalized = [normalize_arabic(part) for part in parts if part]
    return " ".join(part for part in normalized if part)
