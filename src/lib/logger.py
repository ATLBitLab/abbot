from os.path import abspath
from logging import getLogger, FileHandler, DEBUG, ERROR
from datetime import datetime

now = datetime.now()

debugger = getLogger("abbot_debugger")
debugger.setLevel(DEBUG)
debug_handler = FileHandler(abspath("src/data/debug.log"))
debug_handler.setLevel(DEBUG)
debugger.addHandler(debug_handler)


errogger = getLogger("abbot_errogger")
errogger.setLevel(ERROR)
error_handler = FileHandler(abspath("src/data/error.log"))
error_handler.setLevel(ERROR)
errogger.addHandler(error_handler)


def error(message=""):
    message_formatted = f"[{now}] error - {__name__}: {message}\n"
    print(message_formatted)
    errogger.error(message_formatted)


def debug(message=""):
    message_formatted = f"[{now}] debug - {__name__}: {message}\n"
    print(message_formatted)
    debugger.debug(message_formatted)
