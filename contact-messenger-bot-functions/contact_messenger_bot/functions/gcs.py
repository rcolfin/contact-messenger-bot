from collections.abc import Generator
from contextlib import contextmanager
from functools import cache
from os import PathLike
from pathlib import Path

import google.api_core.exceptions
import google.cloud.storage as storage  # noqa: PLR0402
import structlog

from contact_messenger_bot.functions import constants

logger = structlog.get_logger(__name__)


@cache
def get_bucket() -> storage.Bucket:
    client = storage.Client()
    return client.bucket(constants.GCS_BUCKET)


def _make_gcs_bucket(bucket_name: str, file: str) -> str:
    return f"gs://{bucket_name}/{file}"


@contextmanager
def download(dest_path: PathLike, bucket: storage.Bucket, file: str) -> Generator[Path, None, None]:
    dest_file: Path = Path(dest_path, Path(file).name).resolve()
    blob = bucket.blob(file)
    if blob is not None:
        logger.info("Downloading from GCS", file=_make_gcs_bucket(bucket.name, file), dest=str(dest_file))
        try:
            with dest_file.open("wb") as f:
                blob.download_to_file(f)
        except google.api_core.exceptions.NotFound:
            logger.info("File does not exist in GCS", file=_make_gcs_bucket(bucket.name, file))
            dest_file.unlink()

    ctime = dest_file.stat().st_ctime if dest_file.exists() else None
    yield dest_file
    if dest_file.exists() and dest_file.stat().st_ctime != ctime:
        logger.info("Uploading to GCS", file=_make_gcs_bucket(bucket.name, file), source=str(dest_file))
        blob.upload_from_filename(dest_file)
