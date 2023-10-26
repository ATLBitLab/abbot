from sys import argv

ARGS = argv[1:]
TELEGRAM_MODE = "-l" in ARGS or "--telegram" in ARGS
NOSTR_MODE = "-n" in ARGS or "--nostr" in ARGS

import IPython
from lib.db.mongo import MongoNostr


def run_nostr():
    # TODO: create nostr run fn using backend handlers
    pass


DM_DATA = {
    "id": "6039795807c6f86628ccb8195214e6971929ab50a861dd7af85e40ce69fa3d0a",
    "sender_pk": "9ddf6fe3a194d330a6c6e278a432ae1309e52cc08587254b337d0f491f7ff642",
    "started_at": 1697395393,
    "receiver_pk": "ea0110bcc29b5fecf70b9898aff07e9b74ae764f673a38a8f95c78fb0a41188c",
    "messages": [
        {
            "id": "6039795807c6f86628ccb8195214e6971929ab50a861dd7af85e40ce69fa3d0a",
            "pubkey": "9ddf6fe3a194d330a6c6e278a432ae1309e52cc08587254b337d0f491f7ff642",
            "created_at": 1697395393,
            "kind": 4,
            "tags": [["p", "ea0110bcc29b5fecf70b9898aff07e9b74ae764f673a38a8f95c78fb0a41188c"]],
            "content": "WuNx/mLdkjhas7A3JI59Eg==?iv=LfVClj/9AS8hLQ8+PY0MgA==",
            "sig": "e72c4df42aefd93c81a1632697be5d7a9b8d46f84bf1ce855018b04c2c74fe11b08d0e02d24abbb9d6d6df91edab86e54bac88769f7035e4c5418b28d7434ffd",
        },
        {
            "id": "4d4a390d49b44e02afb0b5241c22fec85ad4fd15aa56c161b0a7fc64c5585a1a",
            "pubkey": "ea0110bcc29b5fecf70b9898aff07e9b74ae764f673a38a8f95c78fb0a41188c",
            "created_at": 1697396103,
            "kind": 4,
            "tags": [["p", "9ddf6fe3a194d330a6c6e278a432ae1309e52cc08587254b337d0f491f7ff642"]],
            "content": "8qyjvmgIdfuUo5hxPjk+aQ==?iv=HecDrNIJXVs4Cr2Ibp3BtA==",
            "sig": "95936c8e8ae21cf88dd32af1b07dc1a663e5ffe9c8eb3db45c71f917cd94b520c7d1ebf7157a78921aec9417a74048b861d45d825e780536189591e8863aee3a",
        },
    ],
    "history": [{"role": "user", "content": "Hey buddy"}, {"role": "assistant", "content": "Hey!"}],
}

if __name__ == "__main__":
    mongo_nostr = MongoNostr()
    IPython.embed()
    # if TELEGRAM_MODE:
    #     TG_BOT: ApplicationBuilder = telegram_bot.build_telgram_bot().run_polling()
    # elif NOSTR_MODE:
    #     run_nostr()
