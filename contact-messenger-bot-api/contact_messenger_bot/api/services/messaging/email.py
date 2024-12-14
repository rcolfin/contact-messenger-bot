from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import TYPE_CHECKING, Final

from contact_messenger_bot.api.models import EmailAddress
from contact_messenger_bot.api.settings import settings

if TYPE_CHECKING:
    from contact_messenger_bot.api.models import Contact, Profile

logger = logging.getLogger(__name__)

MAILBOX_FMT: Final[str] = "{DISPLAY_NAME} <{EMAIL_ADDRESS}>"


def is_supported() -> bool:
    """Determines whether this messaging protocol is supported."""
    return bool(settings.email)


def send_message(  # noqa: PLR0913
    sender: Profile,
    recipient: Contact,
    addresses: EmailAddress | list[EmailAddress],
    body: str,
    subject: str | None = None,
    dry_run: bool = False,
) -> None:
    if not is_supported():
        logger.warning("Email not supported")
        return  # not supported

    msg = _create_message(sender, recipient, addresses, body, subject)
    if dry_run:
        logger.info("Sending email [dry-run]:\n%s", msg)
        return

    _send_message(msg)


def _send_message(msg: MIMEMultipart) -> None:
    assert settings.email is not None
    logger.debug("Connecting to %s:%d", settings.email.host, settings.email.port)
    with smtplib.SMTP(settings.email.host, settings.email.port) as s:
        if settings.email.auth:
            logger.debug("Authenticating as %s", settings.email.auth.user)
            s.starttls()
            s.login(settings.email.auth.user, settings.email.auth.password)

        logger.info("Sending email:\n%s", msg)
        s.send_message(msg)


def _create_message(
    sender: Profile,
    recipient: Contact,
    addresses: EmailAddress | list[EmailAddress],
    body: str,
    subject: str | None = None,
) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    if subject is not None:
        msg["Subject"] = subject
    msg["Bcc"] = msg["From"] = formataddr((sender.display_name, sender.email_address.address))
    if isinstance(addresses, EmailAddress):
        msg["To"] = formataddr((recipient.display_name, addresses.address))
    else:
        to = (formataddr((recipient.display_name, addr.address)) for addr in addresses)
        msg["To"] = ",".join(to)

    msg.attach(MIMEText(body, "plain"))
    return msg
