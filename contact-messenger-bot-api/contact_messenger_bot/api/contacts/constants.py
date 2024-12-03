# If modifying these scopes, delete the file token.json.
from pathlib import Path
from typing import Final

SCOPES: Final[list[str]] = ["https://www.googleapis.com/auth/contacts.readonly"]
CREDENTIALS_FILE: Final[Path] = Path(Path.cwd(), "credentials.json").resolve()
TOKEN_FILE: Final[Path] = Path(Path.cwd(), "token.json").resolve()
FIELDS: Final[str] = "names,emailAddresses,phoneNumbers,birthdays,events"
MAX_PAGE_SIZE: Final[int] = 10
MAX_RETRY: Final[int] = 2
