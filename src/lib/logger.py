from cli_args import DEV_MODE, LOG_MODE
from typing import Optional
from os.path import abspath
from datetime import datetime
from logging import FileHandler, Formatter, StreamHandler, getLogger, DEBUG, ERROR

now = datetime.now()

debug_log = getLogger("abbot_debug_logger")
debug_log.setLevel(DEBUG)

debug_formatter = Formatter("[%(asctime)s] debug - %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# File handler for debug logger
debug_file_handler = FileHandler(abspath("src/data/logs/debug.log"))
debug_file_handler.setLevel(DEBUG)
debug_file_handler.setFormatter(debug_formatter)

# Console handler for debug logger (prints to console)
debug_console_handler = StreamHandler()
debug_console_handler.setLevel(DEBUG)
debug_console_handler.setFormatter(debug_formatter)

debug_log.addHandler(debug_file_handler)
debug_log.addHandler(debug_console_handler)

# Configure the logging for the error logger
error_log = getLogger("abbot_error_logger")
error_log.setLevel(ERROR)

error_formatter = Formatter("[%(asctime)s] error - %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# File handler for error logger
error_file_handler = FileHandler(abspath("src/data/logs/error.log"))
error_file_handler.setLevel(ERROR)
error_file_handler.setFormatter(error_formatter)

# Console handler for error logger (prints to console)
error_console_handler = StreamHandler()
error_console_handler.setLevel(ERROR)
error_console_handler.setFormatter(error_formatter)

error_log.addHandler(error_file_handler)
error_log.addHandler(error_console_handler)
FILE_NAME = __name__


class BotLogger:
    def __init__(self, level: str, toggle: bool):
        self.level = level
        self.toggle = toggle

    def log(self, fn_name: str = FILE_NAME, message: Optional[str] = None):
        if not message:
            self._error(f"{FILE_NAME}: No message passed to BotLogger.log()")
            message = fn_name
        message = f"{fn_name} {message}"
        if self.level == "error":
            self._error(message)
        else:
            self._debug(message)

    def _error(self, message: str):
        error_log.error(message)
        debug_log.debug(f"~~~~~~~~~~~~ERROR~~~~~~~~~~~~: {message}")

    def _debug(self, message: str):
        debug_log.debug(message)


error_bot = BotLogger("error", LOG_MODE)
debug_bot = BotLogger("debug", LOG_MODE)
