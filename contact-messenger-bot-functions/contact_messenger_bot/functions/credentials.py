from __future__ import annotations

import logging
import tempfile
from functools import cache, wraps
from pathlib import Path
from typing import TYPE_CHECKING, Callable, TypeVar

import google.cloud.storage as storage  # noqa: PLR0402

from contact_messenger_bot.functions import constants, gcs

if TYPE_CHECKING:
    import flask

logger = logging.getLogger(__name__)

RetType = TypeVar("RetType")


@cache
def get_bucket() -> storage.Bucket:
    client = storage.Client()
    return client.bucket(constants.GCS_BUCKET)


def authenticated(
    func: Callable[[flask.Request, Path, Path], RetType],
) -> Callable[[flask.Request], RetType]:
    if constants.FUSE_SECRETS_CREDENTIALS_FILE.exists():
        # If GCS Fuse Volume exist, then we do not have to explicitly pull/push the credentials:
        @wraps(func)
        def with_fuse_credentials(request: flask.Request) -> RetType:
            return func(request, constants.FUSE_SECRETS_CREDENTIALS_FILE, constants.FUSE_SECRETS_TOKEN_FILE)

        return with_fuse_credentials

    @wraps(func)
    def with_credentials(request: flask.Request) -> RetType:
        bucket = get_bucket()
        with (
            tempfile.TemporaryDirectory() as temp,
            gcs.download(Path(temp), bucket, constants.CREDENTIALS_FILE) as credentials_file,
            gcs.download(Path(temp), bucket, constants.TOKEN_FILE) as token_file,
        ):
            return func(request, credentials_file, token_file)

    return with_credentials
