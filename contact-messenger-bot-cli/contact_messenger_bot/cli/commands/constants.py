from pathlib import Path
from typing import Final

CREDENTIALS_FILE: Final[Path] = Path(Path.cwd(), "credentials.json").resolve()

TOKEN_FILE: Final[Path] = Path(Path.cwd(), "token.json").resolve()

ZIP_CODE_CACHE_FILE: Final[Path] = Path(Path.cwd(), "zip_code_cache.json").resolve()

CONTACTS_SVC_CACHE_FILE: Final[Path] = Path(Path.cwd(), "contacts_svc_cache.pkl").resolve()

DATE_FMT: Final[str] = "%Y-%m-%d"
