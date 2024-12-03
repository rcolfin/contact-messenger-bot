import logging
import logging.config

import functions_framework
import google.cloud.logging
from flask import Flask


def _setup_logging() -> None:
    logging_client = google.cloud.logging.Client()
    logging_client.setup_logging()
    logging.config.dictConfig(
        {
            "version": 1,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                }
            },
            "handlers": {
                "wsgi": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://flask.logging.wsgi_errors_stream",
                    "formatter": "default",
                },
                "gcp_logging": {
                    "class": "google.cloud.logging.handlers.CloudLoggingHandler",
                    "client": logging_client,
                },
            },
            "root": {"level": "INFO", "handlers": ["wsgi", "gcp_logging"]},
        }
    )


def create_app() -> Flask:
    _setup_logging()
    return functions_framework.create_app()
