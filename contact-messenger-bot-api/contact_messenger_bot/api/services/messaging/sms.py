import logging
import os
from functools import cache
from typing import Final

import backoff
from twilio.rest import Client

logger = logging.getLogger(__name__)

MAX_RETRY: Final[int] = 2


@cache
def _get_client() -> Client:
    """Creates an instance of the Twilio Client"""
    # Find these values at https://twilio.com/user/account
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]

    return Client(account_sid, auth_token)


@backoff.on_exception(backoff.expo, IOError, max_tries=MAX_RETRY)
def _send_text(client: Client, to: str, sender: str, body: str) -> None:
    client.api.account.messages.create(to=to, from_=sender, body=body)


def send_text(to: str, body: str) -> None:
    """Sends a text message to the recipient."""
    sender = os.environ["SMS_SENDER_NUMBER"]
    client = _get_client()
    logger.info("Sending message to=%s, from=%s, body=%s", to, sender, body)
    _send_text(client, to, sender, body)
