from pathlib import Path
from typing import Final

GCS_BUCKET: Final[str] = "contact-messenger-4ed7624155de0493"

TOKEN_FILE: Final[str] = "token.json"
CREDENTIALS_FILE: Final[str] = "credentials.json"

ALL_INTERFACES: Final[str] = "0.0.0.0"  # noqa: S104

DEFAULT_PORT: Final[int] = 8080

FUSE_SECRETS_VOLUME: Final[Path] = Path("/var/secrets")
FUSE_SECRETS_TOKEN_FILE: Final[Path] = Path(FUSE_SECRETS_VOLUME, TOKEN_FILE)
FUSE_SECRETS_CREDENTIALS_FILE: Final[Path] = Path(FUSE_SECRETS_VOLUME, CREDENTIALS_FILE)
