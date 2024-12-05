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

    def send_message(self) -> None:
        send_dates = (dt for dt in self.dates if dt.is_today())
        for dates in send_dates:
            messaging.sms.send_text(self.mobile_number, dates[0].format(self.given_name))
