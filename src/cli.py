from sys import argv
from atl_bitlab_bot import clean_jsonl_data, summarize_messages, bot_main
from lib.nostr.nostr import nostr_main
ARGS = argv[1:]
CLEAN = "-c" in ARGS or "--clean" in ARGS
SUMMARY = "-s" in ARGS or "--summary" in ARGS
CLEAN_SUMMARY = CLEAN and SUMMARY

if CLEAN:
    clean_jsonl_data()

elif SUMMARY:
    summarize_messages()

elif CLEAN_SUMMARY:
    clean_jsonl_data()
    summarize_messages()

else:
    nostr_main()
