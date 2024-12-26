from __future__ import annotations

import logging
import logging.config
import sys
from collections import OrderedDict
from enum import Enum
from typing import Any, Final

import structlog

CRITICAL: Final[int] = logging.CRITICAL
FATAL: Final[int] = logging.FATAL
ERROR: Final[int] = logging.ERROR
WARNING: Final[int] = logging.WARNING
WARN: Final[int] = logging.WARN
INFO: Final[int] = logging.INFO
DEBUG: Final[int] = logging.DEBUG
NOTSET: Final[int] = logging.NOTSET


class LogRenderer(str, Enum):
    CONSOLE = "CONSOLE"
    JSON = "JSON"

    @staticmethod
    def default() -> LogRenderer:
        """Returns the default LogRenderer based on whether the stdout is a tty terminal."""
        return LogRenderer.CONSOLE if sys.stdout.isatty() else LogRenderer.JSON


def configure(
    level: int = INFO,
    renderer: LogRenderer | None = None,
    handlers: dict[str, dict[str, Any]] | None = None,
) -> None:
    """
    Configures the struct logger

    Args:
        level (int): The lowest level to display (defaults to INFO).
        renderer (LogRenderer): The type of renderer to use (defaults to LogRenderer.default())
        handlers (dict[str, dict[str, Any]] | None): The standard lib logging handlers.
    """
    structlog.reset_defaults()
    level_name = logging.getLevelName(level)
    if renderer is None:
        renderer = LogRenderer.default()

    processor: structlog.dev.ConsoleRenderer | structlog.processors.JSONRenderer
    if renderer == LogRenderer.CONSOLE:
        processor = structlog.dev.ConsoleRenderer()
    else:
        processor = structlog.processors.JSONRenderer()

    timestamper = structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False)
    processors: list[structlog.typing.Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    foreign_pre_chain = [
        # Add the log level and a timestamp to the event_dict if the log entry
        # is not from structlog.
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
    ]

    if handlers is None:
        handlers = {
            "default": {
                "level": level_name,
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "structlog",
            },
        }

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structlog": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": processor,
                "foreign_pre_chain": foreign_pre_chain,
            },
        },
        "handlers": handlers,
        "loggers": {
            "": {
                "handlers": list(handlers),
                "level": level_name,
                "propagate": True,
            },
        },
    }

    logging.config.dictConfig(logging_config)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=OrderedDict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
