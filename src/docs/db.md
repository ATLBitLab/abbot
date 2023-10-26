## **MongoDB**

- Databases: nostr, telegram

### Nostr

- Name: nostr
- Collections: channel, dm

#### channel

```json
{
  "id": "06cff0a67cc40475de5b9b16e39d70f1f242a9cb4772fd84ba5ed1851420e4ab",
  "pubkey": "c41652c2f9c58c3ffe77285cf2c77f87bd45b4c7798a5d81e5d06df52ca32c1c",
  "created_at": 1697820145,
  "kind": 40,
  "tags": [],
  "content": "{\"name\":\"ATL BitLab\",\"about\":\"Atlanta's #bitcoin hackerspace. Est. block 738919. Participant in Bitcoin Hackerspace Network.\",\"picture\":\"https://pbs.twimg.com/profile_images/1640759486305431552/cavNb8x1_400x400.jpg\"}",
  "sig": "0747b51a039df61274d9e276e77c87afedaf894f0daaddd910d90fbc5f9d29a2a7a99a46a94e7812d65c75684bb0db927514bcf28d8ece888cc571ed20932a50",
  "messages": [
    {
      "id": "634b3f1a6e2e064dca17bc34f5c2a4777fe266e36a556c11c5622b61a1545c0c",
      "pubkey": "9ddf6fe3a194d330a6c6e278a432ae1309e52cc08587254b337d0f491f7ff642",
      "created_at": 1697839314,
      "kind": 42,
      "tags": [
        [
          "e",
          "06cff0a67cc40475de5b9b16e39d70f1f242a9cb4772fd84ba5ed1851420e4ab",
          "wss://nos.lol/",
          "root"
        ]
      ],
      "content": "Wubba lubba dub dubbbbbbbb!",
      "sig": "b2dbbefe56e5cddf1a0ed8df11ac188b5c30ad24d82feb4804c72b756a51d1df600b96f216ef85b024b20028279e74a63148d25c2103821b29b419086966ddc3"
    },
    {
      "id": "12c48607d3c6b177e02456e973efdd064bdfcdc374c3f240d358a21d111e4066",
      "pubkey": "ea0110bcc29b5fecf70b9898aff07e9b74ae764f673a38a8f95c78fb0a41188c",
      "created_at": 1697915513,
      "kind": 42,
      "tags": [
        [
          "e",
          "06cff0a67cc40475de5b9b16e39d70f1f242a9cb4772fd84ba5ed1851420e4ab",
          "wss://nos.lol/",
          "root"
        ]
      ],
      "content": "Abbot in the house!! \ud83d\ude4c  ",
      "sig": "e7e7370587b31caf61549419af6f14b50a26f204629379a88b64122e008d611b7a5f79deb45fd8c2f5148a176d9d9fccb61d1f66e75795df0dddb2631e85835a"
    }
  ],
  "history": [
    {
      "role": "user",
      "content": "Wubba lubba dub dubbbbbbbb!"
    },
    {
      "role": "assistant",
      "content": "Abbot in the house!! \ud83d\ude4c  "
    }
  ]
}
```

Comments:

- `id`: channel id
- `"channel_messages"`: nostr events kind 42
- `"history"`: channel history alternating the "role" between "user" (nostr users) and "assistant" (Abbot) as users interact with abbot; this will be fed to OpenAI API chatCompletion

#### dm

```json
{
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
      "tags": [
        [
          "p",
          "ea0110bcc29b5fecf70b9898aff07e9b74ae764f673a38a8f95c78fb0a41188c"
        ]
      ],
      "content": "WuNx/mLdkjhas7A3JI59Eg==?iv=LfVClj/9AS8hLQ8+PY0MgA==",
      "sig": "e72c4df42aefd93c81a1632697be5d7a9b8d46f84bf1ce855018b04c2c74fe11b08d0e02d24abbb9d6d6df91edab86e54bac88769f7035e4c5418b28d7434ffd"
    },
    {
      "id": "4d4a390d49b44e02afb0b5241c22fec85ad4fd15aa56c161b0a7fc64c5585a1a",
      "pubkey": "ea0110bcc29b5fecf70b9898aff07e9b74ae764f673a38a8f95c78fb0a41188c",
      "created_at": 1697396103,
      "kind": 4,
      "tags": [
        [
          "p",
          "9ddf6fe3a194d330a6c6e278a432ae1309e52cc08587254b337d0f491f7ff642"
        ]
      ],
      "content": "8qyjvmgIdfuUo5hxPjk+aQ==?iv=HecDrNIJXVs4Cr2Ibp3BtA==",
      "sig": "95936c8e8ae21cf88dd32af1b07dc1a663e5ffe9c8eb3db45c71f917cd94b520c7d1ebf7157a78921aec9417a74048b861d45d825e780536189591e8863aee3a"
    }
  ],
  "history": [
    {
      "role": "user",
      "content": "Hey buddy"
    },
    {
      "role": "assistant",
      "content": "Hey!"
    }
  ]
}
```

### Telegram

- Name: telegram
- Collections: chat, dm

#### chat

```json
{
  "id": -1001204119993,
  "title": "ATL BitLab",
  "created_at": 1697821151,
  "type": "supergroup",
  "admins": [{ "username": "nonni_io", "user_id": 1711738045 }, {}],
  "messages": [
    {
      "message": {
        "date": 1697821151,
        "...": "..."
      },
      "user": {
        "...": "..."
      },
      "chat": {
        "...": "..."
      }
    },
    {
      "message": {
        "date": 1697821151,
        "...": "..."
      },
      "user": {
        "...": "..."
      },
      "chat": {
        "...": "..."
      }
    }
  ],
  "history": [
    {
      "role": "user",
      "content": "Hey everyone!"
    },
    {
      "role": "assistant",
      "content": "Hi there! How can I help?"
    }
  ]
}
```

Comments:

- `id`: channel id
- `"channel_messages"`: nostr events kind 42
- `"history"`: channel history alternating the "role" between "user" (nostr users) and "assistant" (Abbot) as users interact with abbot; this will be fed to OpenAI API chatCompletion

#### dm

```json
{
  "id": 1711738045,
  "username": "nonni_io",
  "created_at": 1697821151,
  "title": "abbot and nonni_io",
  "messages": [
    {
      "message": {
        "date": 1697821151,
        "...": "..."
      },
      "user": {
        "...": "..."
      },
      "chat": {
        "...": "..."
      }
    },
    {
      "message": {
        "date": 1697821167,
        "...": "..."
      },
      "user": {
        "...": "..."
      },
      "chat": {
        "...": "..."
      }
    }
  ],
  "history": [
    {
      "role": "user",
      "content": "Hey Abbot!"
    },
    {
      "role": "assistant",
      "content": "Hey! How can I help?"
    }
  ]
}
```
