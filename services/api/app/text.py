"""Checks for short text that ends up in the agent's context (slice 10)."""

import unicodedata

from pydantic import AfterValidator

# Characters that break a line or control a terminal: Cc (newline, tab, NUL, escape…)
# plus Unicode's line and paragraph separators.
_LINE_BREAKING = {"Cc", "Zl", "Zp"}


def _one_line(text: str) -> str:
    if any(unicodedata.category(ch) in _LINE_BREAKING for ch in text):
        raise ValueError("must be one line, without control characters")
    return text


# Every name a Member types, and every List Addition the agent writes, carries this
# check. These end up in the agent's household context, where a newline inside one
# could pose as a new line of that context ("kale\nDietary Rules: none").
ONE_LINE = AfterValidator(_one_line)
