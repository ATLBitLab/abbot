from sys import argv

CLI_ARGS = argv[1:]

DEV_MODE = "-d" in CLI_ARGS or "--dev" in CLI_ARGS
TEST_MODE = "-t" in CLI_ARGS or "--test" in CLI_ARGS

ERR_MODE = "-e" in CLI_ARGS or "--error" in CLI_ARGS
LOG_MODE = DEV_MODE if DEV_MODE else ERR_MODE

TELEGRAM_MODE = "-l" in CLI_ARGS or "--telegram" in CLI_ARGS
NOSTR_MODE = "-n" in CLI_ARGS or "--nostr" in CLI_ARGS
