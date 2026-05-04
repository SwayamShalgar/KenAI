import logging


def configure_logging(level: int = logging.INFO):
    logging.basicConfig(level=level, format="%(levelname)s %(name)s %(message)s")
