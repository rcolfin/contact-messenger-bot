import logging
from functools import cache
from typing import Final

import backoff
from twilio.rest import Client

from contact_messenger_bot.api.models import PhoneNumber
from contact_messenger_bot.api.settings import settings

logger = logging.getLogger(__name__)

MAX_RETRY: Final[int] = 2


@cache
def _get_client() -> Client:
    """Creates an instance of the Twilio Client"""
    # Find these values at https://twilio.com/user/account
    if not is_supported():
        raise ValueError

    assert settings.text is not None
    assert settings.text.auth is not None

    account_sid = settings.text.auth.account
    auth_token = settings.text.auth.token

    return Client(account_sid, auth_token)


@backoff.on_exception(backoff.expo, IOError, max_tries=MAX_RETRY)
def _send_text(client: Client, to: str, sender: str, body: str) -> None:
    client.api.account.messages.create(to=to, from_=sender, body=body)


def is_supported() -> bool:
    """Determines whether this messaging protocol is supported."""
    return bool(settings.text and settings.text.auth)


def send_message(sender: PhoneNumber, to: PhoneNumber, body: str, dry_run: bool) -> None:
    """Sends a text message to the recipient."""
    if is_supported():
        logger.warning("Text not supported")
        return

    if dry_run:
        logger.info("Sending message to=%s, from=%s, body=%s [dry-run]", to, sender, body)
        return

    assert settings.text is None
    client = _get_client()
    logger.info("Sending message to=%s, from=%s, body=%s", to, sender, body)
    _send_text(client, to.number, sender.number, body)
