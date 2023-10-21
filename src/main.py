from . import abbot_telegram

ARGS = argv[1:]
DEV_MODE = "-d" in ARGS or "--dev" in ARGS

if __name__ == "__main__":
    # T0 - need to async thread this
    abbot_api.run()  # T0 - thread0
    abbot_nostr.run()  # T1 - thread1
    abbot_telegram.run()  # T2 - thread2
