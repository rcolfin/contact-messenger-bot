from __future__ import annotations

import importlib.metadata

from contact_messenger_bot.api import contacts, messaging

# set the version number within the package using importlib
try:
    __version__: str | None = importlib.metadata.version("contact-messenger-bot-api")
except importlib.metadata.PackageNotFoundError:
    # package is not installed
    __version__ = None


__all__ = ["__version__", "contacts", "messaging"]
