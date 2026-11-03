"""Checks on what a job seeker types into their public profile.

Two rules from the candidate directory ticket (the owners', 31 Oct 2026):

- **The bio holds no contact details.** People wrote their phone, email and
  questions to the team into it. Numbers belong in their own fields, where
  the "show my number" choice applies to them; a number in the bio would be
  public whatever the person chose there.
- **The name is a person's name**, letters only (Arabic or Latin), first and
  last, so an entry like "nursing. home" is refused at the door.
"""

from __future__ import annotations

import re
import unicodedata

# Seven or more digits, in Western or Arabic-Indic form, with the spaces,
# dashes, dots and brackets people put between them.
_DIGIT = "[0-9\\u0660-\\u0669\\u06f0-\\u06f9]"
_PHONE = re.compile(rf"(?:{_DIGIT}[\s\-./()]*){{7,}}")
_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_LINK = re.compile(r"(?:https?://|www\.)|\b[\w-]+\.(?:com|net|org|me|lb|io|co)\b", re.I)

# Inside a name, between the letters.
_NAME_JOINERS = frozenset(" -'’")


def contains_contact_details(text: str | None) -> bool:
    """True when ``text`` carries a phone number, an email or a link."""
    if not text:
        return False
    return bool(_PHONE.search(text) or _EMAIL.search(text) or _LINK.search(text))


def is_person_name(name: str) -> bool:
    """Arabic or Latin letters only, at least two words of two letters."""
    words = name.split()
    if len(words) < 2:
        return False
    for char in name:
        if char in _NAME_JOINERS:
            continue
        category = unicodedata.category(char)
        if category == "Mn":  # Arabic vowel marks
            continue
        if not char.isalpha():
            return False
        script = unicodedata.name(char, "")
        if not (script.startswith("ARABIC") or script.startswith("LATIN")):
            return False
    letters = [sum(1 for c in word if c.isalpha()) for word in words]
    return sum(1 for count in letters if count >= 2) >= 2
