from __future__ import annotations

from pydantic import BaseModel, Field


class EmailAuth(BaseModel):
    user: str = Field(title="The server authentication user")
    password: str = Field(title="The server authentication password")


class EmailSettings(BaseModel):
    host: str = Field("localhost", title="The SMTP server host")
    port: int = Field(587, title="The SMTP server port")
    auth: EmailAuth | None = None
