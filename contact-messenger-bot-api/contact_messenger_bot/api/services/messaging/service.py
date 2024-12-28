from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeAlias

import structlog

from contact_messenger_bot.api import constants, models, utils
from contact_messenger_bot.api.services.messaging import email, text

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterable


SendMessageRule: TypeAlias = Callable[[models.Profile, models.Contact, list[models.DateTuple], str, bool], bool]

logger = structlog.get_logger(__name__)


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

    def send_messages(
        self, contacts: Iterable[models.Contact], date: datetime.date | None = None, dry_run: bool = False
    ) -> None:
        if not self.supported_protocols():
            logger.info("No protocols found.")
            return

        if self.groups:
            self._filter_contacts(contacts)
            if not contacts:
                logger.info("No contacts found.", groups=self.groups)
                return

        date = date or constants.TODAY
        for contact in contacts:
            self._send_message(self.profile, contact, date, dry_run)

    def dry_run(self, contacts: Iterable[models.Contact]) -> None:
        if self.groups:
            self._filter_contacts(contacts)
            if not contacts:
                logger.info("No contacts found.", groups=self.groups)
                return

        for contact in contacts:
            if contact.opt_out_messages or not contact.dates:
                continue
            notifications = [
                n
                for n in (
                    contact.get_primary_mobile_email_address(),
                    contact.get_us_mobile_number(),
                    contact.get_primary_email_address(),
                    contact.get_all_mobile_email_addresses(),
                )
                if n
            ]
            if not notifications:
                continue
            logger.info(
                "Will send notifications",
                contact=str(contact),
                saluation=contact.saluation,
                dates=contact.dates,
                notifications=notifications,
            )

    @staticmethod
    def _create_send_message() -> Callable[[models.Profile, models.Contact, datetime.date, bool], bool]:
        rules: list[SendMessageRule] = Messaging._create_send_message_rules()

        if rules:

            def apply(
                profile: models.Profile,
                contact: models.Contact,
                date: datetime.date,
                dry_run: bool,
            ) -> bool:
                if contact.opt_out_messages:
                    logger.debug("Contact has opt-out.", contact=contact)
                    return False  # contact is opt-out

                send_dates = [dt for dt in contact.dates if dt.is_today(date)]
                if not send_dates:
                    logger.debug("Contact has no applicable dates.", contact=str(contact), date=date.isoformat())
                    return False

                logger.info(
                    "Contact has the following events.",
                    contact=str(contact),
                    events=[str(x.type) for x in send_dates],
                    date=date.isoformat(),
                )
                saluation = contact.saluation
                for rule in rules:
                    try:
                        if rule(profile, contact, send_dates, saluation, dry_run):
                            return True
                    except Exception:  # noqa: PERF203
                        logger.exception("Failed to notify.", contact=str(contact), rule=rule)

                return False
        else:

            def apply(
                profile: models.Profile,
                contact: models.Contact,
                date: datetime.date,
                dry_run: bool,
            ) -> bool:
                logger.info("No supported communication methods.", contact=contact)
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
            rules.append(Messaging._email_mobile_wide_rule)
            rules.append(Messaging._email_rule)

        return rules

    @staticmethod
    def _email_rule(
        profile: models.Profile,
        contact: models.Contact,
        send_dates: list[models.DateTuple],
        saluation: str,
        dry_run: bool,
    ) -> bool:
        email_address = contact.get_primary_email_address()
        if not email_address:
            return False

        logger.debug("Using", email=email_address)
        for dates in send_dates:
            email.send_message(
                profile,
                contact,
                email_address,
                dates[0].message(saluation),
                dates[0].subject(saluation),
                dry_run=dry_run,
            )

        return True

    @staticmethod
    def _email_mobile_rule(
        profile: models.Profile,
        contact: models.Contact,
        send_dates: list[models.DateTuple],
        saluation: str,
        dry_run: bool,
    ) -> bool:
        mobile_email_address = contact.get_primary_mobile_email_address()
        if not mobile_email_address:
            return False

        logger.debug("Using", email=mobile_email_address)
        for dates in send_dates:
            email.send_message(profile, contact, mobile_email_address, dates[0].message(saluation), dry_run=dry_run)

        return True

    @staticmethod
    def _email_mobile_wide_rule(
        profile: models.Profile,
        contact: models.Contact,
        send_dates: list[models.DateTuple],
        saluation: str,
        dry_run: bool,
    ) -> bool:
        all_mobile_email_addresses = contact.get_all_mobile_email_addresses()
        if not all_mobile_email_addresses:
            return False

        logger.debug("Using", email=all_mobile_email_addresses)
        for dates in send_dates:
            email.send_message(
                profile, contact, all_mobile_email_addresses, dates[0].message(saluation), dry_run=dry_run
            )

        return True

    @staticmethod
    def _text_rule(
        profile: models.Profile,
        contact: models.Contact,
        send_dates: list[models.DateTuple],
        saluation: str,
        dry_run: bool,
    ) -> bool:
        us_mobile_number = contact.get_us_mobile_number()
        if not us_mobile_number:
            return False

        logger.debug("Using", email=us_mobile_number)
        for dates in send_dates:
            text.send_message(profile.mobile_number, us_mobile_number, dates[0].message(saluation), dry_run=dry_run)

        return True

    def _filter_contacts(self, contacts: Iterable[models.Contact]) -> list[models.Contact]:
        assert self.groups is not None
        return [c for c in contacts if c.is_member(self.groups)]
