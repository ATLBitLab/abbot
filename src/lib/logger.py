from os.path import abspath
from logging import getLogger, FileHandler, DEBUG, ERROR
from datetime import datetime

now = datetime.now().date()

debug_log = getLogger("abbot_debug_logger")
debug_log.setLevel(DEBUG)
debug_handler = FileHandler(abspath("src/data/debug.log"))
debug_handler.setLevel(DEBUG)
debug_log.addHandler(debug_handler)

error_log = getLogger("abbot_error_logger")
error_log.setLevel(ERROR)
error_handler = FileHandler(abspath("src/data/error.log"))
error_handler.setLevel(ERROR)
error_log.addHandler(error_handler)


class BotLogger:
    def __init__(self, log_type: str):
        self.log_type = log_type
        self.message_format = f"[{now}] {log_type} - {__name__}"

    def log(self, message: str = ""):
        formatted_message = f"{self.message_format}: {message}"
        if self.log_type == "error":
            self._error(formatted_message)
        else:
            self._debug(formatted_message)

    def _error(self, message: str):
        print(message)
        error_log.error(message, exc_info=1)

    def _debug(self, message: str):
        print(message)
        debug_log.debug(message, exc_info=1)


error_logger = BotLogger("error")
debug_logger = BotLogger("debug")
