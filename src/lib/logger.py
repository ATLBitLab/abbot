import logging
logger = logging.getLogger('atl_bitlab_bot')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('data/debug.log')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

def get_logger():
    return logger

def debug(msg):
    print(msg)
    logger.debug(msg)