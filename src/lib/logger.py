import os
import logging

from lib.utils import now_date
from main import PROGRAM

logger = logging.getLogger("atl_bitlab_bot")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(os.path.abspath("data/debug.log"))
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
now = now_date()

def get_logger():
    return logger


def debug(msg):
    msg_formatted = f"[{now}] {PROGRAM}: {msg}\n"
    print(msg_formatted)
    logger.debug(msg_formatted)
