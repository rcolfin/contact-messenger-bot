from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable

US_CANOICAL_PHONE_NUMBER: Final[re.Pattern] = re.compile(r"^(?:\+1\s?)?\d{10}$")


def is_us_phone_number(number: str) -> bool:
    """Determines if a number if a US Canoical Phone Number."""
    return bool(US_CANOICAL_PHONE_NUMBER.match(number))


def to_frozen_set(collection: Iterable[str] | None) -> frozenset[str] | None:
    """Builds a frozenset of the input sequence provided the input sequence has elements."""
    if collection is None:
        return None
    result = frozenset(s.casefold() for s in collection)
    return result if result else None
