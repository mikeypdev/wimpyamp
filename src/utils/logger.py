import logging


def get_logger(name: str = "wimpyamp") -> logging.Logger:
    """Get a logger for the WimPyAmp application.

    All modules should use `logger = get_logger(__name__)` to get
    a child logger that inherits the root configuration.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)
    return logger
