"""JSON log records with request IDs and PHI scrubbing (DESIGN §16)."""

import json
import logging
from datetime import UTC, datetime

from apps.core.request_id import get_request_id
from apps.core.scrubbing import scrub_text, scrub_value

# Attributes every LogRecord has; anything else came in through ``extra=``.
_STANDARD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "request_id"}


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "request_id", None):
            record.request_id = get_request_id()
        return True


class PhiScrubbingFilter(logging.Filter):
    """Render the message, scrub identifiers/phones/e-mails, redact sensitive extras."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)
        record.msg = scrub_text(message)
        record.args = None
        for key in list(vars(record)):
            if key not in _STANDARD_ATTRS:
                setattr(record, key, scrub_value(getattr(record, key), key))
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = scrub_text(record.exc_text)
            record.exc_info = None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS:
                payload[key] = value
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            payload["exception"] = record.exc_text
        return json.dumps(payload, default=str, ensure_ascii=False)


def logging_config(level: str = "INFO") -> dict:
    """LOGGING dict for settings: every record leaves through the scrubbing filter as JSON."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {"()": "apps.core.logs.RequestIdFilter"},
            "scrub_phi": {"()": "apps.core.logs.PhiScrubbingFilter"},
        },
        "formatters": {"json": {"()": "apps.core.logs.JsonFormatter"}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "filters": ["request_id", "scrub_phi"],
            }
        },
        "root": {"handlers": ["console"], "level": level},
        "loggers": {
            # SQL with parameters would contain PHI; never log it above DEBUG and never by default.
            "django.db.backends": {"level": "WARNING", "propagate": True},
        },
    }
