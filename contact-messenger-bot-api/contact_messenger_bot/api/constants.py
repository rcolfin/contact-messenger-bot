import datetime
from typing import Final

MAX_RETRY: Final[int] = 2

HOME_LABEL: Final[str] = "home"
PHONE_LABEL: Final[str] = "phone"
MOBILE_LABEL: Final[str] = "mobile"

TODAY: Final[datetime.date] = datetime.datetime.now(tz=datetime.UTC).date()

TRUTHY: Final[frozenset[str]] = frozenset(["true", "1"])

EMAIL_ADDRESS_LABELS: Final[frozenset[str]] = frozenset([HOME_LABEL, MOBILE_LABEL, PHONE_LABEL])

MOBILE_LABELS: Final[frozenset[str]] = frozenset([MOBILE_LABEL, PHONE_LABEL])

APP_NAME: Final[str] = "contact-message-bot"
