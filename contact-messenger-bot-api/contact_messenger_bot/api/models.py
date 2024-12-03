from __future__ import annotations

import random
from collections.abc import Iterable
from enum import Enum, EnumMeta, IntEnum, auto, unique
from typing import TYPE_CHECKING, Any, Final, NamedTuple, cast

from contact_messenger_bot.api import constants
from contact_messenger_bot.api.messages import anniversary, birthday
from contact_messenger_bot.api.services import messaging

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


class Coordinate(NamedTuple):
    latitude: float
    longitude: float


@unique
class Country(str, Enum, metaclass=_CaseInsensitiveEnumMeta):
    US = "US"


class DateType(IntEnum):
    BIRTHDAY = auto()
    ANNIVERSARY = auto()

    def format(self, given_name: str) -> str:
        if self == self.BIRTHDAY:
            return self._message_fmt(birthday.MESSAGES).format(GIVEN_NAME=given_name)
        if self == self.ANNIVERSARY:
            return self._message_fmt(anniversary.MESSAGES).format(GIVEN_NAME=given_name)

        raise NotImplementedError

    @staticmethod
    def _message_fmt(mesages: list[str]) -> str:
        idx = int(_RANDOM.uniform(0, len(mesages)))
        return mesages[idx]


class DateTuple(NamedTuple):
    type: DateType
    date: datetime.date

    def __repr__(self) -> str:
        return f"{self.date} ({self.type.name})"

    def is_today(self) -> bool:
        """Determines if the date is today."""
        return constants.TODAY.month == self.date.month and constants.TODAY.day == self.date.day


class Contact(NamedTuple):
    given_name: str
    display_name: str
    mobile_number: str
    dates: list[DateTuple]
    home_postal_code: str | None
    tz: datetime.tzinfo | None
    groups: list[ContactGroup]
    metadata: dict[str, Any]

    def __repr__(self) -> str:
        return self.display_name

    @property
    def saluation(self) -> str:
        """Gets the saluation in sending messages."""
        return self.metadata.get(CustomFields.BOT_SALUATION, self.given_name)

    @property
    def opt_out_messages(self) -> bool:
        """Gets a value indicating whether this contact has opt out to receiving messages."""
        return self.metadata.get(CustomFields.BOT_OPT_OUT, "").casefold() in constants.TRUTHY

    def send_message(self) -> None:
        if self.opt_out_messages:
            return  # contact is opt-out

        saluation = self.saluation
        send_dates = (dt for dt in self.dates if dt.is_today())
        for dates in send_dates:
            messaging.sms.send_text(self.mobile_number, dates[0].format(saluation))


class ContactGroup(NamedTuple):
    name: str
    members: frozenset[str]

    def __repr__(self) -> str:
        return self.name


@unique
class CustomFields(str, Enum):
    BOT_SALUATION = "BOT_SALUATION"
    BOT_OPT_OUT = "BOT_OPT_OUT"


@unique
class SortOrder(str, Enum):
    LAST_MODIFIED_ASCENDING = "LAST_MODIFIED_ASCENDING"  # Sort people by when they were changed; older entries first.
    LAST_MODIFIED_DESCENDING = "LAST_MODIFIED_DESCENDING"  # Sort people by when they were changed; newer entries first.
    FIRST_NAME_ASCENDING = "FIRST_NAME_ASCENDING"  # Sort people by first name.
    LAST_NAME_ASCENDING = "LAST_NAME_ASCENDING"  # 	Sort people by last name.
