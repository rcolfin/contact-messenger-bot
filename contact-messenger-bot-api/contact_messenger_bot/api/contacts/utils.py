import re
from typing import Final

US_CANOICAL_PHONE_NUMBER: Final[re.Pattern] = re.compile(r"^(?:\+1\s?)?\d{10}$")


def is_us_phone_number(number: str) -> bool:
    """Determines if a number if a US Canoical Phone Number."""
    return bool(US_CANOICAL_PHONE_NUMBER.match(number))
