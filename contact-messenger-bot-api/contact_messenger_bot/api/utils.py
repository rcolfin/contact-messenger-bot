from __future__ import annotations

import inspect
import re
from typing import TYPE_CHECKING, Final

from contact_messenger_bot.api import constants

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


def get_all_subclasses(class_type: type) -> Iterable[type]:
    """Gets all the subclasses of the specified type."""
    for subclass in class_type.__subclasses__():
        if not inspect.isabstract(subclass):
            yield subclass
        yield from get_all_subclasses(subclass)


def is_truthy(value: str | None, default: bool = False) -> bool:
    """
    Determines if the value is considered True.
    Args:
        value (str | None): The value.
        default (bool): The default value to return if value is None.
    Returns:
        True or False

    >>> is_truthy("True")
    True
    >>> is_truthy("true")
    True
    >>> is_truthy("1")
    True
    >>> is_truthy(None)
    False
    >>> is_truthy(None, True)
    True
    >>> is_truthy("False")
    False
    >>> is_truthy("false")
    False
    >>> is_truthy("0")
    False
    """
    if value is None:
        return default
    return value.casefold() in constants.TRUTHY
