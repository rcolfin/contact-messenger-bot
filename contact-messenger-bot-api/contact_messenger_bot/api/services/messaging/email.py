from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

from contact_messenger_bot.api.settings import settings

if TYPE_CHECKING:
    from contact_messenger_bot.api.models import EmailAddress

logger = logging.getLogger(__name__)


def is_supported() -> bool:
    """Determines whether this messaging protocol is supported."""
    return bool(settings.email)


def send_message(sender: EmailAddress, recipient: EmailAddress, body: str, subject: str | None = None) -> None:
    if not is_supported():
        logger.warning("Email not supported")
        return  # not supported

    assert settings.email is not None
    sender_email = sender.address
    receiver_email = recipient.address

    msg = MIMEMultipart("alternative")
    if subject is not None:
        msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(settings.email.host, settings.email.port) as s:
        if settings.email.auth:
            logger.debug("Authenticating as %s", settings.email.auth.user)
            s.starttls()
            s.login(settings.email.auth.user, settings.email.auth.password)

        logger.info("Sending email:\n%s", msg)
        s.send_message(msg)
