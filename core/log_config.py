import logging
import contextvars
from pythonjsonlogger import jsonlogger

# Context variable to store the incident ID for the current request/processing flow
incident_id_var = contextvars.ContextVar("incident_id", default="-")


class IncidentFilter(logging.Filter):
    """Injects incident_id into log records if present in the context."""

    def filter(self, record):
        try:
            record.incident_id = incident_id_var.get()
        except LookupError:
            record.incident_id = "-"
        return True


def setup_logging():
    """Configure structured JSON logging."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    log_handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s %(incident_id)s",
        rename_fields={"levelname": "level", "asctime": "timestamp"},
    )

    log_handler.setFormatter(formatter)
    log_handler.addFilter(IncidentFilter())
    logger.addHandler(log_handler)

    return logger
