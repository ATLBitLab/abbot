import time
from lib.abbot.config import BOT_NAME
from subprocess import run, CalledProcessError

from lib.utils import try_get
from lib.logger import bot_debug, bot_error
from lib.abbot.exceptions.exception import try_except


SERVICE_STATUSES = {
    -1: "unknown",
    0: "running",
    1: "stopped",
    2: "killed",
    3: "sleeped",
}


class AdminService:
    status = "unknown"
    status_code = -1
    sleep_time = 60

    def __init__(
        self,
        user_id: int,
        chat_id: int,
        status: str = status,
        status_code: int = status_code,
    ):
        self.user_id = user_id
        self.chat_id = chat_id
        self.status = status
        self.status_code = status_code

    @try_except
    def start_service(self) -> int:
        try:
            fn = "start_service:"
            service = BOT_NAME.lower()
            completed_process = run(["sudo", "systemctl", "start", service], check=True)
            bot_debug.log(f"{fn} Successfully started {service}")
            self.status_code = try_get(completed_process, "returncode")
            self.status = try_get(SERVICE_STATUSES, self.status_code, default=-1)
            return True
        except CalledProcessError as exception:
            bot_error.log(f"Error stopping {service}: {exception}")
            raise exception

    @try_except
    def stop_service(self) -> int:
        try:
            fn = "stop_abbot_process:"
            service = BOT_NAME.lower()
            run(["sudo", "systemctl", "stop", service], check=True)
            bot_debug.log(f"{fn} Successfully stopped {service}")
            self.status = "stopped"
            return True
        except CalledProcessError as exception:
            bot_error.log(f"Error stopping {service}: {exception}")
            raise exception

    @try_except
    def kill_service(self) -> Exception:
        fn = "kill_service:"
        exception = Exception("Plugging Abbot back into the matrix!")
        bot_error.log(f"{fn} => raising exception={exception}")
        raise exception

    @try_except
    def sleep_service(self, S: int = sleep_time) -> bool:
        time.sleep(S)
