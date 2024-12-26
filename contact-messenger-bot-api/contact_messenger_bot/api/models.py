from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections.abc import Iterable
from enum import Enum, EnumMeta, IntEnum, auto, unique
from functools import cache
from typing import TYPE_CHECKING, Any, Final, NamedTuple, cast

from contact_messenger_bot.api import utils
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

    def __repr__(self) -> str:
        return self.name


@unique
class CustomFields(str, Enum):
    BOT_SALUATION = "BOT_SALUATION"
    BOT_OPT_OUT = "BOT_OPT_OUT"

    def __repr__(self) -> str:
        return self.name


@unique
class SortOrder(str, Enum, metaclass=_CaseInsensitiveEnumMeta):
    LAST_MODIFIED_ASCENDING = "LAST_MODIFIED_ASCENDING"  # Sort people by when they were changed; older entries first.
    LAST_MODIFIED_DESCENDING = "LAST_MODIFIED_DESCENDING"  # Sort people by when they were changed; newer entries first.
    FIRST_NAME_ASCENDING = "FIRST_NAME_ASCENDING"  # Sort people by first name.
    LAST_NAME_ASCENDING = "LAST_NAME_ASCENDING"  # 	Sort people by last name.


class DateType(IntEnum):
    BIRTHDAY = auto()
    ANNIVERSARY = auto()

    def __repr__(self) -> str:
        return self.name

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

    def is_today(self, test: datetime.date) -> bool:
        """Determines if the date is today."""
        return test.month == self.date.month and test.day == self.date.day


class Address(NamedTuple):
    postal_code: str
    tz: datetime.tzinfo | None


class Contact(NamedTuple):
    given_name: str
    display_name: str
    nickname: str | None
    mobile_numbers: list[PhoneNumber]
    dates: list[DateTuple]
    home_addresses: list[Address]
    email_addresses: list[EmailAddress]
    groups: list[str]
    metadata: dict[str, Any]

    def __repr__(self) -> str:
        return self.display_name

    def can_notify_today(self, test: datetime.date) -> bool:
        """Determines whether this Contact has notifications today."""
        return any(dt.is_today(test) for dt in self.dates)

    def is_member(self, groups: frozenset[str]) -> bool:
        """Determines if this Contact is a member of one of the specified groups."""
        return bool(groups.intersection(g.casefold() for g in self.groups))

    @property
    def saluation(self) -> str:
        """Gets the saluation in sending messages."""
        return self.metadata.get(CustomFields.BOT_SALUATION) or self.nickname or self.given_name

    @property
    def opt_out_messages(self) -> bool:
        """Gets a value indicating whether this contact has opt out to receiving messages."""
        return utils.is_truthy(self.metadata.get(CustomFields.BOT_OPT_OUT))

    def get_primary_mobile_email_address(self) -> EmailAddress | None:
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
        us_mobile_numbers = (n for n in self.mobile_numbers if n.country() == Country.US)
        return next(us_mobile_numbers, None)

    def get_all_mobile_email_addresses(self) -> list[EmailAddress]:
        """Gets the possible email addresses for the phone carriers that match the mobile number associated."""
        mobile_email_addresses = ((n.is_primary, n.get_email_addresses()) for n in self.mobile_numbers)
        mobile_email_addresses_lst = [(is_primary, ea) for is_primary, ea in mobile_email_addresses if ea]
        if not mobile_email_addresses_lst:
            return []

        r = next((ea for is_primary, ea in mobile_email_addresses_lst if is_primary), None)
        if r:
            return r
        return next((ea for _is_primary, ea in mobile_email_addresses_lst), [])


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

    def country(self) -> Country | None:
        """Determines if the Country of the number."""
        return Country.US if utils.is_us_phone_number(self.number) else None

    def shortnumber(self) -> str:
        """Gets the short representation of the phone number."""
        if self.country() == Country.US:
            return self.number.replace("-", "")[-10:]
        return self.number

    def get_email_addresses(self) -> list[EmailAddress]:
        """Gets the list of email addresses associated with phone carriers in the same Country as the number."""
        addresses = (carrier.get_email(self) for carrier in MobileCarrier.get_carriers())
        return [
            EmailAddress(address, is_primary=self.is_primary, is_phone=True)
            for address in addresses
            if address is not None
        ]


class EmailAddress(NamedTuple):
    address: str
    is_primary: bool
    is_phone: bool


class MobileCarrier(ABC):
    def __repr__(self) -> str:
        return self.__class__.__name__

    @property
    @abstractmethod
    def country(self) -> Country:
        pass

    @abstractmethod
    def get_email(self, number: PhoneNumber) -> str | None:
        pass

    @staticmethod
    @cache
    def get_carriers() -> list[MobileCarrier]:
        return [x() for x in utils.get_all_subclasses(MobileCarrier)]


class USMobileCarrier(MobileCarrier):
    @property
    def country(self) -> Country:
        return Country.US

    @property
    @abstractmethod
    def _format(self) -> str:
        pass

    def get_email(self, number: PhoneNumber) -> str | None:
        if number.country() == self.country:
            return self._format.format(number.shortnumber())
        return None


class ATT(USMobileCarrier):
    _format: Final[str] = "{}@txt.att.net"


class GoogleFi(USMobileCarrier):
    _format: Final[str] = "{}@msg.fi.google.com"


class TMobile(USMobileCarrier):
    _format: Final[str] = "{}@tmomail.com"


class Verison(USMobileCarrier):
    _format: Final[str] = "{}@vtext.com"
