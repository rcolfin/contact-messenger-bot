import os
from pathlib import Path
from typing import Final

GCS_BUCKET: Final[str] = "contact-messenger-4ed7624155de0493"

TOKEN_FILE: Final[str] = "token.json"  # noqa: S105
CREDENTIALS_FILE: Final[str] = "credentials.json"
ZIP_CODE_CACHE_FILE: Final[str] = "zip_code_cache.json"
CONTACTS_SVC_CACHE_FILE: Final[str] = "contacts_svc_cache.pkl"

ALL_INTERFACES: Final[str] = "0.0.0.0"  # noqa: S104

DEFAULT_PORT: Final[int] = 8080

FUSE_SECRETS_VOLUME: Final[Path] = Path(os.getenv("FUSE_SECRETS_VOLUME", "/var/secrets"))
FUSE_SECRETS_TOKEN_FILE: Final[Path] = Path(FUSE_SECRETS_VOLUME, TOKEN_FILE)
FUSE_SECRETS_CREDENTIALS_FILE: Final[Path] = Path(FUSE_SECRETS_VOLUME, CREDENTIALS_FILE)
FUSE_SECRETS_CONTACTS_SVC_CACHE_FILE: Final[Path] = Path(FUSE_SECRETS_VOLUME, CONTACTS_SVC_CACHE_FILE)

DATE_FMT: Final[str] = "%Y-%m-%d"
