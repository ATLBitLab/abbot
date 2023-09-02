from sys import argv
from main import clean_jsonl_data, summarize_messages, bot_main

ARGS = argv[1:]
CLEAN = "-c" in ARGS or "--clean" in ARGS
SUMMARY = "-s" in ARGS or "--summary" in ARGS
DEV_MODE = "-d" in ARGS or "--dev" in ARGS
CLEAN_SUMMARY = CLEAN and SUMMARY

if CLEAN:
    clean_jsonl_data()

elif SUMMARY:
    summarize_messages()

elif CLEAN_SUMMARY:
    clean_jsonl_data()
    summarize_messages()

else:
    bot_main()
