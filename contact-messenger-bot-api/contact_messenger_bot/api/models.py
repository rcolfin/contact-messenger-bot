from __future__ import annotations

import random
from collections.abc import Iterable
from enum import Enum, EnumMeta, IntEnum, auto, unique
from typing import TYPE_CHECKING, Any, Final, NamedTuple, cast

from contact_messenger_bot.api import constants, utils
from contact_messenger_bot.api.messages import anniversary, birthday

if TYPE_CHECKING:
    import datetime

_RANDOM: Final[random.Random] = random.Random()  # noqa: S311


class _CaseInsensitiveEnumMeta(EnumMeta):
    def __call__(cls, value: str, *args: list[Any], **kwargs: Any) -> type[Enum]:  # noqa: ANN401
        try:
            return super().__call__(value, *args, **kwargs)
        except ValueError:
            items = cast(Iterable[Enum], cls)
            for item in items:
                if item.name.casefold() == value.casefold():
                    return cast(type[Enum], item)
            raise


@unique
class Country(str, Enum, metaclass=_CaseInsensitiveEnumMeta):
    US = "US"


@unique
class CustomFields(str, Enum):
    BOT_SALUATION = "BOT_SALUATION"
    BOT_OPT_OUT = "BOT_OPT_OUT"


@unique
class SortOrder(str, Enum, metaclass=_CaseInsensitiveEnumMeta):
    LAST_MODIFIED_ASCENDING = "LAST_MODIFIED_ASCENDING"  # Sort people by when they were changed; older entries first.
    LAST_MODIFIED_DESCENDING = "LAST_MODIFIED_DESCENDING"  # Sort people by when they were changed; newer entries first.
    FIRST_NAME_ASCENDING = "FIRST_NAME_ASCENDING"  # Sort people by first name.
    LAST_NAME_ASCENDING = "LAST_NAME_ASCENDING"  # 	Sort people by last name.


class DateType(IntEnum):
    BIRTHDAY = auto()
    ANNIVERSARY = auto()

    def subject(self, given_name: str) -> str:
        if self == self.BIRTHDAY:
            return self._message_fmt(birthday.SUBJECTS).format(GIVEN_NAME=given_name)
        if self == self.ANNIVERSARY:
            return self._message_fmt(anniversary.SUBJECTS).format(GIVEN_NAME=given_name)

        raise NotImplementedError

    def message(self, given_name: str) -> str:
        if self == self.BIRTHDAY:
            return self._message_fmt(birthday.MESSAGES).format(GIVEN_NAME=given_name)
        if self == self.ANNIVERSARY:
            return self._message_fmt(anniversary.MESSAGES).format(GIVEN_NAME=given_name)

        raise NotImplementedError

    @staticmethod
    def _message_fmt(mesages: list[str]) -> str:
        idx = int(_RANDOM.uniform(0, len(mesages)))
        return mesages[idx]


class Coordinate(NamedTuple):
    latitude: float
    longitude: float


class DateTuple(NamedTuple):
    type: DateType
    date: datetime.date

    def __repr__(self) -> str:
        return f"{self.date} ({self.type.name})"

    def is_today(self, today: datetime.date) -> bool:
        """Determines if the date is today."""
        return today.month == self.date.month and today.day == self.date.day


class Address(NamedTuple):
    postal_code: str
    tz: datetime.tzinfo | None


class Contact(NamedTuple):
    given_name: str
    display_name: str
    mobile_numbers: list[PhoneNumber]
    dates: list[DateTuple]
    home_addresses: list[Address]
    email_addresses: list[EmailAddress]
    groups: list[ContactGroup]
    metadata: dict[str, Any]

    def __repr__(self) -> str:
        return self.display_name

    @property
    def saluation(self) -> str:
        """Gets the saluation in sending messages."""
        return self.metadata.get(CustomFields.BOT_SALUATION, self.given_name)

    def get_mobile_email_address(self) -> EmailAddress | None:
        """Gets the email address associated with the contact's phone number."""
        mobile_email_addresses = [n for n in self.email_addresses if n.is_phone]
        if not mobile_email_addresses:
            return None
        prmary_mobile_email_addresses = (n for n in mobile_email_addresses if n.is_primary)
        return next(prmary_mobile_email_addresses, None) or mobile_email_addresses[0]

    def get_primary_email_address(self) -> EmailAddress | None:
        """Gets the email address associated with the contact's phone number."""
        prmary_email_addresses = (n for n in self.email_addresses if n.is_primary)
        return next(prmary_email_addresses, None)

    def get_us_mobile_number(self) -> PhoneNumber | None:
        """Gets the mobile number that can receive SMS messages."""
        us_mobile_numbers = (n for n in self.mobile_numbers if n.is_us_phone_number())
        return next(us_mobile_numbers, None)

    @property
    def opt_out_messages(self) -> bool:
        """Gets a value indicating whether this contact has opt out to receiving messages."""
        return self.metadata.get(CustomFields.BOT_OPT_OUT, "").casefold() in constants.TRUTHY


class Profile(NamedTuple):
    given_name: str
    display_name: str
    mobile_number: PhoneNumber
    email_address: EmailAddress


class ContactGroup(NamedTuple):
    name: str
    members: frozenset[str]

    def __repr__(self) -> str:
        return self.name


class PhoneNumber(NamedTuple):
    number: str
    is_primary: bool

    def is_us_phone_number(self) -> bool:
        """Determines if the number is a US phone number."""
        return utils.is_us_phone_number(self.number)


class EmailAddress(NamedTuple):
    address: str
    is_primary: bool
    is_phone: bool
