import logging
from logging.config import dictConfig

def setup_logging():
    """
    Configure logging for the application.
    """
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "detailed": {
                "format": (
                    "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s"
                ),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "detailed",
                "filename": "app.log",
                "mode": "a",
            },
        },
        "root": {
            "level": "INFO",  # Default logging level
            "handlers": ["console", "file"],
        },
        "loggers": {
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    dictConfig(logging_config)