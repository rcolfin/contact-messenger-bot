from pathlib import Path
from typing import Final

CREDENTIALS_FILE: Final[Path] = Path(Path.cwd(), "credentials.json").resolve()

TOKEN_FILE: Final[Path] = Path(Path.cwd(), "token.json").resolve()

ZIP_CODE_CACHE_FILE: Final[Path] = Path(Path.cwd(), "zip-code-cache.json").resolve()
