from os.path import abspath
from logging import getLogger, FileHandler, DEBUG, ERROR

from lib.utils import now_date
now = now_date()

debugger = getLogger("abbot_debugger")
debugger.setLevel(DEBUG)
debug_handler = FileHandler(abspath("data/debug.log"))
debug_handler.setLevel(DEBUG)
debugger.addHandler(debug_handler)


errogger = getLogger("abbot_errogger")
errogger.setLevel(ERROR)
error_handler = FileHandler(abspath("data/error.log"))
error_handler.setLevel(ERROR)
errogger.addHandler(error_handler)


def error(message=""):
    message_formatted = f"[{now_date()}] {__name__}: {message}\n"
    print(message_formatted)
    errogger.error(message_formatted)


def debug(message=""):
    message_formatted = f"[{now_date()}] {__name__}: {message}\n"
    print(message_formatted)
    debugger.debug(message_formatted)
