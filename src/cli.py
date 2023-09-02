from sys import argv
from lib.utils import debug
from main import abbot, bot_clean_jsonl_data, bot_summarize_messages, bot_start
import constants

print('constants.DEV_MODE', constants.DEV_MODE)
ARGS = argv[1:]
CLEAN = "-c" in ARGS or "--clean" in ARGS
SUMMARY = "-s" in ARGS or "--summary" in ARGS
constants.DEV_MODE = True if "-d" in ARGS or "--dev" in ARGS else False
print('constants.DEV_MODE', constants.DEV_MODE)
CLEAN_SUMMARY = CLEAN and SUMMARY

if CLEAN:
    bot_clean_jsonl_data()

elif SUMMARY:
    bot_summarize_messages()

elif CLEAN_SUMMARY:
    bot_clean_jsonl_data()
    bot_summarize_messages()

else:
    started = abbot.start()
    debug(f"{abbot.name} @{abbot.handle} Started={started}")
