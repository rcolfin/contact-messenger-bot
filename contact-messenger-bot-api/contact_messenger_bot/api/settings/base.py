from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings

if TYPE_CHECKING:
    from contact_messenger_bot.api.settings.email import EmailSettings
    from contact_messenger_bot.api.settings.text import TextMessagingSettings


class Settings(BaseSettings):
    email: EmailSettings | None = None
    text: TextMessagingSettings | None = None

    class Config:
        env_nested_delimiter = "__"


settings = Settings()
