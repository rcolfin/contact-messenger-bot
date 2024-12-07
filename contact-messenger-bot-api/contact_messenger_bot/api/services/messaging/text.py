import logging
from functools import cache
from typing import Final

import backoff
from twilio.rest import Client

from contact_messenger_bot.api.settings import settings

logger = logging.getLogger(__name__)

MAX_RETRY: Final[int] = 2


@cache
def _get_client() -> Client:
    """Creates an instance of the Twilio Client"""
    # Find these values at https://twilio.com/user/account
    if settings.text is None or settings.text.auth is None:
        raise ValueError

    account_sid = settings.text.auth.account
    auth_token = settings.text.auth.token

    return Client(account_sid, auth_token)


@backoff.on_exception(backoff.expo, IOError, max_tries=MAX_RETRY)
def _send_text(client: Client, to: str, sender: str, body: str) -> None:
    client.api.account.messages.create(to=to, from_=sender, body=body)


def send_message(to: str, body: str) -> None:
    """Sends a text message to the recipient."""
    if settings.text is None:
        return  # not supported

    sender = settings.text.sender
    client = _get_client()
    logger.info("Sending message to=%s, from=%s, body=%s", to, sender, body)
    _send_text(client, to, sender, body)
