from __future__ import annotations

from pydantic import BaseModel, Field


class TextMessagingAuth(BaseModel):
    account: str = Field(title="The server authentication user")
    token: str = Field(title="The server authentication token")


class TextMessagingSettings(BaseModel):
    sender: str = Field(title="The text messenger sender")
    auth: TextMessagingAuth | None = None
