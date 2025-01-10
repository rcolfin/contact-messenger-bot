from __future__ import annotations

from pydantic_settings import BaseSettings

from contact_messenger_bot.api.settings.email import EmailSettings  # noqa: TC001
from contact_messenger_bot.api.settings.text import TextMessagingSettings  # noqa: TC001


class Settings(BaseSettings):
    email: EmailSettings | None = None
    text: TextMessagingSettings | None = None

    class Config:
        env_nested_delimiter = "__"


settings = Settings()
