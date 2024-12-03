from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeAlias

from contact_messenger_bot.api import constants, models, utils
from contact_messenger_bot.api.services.messaging import email, text

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterable


SendMessageRule: TypeAlias = Callable[[models.Profile, models.Contact, list[models.DateTuple], str], bool]

logger = logging.getLogger(__name__)


class Messaging:
    def __init__(self, profile: models.Profile, groups: list[str] | None = None) -> None:
        self.profile = profile
        self.groups = utils.to_frozen_set(groups)
        self._send_message = self._create_send_message()

    @staticmethod
    def supported_protocols() -> list[str]:
        """Gets the list of supported messaging protocols."""
        protocols = []
        if email.is_supported():
            protocols.append("email")
        if text.is_supported():
            protocols.append("text")
        return protocols

    def send_messages(self, contacts: Iterable[models.Contact], today: datetime.date | None = None) -> None:
        if not self.supported_protocols():
            logger.info("No protocols found.")
            return

        if self.groups:
            self._filter_contacts(contacts)
            if not contacts:
                logger.info("No contacts found in %s.", self.groups)
                return

        today = today or constants.TODAY
        for contact in contacts:
            self._send_message(self.profile, contact, today)

    def dry_run(self, contacts: Iterable[models.Contact]) -> None:
        if self.groups:
            self._filter_contacts(contacts)
            if not contacts:
                logger.info("No contacts found in %s.", self.groups)
                return

        for contact in contacts:
            if contact.opt_out_messages or not contact.dates:
                continue
            notifications = [
                n
                for n in (
                    contact.get_mobile_email_address(),
                    contact.get_us_mobile_number(),
                    contact.get_primary_email_address(),
                )
                if n
            ]
            if not notifications:
                continue
            logger.info(
                "Will send notifications to %s (%s) on %s, via [%s]",
                contact,
                contact.saluation,
                contact.dates,
                notifications,
            )

    @staticmethod
    def _create_send_message() -> Callable[[models.Profile, models.Contact, datetime.date], bool]:
        rules: list[SendMessageRule] = Messaging._create_send_message_rules()

        if rules:

            def apply(
                profile: models.Profile,
                contact: models.Contact,
                today: datetime.date,
            ) -> bool:
                if contact.opt_out_messages:
                    logger.info("%s opt-out.", contact)
                    return False  # contact is opt-out

                send_dates = [dt for dt in contact.dates if dt.is_today(today)]
                if not send_dates:
                    logger.info("%s has no applicable dates that match %s.", contact, today)
                    return False

                saluation = contact.saluation
                for rule in rules:
                    try:
                        if rule(profile, contact, send_dates, saluation):
                            return True
                    except Exception:  # noqa: PERF203
                        logger.exception("Failed to notify via %s.", rule)

                return False
        else:

            def apply(
                profile: models.Profile,
                contact: models.Contact,
                today: datetime.date,
            ) -> bool:
                logger.info("%s has no supported communication methods.")
                return False

        return apply

    @staticmethod
    def _create_send_message_rules() -> list[SendMessageRule]:
        rules: list[SendMessageRule] = []
        if email.is_supported():
            rules.append(Messaging._email_mobile_rule)

        if text.is_supported():
            rules.append(Messaging._text_rule)

        if email.is_supported():
            rules.append(Messaging._email_rule)

        return rules

    @staticmethod
    def _email_rule(
        profile: models.Profile, contact: models.Contact, send_dates: list[models.DateTuple], saluation: str
    ) -> bool:
        email_address = contact.get_primary_email_address()
        if not email_address:
            return False

        logger.debug("using %s", email_address)
        for dates in send_dates:
            email.send_message(
                profile,
                contact,
                email_address,
                dates[0].message(saluation),
                dates[0].subject(saluation),
            )

        return True

    @staticmethod
    def _email_mobile_rule(
        profile: models.Profile, contact: models.Contact, send_dates: list[models.DateTuple], saluation: str
    ) -> bool:
        mobile_email_address = contact.get_mobile_email_address()
        if not mobile_email_address:
            return False

        logger.debug("using %s", mobile_email_address)
        for dates in send_dates:
            email.send_message(profile, contact, mobile_email_address, dates[0].message(saluation))

        return True

    @staticmethod
    def _text_rule(
        profile: models.Profile, contact: models.Contact, send_dates: list[models.DateTuple], saluation: str
    ) -> bool:
        us_mobile_number = contact.get_us_mobile_number()
        if not us_mobile_number:
            return False

        logger.debug("using %s", us_mobile_number)
        for dates in send_dates:
            text.send_message(profile.mobile_number, us_mobile_number, dates[0].message(saluation))

        return True

    def _filter_contacts(self, contacts: Iterable[models.Contact]) -> list[models.Contact]:
        assert self.groups is not None
        return [c for c in contacts if c.is_member(self.groups)]
