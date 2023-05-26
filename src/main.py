from lib.logger import logger, debug
from lib.utils import get_now
from lib.env import PROGRAM
from atl_bitlab_bot import init

if __name__ == "__main__":
    debug(f'[{get_now()}] {PROGRAM}: Starting!')
    init()
