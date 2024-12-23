from __future__ import annotations

import datetime
import logging
import pickle
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast

import backoff
import google.auth.exceptions
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from googleapiclient.http import HttpRequest

from contact_messenger_bot.api import constants, models, utils

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable

    from contact_messenger_bot.api import oauth2
    from contact_messenger_bot.api.services.zipcode import ZipCode


logger = logging.getLogger(__name__)


class Contacts:
    SCOPES: Final[list[str]] = [
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]
    CONTACT_FIELDS: Final[str] = (
        "names,nicknames,emailAddresses,phoneNumbers,birthdays,events,userDefined,addresses"  # see https://developers.google.com/people/api/rest/v1/people
    )
    PROFILE_FIELDS: Final[str] = (
        "names,emailAddresses,phoneNumbers"  # see https://developers.google.com/people/api/rest/v1/people
    )
    PEOPLE_API_RESOURCE: Final[str] = "people/me"
    MAX_PAGE_SIZE: Final[int] = 100
    BUILT_IN_GROUPS: Final[tuple[str, ...]] = ("all", "mycontacts")
    GROUP_FIELDS: Final[str] = "name,memberCount"

    def __init__(self, creds: oauth2.CredentialsManager, zipcode: ZipCode, cache: os.PathLike | None = None) -> None:
        self.creds = creds
        self.zipcode = zipcode
        self.cache = Path(cache) if cache else None

    def get_contacts(
        self, groups: Iterable[str] | None = None, load_cache: bool = True, save_cache: bool = True
    ) -> Iterable[models.Contact]:
        groups = utils.to_frozen_set(groups)
        if load_cache and self.cache is not None and self.cache.exists():
            contacts = self._load_cache()[1]
            if contacts is not None:
                if groups:
                    gcontacts = [c for c in contacts if c.is_member(groups)]
                    logger.debug(
                        "Filter on %s groups, reduced %d contacts to %d.", sorted(groups), len(contacts), len(gcontacts)
                    )
                    return gcontacts

                return contacts

        contacts = list(self._get_contacts(groups))
        if save_cache and groups is None and self.cache is not None:
            self._save_cache(contacts=contacts)
        return contacts

    def get_groups(self, groups: Iterable[str] | None = None) -> list[models.ContactGroup]:
        return list(self._get_groups(utils.to_frozen_set(groups)))

    def get_profile(self, load_cache: bool = True, save_cache: bool = True) -> models.Profile:
        if load_cache and self.cache is not None and self.cache.exists():
            profile = self._load_cache()[0]
            if profile is not None:
                return profile

        profile = self._get_profile()
        if save_cache and self.cache is not None:
            self._save_cache(profile=profile)
        return profile

    @backoff.on_exception(backoff.expo, google.auth.exceptions.RefreshError, max_tries=constants.MAX_RETRY)
    def _get_profile(self) -> models.Profile:
        resource = self._create_resource()
        profile = self._query_profile(resource, self.PROFILE_FIELDS)
        profile_name = self._get_name(profile)
        assert profile_name is not None
        mobile_number = next(filter(lambda x: x.is_primary, self._get_mobile_numbers(profile)))
        email_address = next(filter(lambda x: x.is_primary, self._get_email_addresses(profile)))
        return models.Profile(profile_name[0], profile_name[1], mobile_number, email_address)

    @backoff.on_exception(backoff.expo, google.auth.exceptions.RefreshError, max_tries=constants.MAX_RETRY)
    def _get_contacts(self, interested_groups: frozenset[str] | None = None) -> Iterable[models.Contact]:
        resource = self._create_resource()
        groups = self._query_groups(resource, interested_groups)
        contacts = self._query_contacts(resource, self.CONTACT_FIELDS)
        for contact in contacts:
            resource_name = contact["resourceName"]
            membership = [g.name for g in groups if resource_name in g.members]
            if interested_groups is not None and not membership:
                continue  # This contact is not a member of any of the Groups.

            name = self._get_name(contact)
            if name is None:
                continue

            given_name, display_name = name

            logger.debug("Processing %s...", display_name)

            nickname = self._get_nickname(contact)
            home_addresses = self._get_home_addresses(contact)
            mobile_numbers = self._get_mobile_numbers(contact)
            email_addresses = self._get_email_addresses(contact)
            dates = self._get_dates(contact)
            metadata = {ud["key"]: ud["value"] for ud in contact["userDefined"]} if "userDefined" in contact else {}
            yield models.Contact(
                given_name,
                display_name,
                nickname,
                mobile_numbers,
                dates,
                home_addresses,
                email_addresses,
                membership,
                metadata,
            )

    @backoff.on_exception(backoff.expo, google.auth.exceptions.RefreshError, max_tries=constants.MAX_RETRY)
    def _get_groups(self, interested_groups: frozenset[str] | None) -> list[models.ContactGroup]:
        resource = self._create_resource()
        return self._query_groups(resource, interested_groups)

    @backoff.on_exception(backoff.expo, AttributeError, max_tries=constants.MAX_RETRY)
    def _create_resource(self) -> Resource:
        return build(
            "people", "v1", credentials=self.creds.create_oauth_credentials(self.SCOPES), cache_discovery=False
        )

    def _query_profile(self, resource: Resource, fields: str) -> dict[str, Any]:
        return resource.people().get(resourceName=self.PEOPLE_API_RESOURCE, personFields=fields).execute()

    def _query_contacts(self, resource: Resource, fields: str) -> Iterable[dict[str, Any]]:
        return self._get_pages(
            resource.people().connections(),
            "connections",
            resourceName=self.PEOPLE_API_RESOURCE,
            pageSize=self.MAX_PAGE_SIZE,
            personFields=fields,
            sortOrder=models.SortOrder.FIRST_NAME_ASCENDING.value,
        )

    def _query_groups(self, resource: Resource, interested_groups: frozenset[str] | None) -> list[models.ContactGroup]:
        def get() -> Iterable[models.ContactGroup]:
            groups = self._get_pages(
                resource.contactGroups(), "contactGroups", pageSize=self.MAX_PAGE_SIZE, groupFields=self.GROUP_FIELDS
            )

            for group in groups:
                member_count = cast(int, group.get("memberCount", 0))
                if member_count < 1:
                    continue

                name = cast(str, group["name"])
                if name.casefold() in self.BUILT_IN_GROUPS:
                    continue  # ignore
                if interested_groups is not None:
                    if name.casefold() not in interested_groups:
                        continue  # ignore

                member_request = resource.contactGroups().get(
                    resourceName=group["resourceName"], maxMembers=member_count
                )
                resp = self._execute_with_retry(member_request)
                members = resp.get("memberResourceNames", [])
                assert len(members) == member_count
                yield models.ContactGroup(name, frozenset(members))

        return sorted(get(), key=lambda x: x.name)

    @staticmethod
    def _is_primary(container: dict[str, Any], field: str = "primary") -> bool:
        return container.get("metadata", {}).get(field, False)

    @staticmethod
    @backoff.on_exception(backoff.expo, HttpError, max_tries=constants.MAX_RETRY)
    def _execute_with_retry(request: HttpRequest) -> dict[str, Any]:
        return request.execute()

    def _get_pages(self, resource: Resource, select_key: str, **kwargs: Any) -> Iterable[Any]:  # noqa: ANN401
        try:
            next_page_token: str | None = None
            start_idx = 0
            page_count = 1
            while True:
                request = cast(
                    HttpRequest,
                    resource.list(
                        pageToken=next_page_token,
                        **kwargs,
                    ),
                )

                results = self._execute_with_retry(request)
                values = cast(list[dict[str, Any]], results.get(select_key, []))

                total_len = start_idx + len(values)
                logger.debug("Page: %d (%d-%d %s)", page_count, start_idx, total_len, select_key)

                yield from values

                next_page_token = results.get("nextPageToken")
                if next_page_token is None:
                    break

                start_idx = total_len
                page_count += 1
        except google.auth.exceptions.RefreshError:
            logger.exception("Token failed to be refreshed", exc_info=False)
            self.creds.invalidate_token()
            raise

    def _get_mobile_numbers(self, contact: dict[str, Any]) -> list[models.PhoneNumber]:
        mobile_numbers: list[models.PhoneNumber] = []
        for number in contact.get("phoneNumbers", []):
            if number.get("type", "").casefold() != constants.MOBILE_LABEL:
                continue

            primary = self._is_primary(number)
            contact_number = number.get("canonicalForm")
            if contact_number is None:
                display_name = cast(tuple[str, str], self._get_name(contact))[1]
                logger.warning("%s has no canonical phone number.", display_name)
                return number["value"].replace(" ", "")

            mobile_numbers.append(models.PhoneNumber(contact_number, primary))

        return mobile_numbers

    def _get_home_addresses(self, contact: dict[str, Any]) -> list[models.Address]:
        return [
            models.Address(address["postalCode"], self.zipcode.get_timezone(models.Country.US, address["postalCode"]))
            for address in contact.get("addresses", [])
            if address.get("postalCode") and address.get("type", "").casefold() == constants.HOME_LABEL
        ]

    def _get_email_addresses(self, contact: dict[str, Any]) -> list[models.EmailAddress]:
        addresses: list[models.EmailAddress] = []
        for email_addresses in contact.get("emailAddresses", []):
            email_address_type = email_addresses.get("type", "").casefold()
            if email_address_type not in (constants.EMAIL_ADDRESS_LABELS):
                continue

            primary = self._is_primary(email_addresses)
            address = email_addresses.get("value")
            is_phone = email_address_type in constants.MOBILE_LABELS
            addresses.append(models.EmailAddress(address, primary, is_phone))

        return addresses

    def _get_name(self, contact: dict[str, Any]) -> tuple[str, str] | None:
        if "names" not in contact:
            return None

        given_name, display_name = next(
            ((n.get("givenName"), n.get("displayName")) for n in contact["names"]),
            (None, None),
        )

        if display_name is None:
            return None

        if given_name is None:
            given_name = display_name.split(" ")[0]
            logger.warning("Defaulting %s (no given name) from %s.", given_name, display_name)

        return given_name.strip(), display_name.strip()

    def _get_nickname(self, contact: dict[str, Any]) -> str | None:
        if "nicknames" not in contact:
            return None

        primary_nicknames = (n["value"].strip() for n in contact.get("nicknames", []) if self._is_primary(n))
        return next(primary_nicknames, None)

    def _convert_date(self, date: dict[str, int]) -> datetime.date:
        year = date.get("year")
        if year is None:
            logger.debug("year is not present in %s", date)
            year = constants.TODAY.year

        return datetime.date(year, date["month"], date["day"])

    def _get_dates(self, contact: dict[str, Any]) -> list[models.DateTuple]:
        results: list[models.DateTuple] = []

        results.extend(
            models.DateTuple(models.DateType.BIRTHDAY, self._convert_date(bd["date"]))
            for bd in contact.get("birthdays", [])
            if "date" in bd and self._is_primary(bd)
        )

        results.extend(
            models.DateTuple(models.DateType.ANNIVERSARY, self._convert_date(e["date"]))
            for e in contact.get("events", [])
            if e["type"] == "anniversary"
        )

        return results

    def _save_cache(
        self,
        profile: models.Profile | None = None,
        contacts: list[models.Contact] | None = None,
    ) -> None:
        self._assert_cache_supported()
        assert self.cache is not None

        if profile is None and contacts is None:
            return  # Nothing to persist.

        payload: dict[str, Any] = {}
        if self.cache.exists():
            cache_profile, cache_contacts = self._load_cache()
            if profile is None:
                profile = cache_profile
            if contacts is None:
                contacts = cache_contacts

        if profile is not None:
            payload["profile"] = profile

        if contacts is not None:
            payload["contacts"] = list(contacts)

        logger.info("Saving %s", self.cache)
        with self.cache.open(mode="wb") as f:
            pickle.dump(payload, f)

    def _load_cache(self) -> tuple[models.Profile | None, list[models.Contact] | None]:
        self._assert_cache_supported()
        assert self.cache is not None

        if not self.cache.is_file():
            return None, None

        logger.info("Loading %s", self.cache)
        with self.cache.open(mode="rb") as f:
            payload = pickle.load(f)  # noqa: S301

        return payload.get("profile"), payload.get("contacts")

    def _assert_cache_supported(self) -> None:
        if self.cache is None:
            msg = "Cache not supported"
            raise ValueError(msg)
