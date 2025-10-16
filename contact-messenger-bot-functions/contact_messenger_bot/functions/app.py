import functions_framework
import google.cloud.logging
from contact_messenger_bot.api import logging
from flask import Flask


def _setup_logging() -> None:
    logging_client = google.cloud.logging.Client()
    logging_client.setup_logging()

    logging.configure(
        handlers={
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "structlog",
            },
            "gcp_logging": {
                "class": "google.cloud.logging.handlers.CloudLoggingHandler",
                "client": logging_client,
            },
        },
    )


def create_app() -> Flask:
    _setup_logging()
    return functions_framework.create_app()
