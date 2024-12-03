import datetime
import random
from enum import IntEnum, auto
from typing import Final, NamedTuple

from .messages import anniversary, birthday

_RANDOM: Final[random.Random] = random.Random()  # noqa: S311


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


class Contact(NamedTuple):
    given_name: str
    display_name: str
    mobile_number: str
    dates: list[DateTuple]
