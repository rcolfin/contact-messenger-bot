from __future__ import annotations

import datetime
import pickle
from functools import cached_property
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast

import google.auth.exceptions
import structlog
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from tenacity import retry, retry_if_exception_cause_type, retry_if_exception_type, stop_after_attempt, wait_exponential

from contact_messenger_bot.api import constants, models, utils

if TYPE_CHECKING:
    import os
    from collections.abc import Callable, Iterable

    from googleapiclient.http import HttpRequest

    from contact_messenger_bot.api import oauth2
    from contact_messenger_bot.api.services.zipcode import ZipCode


logger = structlog.get_logger(__name__)


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
        self._cache: tuple[models.Profile | None, list[models.Contact] | None] | None = None

    def get_contacts(
        self, groups: Iterable[str] | None = None, load_cache: bool = True, save_cache: bool = True
    ) -> Iterable[models.Contact]:
        groups = utils.to_frozen_set(groups)
        if load_cache and self.cache is not None and self.cache.exists():
            contacts = self._get_cache()[1]
            if contacts is not None:
                if groups:
                    gcontacts = [c for c in contacts if c.is_member(groups)]
                    logger.debug("Filter applied", groups=sorted(groups), length=len(contacts), filtered=len(gcontacts))
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
            profile = self._get_cache()[0]
            if profile is not None:
                return profile

        profile = self._get_profile()
        if save_cache and self.cache is not None:
            self._save_cache(profile=profile)
        return profile

    @retry(
        retry=retry_if_exception_type(google.auth.exceptions.RefreshError),
        wait=wait_exponential(),
        stop=stop_after_attempt(constants.MAX_RETRY),
    )
    def _get_profile(self) -> models.Profile:
        profile = self._query_profile(self.PROFILE_FIELDS)
        profile_name = self._get_name(profile)
        assert profile_name is not None
        mobile_number = next(filter(lambda x: x.is_primary, self._get_mobile_numbers(profile)))
        email_address = next(filter(lambda x: x.is_primary, self._get_email_addresses(profile)))
        return models.Profile(profile_name[0], profile_name[1], mobile_number, email_address)

    @retry(
        retry=retry_if_exception_type(google.auth.exceptions.RefreshError),
        wait=wait_exponential(),
        stop=stop_after_attempt(constants.MAX_RETRY),
    )
    def _get_contacts(self, interested_groups: frozenset[str] | None = None) -> Iterable[models.Contact]:
        groups = self._query_groups(interested_groups)
        contacts = self._query_contacts(self.CONTACT_FIELDS)
        for contact in contacts:
            resource_name = contact["resourceName"]
            membership = [g.name for g in groups if resource_name in g.members]
            if interested_groups is not None and not membership:
                continue  # This contact is not a member of any of the Groups.

            name = self._get_name(contact)
            if name is None:
                continue

            given_name, display_name = name

            logger.debug("Processing", contact=display_name)

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

    @retry(
        retry=retry_if_exception_type(google.auth.exceptions.RefreshError),
        wait=wait_exponential(),
        stop=stop_after_attempt(constants.MAX_RETRY),
    )
    def _get_groups(self, interested_groups: frozenset[str] | None) -> list[models.ContactGroup]:
        return self._query_groups(interested_groups)

    @cached_property
    @retry(
        retry=retry_if_exception_type(AttributeError),
        wait=wait_exponential(),
        stop=stop_after_attempt(constants.MAX_RETRY),
    )
    def _resource(self) -> Resource:
        logger.debug("Creating Resource")
        credentials = self.creds.create_oauth_credentials(self.SCOPES)
        return build("people", "v1", credentials=credentials, cache_discovery=False)

    def _reset_resource(self) -> None:
        logger.debug("Resetting resource.")
        self.__dict__.pop("_resource", None)
        self.creds.invalidate_token()

    def _query_profile(self, fields: str) -> dict[str, Any]:
        return self._execute_with_retry(
            lambda resource: resource.people().get(resourceName=self.PEOPLE_API_RESOURCE, personFields=fields)
        )

    def _query_contacts(self, fields: str) -> Iterable[dict[str, Any]]:
        return self._get_pages(
            lambda resource: resource.people().connections(),
            "connections",
            resourceName=self.PEOPLE_API_RESOURCE,
            pageSize=self.MAX_PAGE_SIZE,
            personFields=fields,
            sortOrder=models.SortOrder.FIRST_NAME_ASCENDING.value,
        )

    def _query_groups(self, interested_groups: frozenset[str] | None) -> list[models.ContactGroup]:
        def get() -> Iterable[models.ContactGroup]:
            groups = self._get_pages(
                lambda resource: resource.contactGroups(),
                "contactGroups",
                pageSize=self.MAX_PAGE_SIZE,
                groupFields=self.GROUP_FIELDS,
            )

            for group in groups:
                member_count = cast("int", group.get("memberCount", 0))
                if member_count < 1:
                    continue

                name = cast("str", group["name"])
                if name.casefold() in self.BUILT_IN_GROUPS:
                    continue  # ignore
                if interested_groups is not None:
                    if name.casefold() not in interested_groups:
                        continue  # ignore

                def get_request(
                    resource: Resource, group: str = group["resourceName"], member_count: int = member_count
                ) -> HttpRequest:
                    return resource.contactGroups().get(resourceName=group, maxMembers=member_count)

                resp = self._execute_with_retry(get_request)
                members = resp.get("memberResourceNames", [])
                assert len(members) == member_count
                yield models.ContactGroup(name, frozenset(members))

        return sorted(get(), key=lambda x: x.name)

    @staticmethod
    def _is_primary(container: dict[str, Any], field: str = "primary") -> bool:
        return container.get("metadata", {}).get(field, False)

    @retry(
        retry=retry_if_exception_cause_type((google.auth.exceptions.RefreshError, HttpError)),
        wait=wait_exponential(),
        stop=stop_after_attempt(constants.MAX_RETRY),
    )
    def _execute_with_retry(self, request_factory: Callable[[Resource], HttpRequest]) -> dict[str, Any]:
        try:
            return request_factory(self._resource).execute()
        except HttpError as e:
            if e.status_code == HTTPStatus.FORBIDDEN:
                logger.exception("Token failed to be refreshed", exc_info=False)
                self._reset_resource()
            raise
        except google.auth.exceptions.RefreshError:
            logger.exception("Token failed to be refreshed", exc_info=False)
            self._reset_resource()
            raise

    def _get_pages(self, get_resource: Callable[[Resource], Resource], select_key: str, **kwargs: Any) -> Iterable[Any]:  # noqa: ANN401
        next_page_token: str | None = None
        start_idx = 0
        page_count = 1
        while True:
            request: dict[str, Any] = {"pageToken": next_page_token, **kwargs}

            def get_request(resource: Resource, request: dict[str, Any] = request) -> HttpRequest:
                return get_resource(resource).list(**request)

            results = self._execute_with_retry(get_request)
            values = cast("list[dict[str, Any]]", results.get(select_key, []))

            total_len = start_idx + len(values)
            logger.debug("Page", page=page_count, start=start_idx, length=total_len, key=select_key)

            yield from values

            next_page_token = results.get("nextPageToken")
            if next_page_token is None:
                break

            start_idx = total_len
            page_count += 1

    def _get_mobile_numbers(self, contact: dict[str, Any]) -> list[models.PhoneNumber]:
        mobile_numbers: list[models.PhoneNumber] = []
        for number in contact.get("phoneNumbers", []):
            if number.get("type", "").casefold() not in (constants.MOBILE_LABEL, constants.BOT_LABEL):
                continue

            primary = self._is_primary(number)
            is_bot = number.get("type", "").casefold() == constants.BOT_LABEL
            contact_number = number.get("canonicalForm")
            if contact_number is None:
                display_name = cast("tuple[str, str]", self._get_name(contact))[1]
                logger.warning("No canonical phone number.", contact=display_name)
                contact_number = number["value"].replace(" ", "")

            mobile_numbers.append(models.PhoneNumber(contact_number, primary, is_bot))

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
            is_bot = email_address_type in constants.BOT_LABEL
            addresses.append(models.EmailAddress(address, primary, is_phone, is_bot))

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
            logger.warning("Defaulting (no given name)", selected=given_name, contact=display_name)

        return given_name.strip(), display_name.strip()

    def _get_nickname(self, contact: dict[str, Any]) -> str | None:
        if "nicknames" not in contact:
            return None

        primary_nicknames = (n["value"].strip() for n in contact.get("nicknames", []) if self._is_primary(n))
        return next(primary_nicknames, None)

    def _convert_date(self, date: dict[str, int]) -> datetime.date:
        year = date.get("year")
        if year is None:
            logger.debug("Year is not present", date=date)
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
            cache_profile, cache_contacts = self._get_cache()
            if profile is None:
                profile = cache_profile
            if contacts is None:
                contacts = cache_contacts

        if profile is not None:
            payload["profile"] = profile

        if contacts is not None:
            payload["contacts"] = contacts

        # Persist the updated cache:
        self._cache = profile, contacts

        logger.info("Saving", file=str(self.cache))
        with self.cache.open(mode="wb") as f:
            pickle.dump(payload, f)

    def _get_cache(self) -> tuple[models.Profile | None, list[models.Contact] | None]:
        if self._cache is not None:
            return self._cache

        self._cache = self._load_cache()
        return self._cache

    def _load_cache(self) -> tuple[models.Profile | None, list[models.Contact] | None]:
        self._assert_cache_supported()
        assert self.cache is not None

        if not self.cache.is_file():
            return None, None

        logger.info("Loading", file=str(self.cache))
        with self.cache.open(mode="rb") as f:
            payload = pickle.load(f)  # noqa: S301

        return payload.get("profile"), payload.get("contacts")

    def _assert_cache_supported(self) -> None:
        if self.cache is None:
            msg = "Cache not supported"
            raise ValueError(msg)
