from sys import argv

CLI_ARGS = argv[1:]

DEV_MODE = "-d" in CLI_ARGS or "--dev" in CLI_ARGS
TEST_MODE = "-t" in CLI_ARGS or "--test" in CLI_ARGS
DEV_TEST_MODE = DEV_MODE or TEST_MODE
LOG_MODE = DEV_TEST_MODE or "-l" in CLI_ARGS or "--log" in CLI_ARGS
TELEGRAM_MODE = "-l" in CLI_ARGS or "--telegram" in CLI_ARGS
NOSTR_MODE = "-n" in CLI_ARGS or "--nostr" in CLI_ARGS
