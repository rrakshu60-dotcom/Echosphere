"""
Reading the free-text target audience of a notice ("Entire College", "CSE 3rd Sem", ...).

Matching is by whole words, never by substring: a short department code must not match inside an
unrelated word ("ISE" in "raise", "CHE" in "teachers"), and "all" must not match inside "hall".
"""

import re
from typing import Iterable, List, Optional, Set

_WORD = re.compile(r"[a-z0-9]+")
_INSTITUTION_WIDE_WORDS = {"entire", "all", "institution", "everyone", "everybody", "whole"}
_INSTITUTION_WIDE_PHRASES = ("college wide", "campus wide", "institution wide")


def audience_words(text: Optional[str]) -> List[str]:
    return _WORD.findall((text or "").lower())


def _contains_phrase(words: List[str], phrase: str) -> bool:
    target = audience_words(phrase)
    if not target:
        return False
    n = len(target)
    return any(words[i:i + n] == target for i in range(len(words) - n + 1))


def is_institution_wide(text: Optional[str]) -> bool:
    words = audience_words(text)
    if _INSTITUTION_WIDE_WORDS.intersection(words):
        return True
    return any(_contains_phrase(words, p) for p in _INSTITUTION_WIDE_PHRASES)


def mentions_department(text: Optional[str], code: Optional[str], name: Optional[str] = None) -> bool:
    """True when the audience names the department by its code or full name, as whole words."""
    words = audience_words(text)
    return bool((code and _contains_phrase(words, code)) or (name and _contains_phrase(words, name)))


def mentioned_departments(text: Optional[str], departments: Iterable) -> Set[int]:
    """Ids of the departments (objects with id, code, name) that the audience names."""
    return {d.id for d in departments if mentions_department(text, getattr(d, "code", None), getattr(d, "name", None))}
