from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from contact_messenger_bot.api import constants
from contact_messenger_bot.api.services.messaging import email, text

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterable

    from contact_messenger_bot.api import models


logger = logging.getLogger(__name__)


class Messaging:
    def __init__(
        self, profile: models.Profile, today: datetime.date | None = None, groups: list[str] | None = None
    ) -> None:
        self.profile = profile
        self.today = today or constants.TODAY
        self.groups = frozenset(groups) if groups else None

    def send_messages(self, contacts: Iterable[models.Contact]) -> None:
        if self.groups:
            contacts = (c for c in contacts if any(x.name in self.groups for x in c.groups))

        for contact in contacts:
            logger.info(contact)
            self._send_message(contact)

    def _send_message(self, contact: models.Contact) -> None:
        try:
            if contact.opt_out_messages:
                logger.debug("%s opt-out.", contact)
                return  # contact is opt-out

            send_dates = [dt for dt in contact.dates if dt.is_today(self.today)]
            if not send_dates:
                logger.debug("%s has no send-dates.", contact)
                return

            saluation = contact.saluation
            mobile_email_address = contact.get_mobile_email_address()
            if mobile_email_address:
                logger.info("using %s", mobile_email_address)
                for dates in send_dates:
                    email.send_message(self.profile.email_address, mobile_email_address, dates[0].message(saluation))
            else:
                us_mobile_number = contact.get_us_mobile_number()
                if us_mobile_number:
                    logger.info("using %s", us_mobile_number)
                    for dates in send_dates:
                        text.send_message(self.profile.mobile_number, us_mobile_number, dates[0].message(saluation))
                else:
                    email_address = contact.get_primary_email_address()
                    if email_address:
                        logger.info("using %s", email_address)
                        for dates in send_dates:
                            email.send_message(
                                self.profile.email_address,
                                email_address,
                                dates[0].message(saluation),
                                dates[0].subject(saluation),
                            )
        except Exception:
            logger.exception("Failed to send message in %s.", contact)
