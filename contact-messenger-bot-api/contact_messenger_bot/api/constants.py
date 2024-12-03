import datetime
from typing import Final

MAX_RETRY: Final[int] = 2

TODAY: Final[datetime.date] = datetime.datetime.now(tz=datetime.UTC).date()

TRUTHY: Final[frozenset[str]] = frozenset(["true", "1"])
