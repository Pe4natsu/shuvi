import logging

from shuvi.constant import APP_NAME

__all__ = ["logger"]


logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger(APP_NAME)
