from __future__ import annotations

import random
from abc import ABC, abstractmethod
from enum import Enum, EnumMeta, IntEnum, auto, unique
from functools import cache
from typing import TYPE_CHECKING, Any, Final, NamedTuple, cast

from contact_messenger_bot.api import utils
from contact_messenger_bot.api.messages import anniversary, birthday

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterable

_RANDOM: Final[random.Random] = random.Random()  # noqa: S311


class _CaseInsensitiveEnumMeta(EnumMeta):
    def __call__(cls, value: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        try:
            return super().__call__(value, *args, **kwargs)
        except ValueError:
            items = cast("Iterable[Enum]", cls)
            for item in items:
                if item.name.casefold() == value.casefold():
                    return cast("type[Enum]", item)
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
        mobile_email_addresses = [n for n in self.email_addresses if n.is_phone]
        if not mobile_email_addresses:
            return None
        primary_mobile_email_address = next((n for n in mobile_email_addresses if n.is_primary), None)
        if primary_mobile_email_address:
            return primary_mobile_email_address
        return mobile_email_addresses[0]

    def get_primary_email_address(self) -> EmailAddress | None:
        """Gets the email address associated with the contact's phone number."""
        bot_email_address = next((n for n in self.email_addresses if n.is_bot), None)
        if bot_email_address:
            return bot_email_address
        return next((n for n in self.email_addresses if n.is_primary), None)

    def get_us_mobile_number(self) -> PhoneNumber | None:
        """Gets the mobile number that can receive SMS messages."""
        us_mobile_numbers = [n for n in self.mobile_numbers if n.country() == Country.US]
        bot_mobile_number = next((n for n in us_mobile_numbers if n.is_bot), None)
        if bot_mobile_number:
            return bot_mobile_number
        primary_mobile_number = next((n for n in us_mobile_numbers if n.is_primary), None)
        if primary_mobile_number:
            return primary_mobile_number
        return next(iter(us_mobile_numbers), None)

    def get_all_mobile_email_addresses(self) -> list[EmailAddress]:
        """Gets the possible email addresses for the phone carriers that match the mobile number associated."""
        mobile_email_addresses = [(n, n.get_email_addresses()) for n in self.mobile_numbers]
        if not mobile_email_addresses:
            return []

        bot_mobile_email_addresses = next((ea for n, ea in mobile_email_addresses if n.is_bot), None)
        if bot_mobile_email_addresses:
            return bot_mobile_email_addresses

        primary_email_addresses = next((ea for n, ea in mobile_email_addresses if n.is_primary), None)
        if primary_email_addresses:
            return primary_email_addresses

        return mobile_email_addresses[0][1]


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
    is_bot: bool = False

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
        addresses = (carrier.get_email(self) for carrier in MobileCarrier.get_carriers() if carrier.enabled)
        return [
            EmailAddress(address, is_primary=self.is_primary, is_phone=True, is_bot=self.is_bot)
            for address in addresses
            if address is not None
        ]


class EmailAddress(NamedTuple):
    address: str
    is_primary: bool
    is_phone: bool
    is_bot: bool = False

    def get_mobile_carrier(self) -> MobileCarrier | None:
        """Gets the mobile carrier associated with this email address."""
        for carrier in MobileCarrier.get_carriers():
            if carrier.is_carrier(self.address):
                return carrier
        return None

    def is_enabled(self) -> bool:
        """Indicates whether this email address is enabled."""
        if self.is_phone:
            carrier = self.get_mobile_carrier()
            if carrier:
                return carrier.enabled
        return True


class MobileCarrier(ABC):
    def __repr__(self) -> str:
        return self.__class__.__name__

    @property
    def enabled(self) -> bool:
        """Indicates whether this carrier is enabled."""
        return True

    def is_carrier(self, address: str) -> bool:
        return False

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
    def domain(self) -> str:
        pass

    def is_carrier(self, address: str) -> bool:
        return address.endswith(f"@{self.domain}")

    def get_email(self, number: PhoneNumber) -> str | None:
        if number.country() == self.country:
            return f"{number.shortnumber()}@{self.domain}"
        return None


class ATT(USMobileCarrier):
    domain: Final[str] = "txt.att.net"

    @property
    def enabled(self) -> bool:
        """Indicates whether this carrier is enabled."""
        return False


class GoogleFi(USMobileCarrier):
    domain: Final[str] = "msg.fi.google.com"


class TMobile(USMobileCarrier):
    domain: Final[str] = "tmomail.com"


class Verison(USMobileCarrier):
    domain: Final[str] = "vtext.com"
