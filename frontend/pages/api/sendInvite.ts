import type { NextApiRequest, NextApiResponse } from 'next'
import NDK, { NDKEvent, NDKPrivateKeySigner, NDKUser, NDKTag } from "@nostr-dev-kit/ndk";

const RELAYS = [
  "wss://relay1.nostrchat.io",
  "wss://relay2.nostrchat.io",
  "wss://relay.damus.io",
  "wss://nos.lol/",
  "wss://relay.primal.net",
  "wss://relay.snort.social/",
];

const NOSTR_CHANNEL_INVITE = 21021;

interface RequestBody {
  channelId: string
}

const createInviteEvent = (ndk: NDK, abbot: NDKUser, channelId: string): NDKEvent => {
  const event = new NDKEvent(ndk);

  event.kind = NOSTR_CHANNEL_INVITE;
  event.tags.push(["e", channelId]);
  event.tag(abbot);

  return event;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') return;

  const nostrPrivKey = req.env['NOSTR_PRIVATE_KEY'];
  const signer = new NDKPrivateKeySigner(nostrPrivKey);

  const ndk = new NDK({ explicitRelayUrls: RELAYS, signer });
  await ndk.connect();

  const abbotPubKey = req.env['NOSTR_ABBOT_PUBLIC_KEY'];
  const abbot = new NDKUser({ npub: abbotPubKey });

  const body: RequestBody = req.body;
  const event = createInviteEvent(ndk, abbot, body.channelId);

  await event.sign();
  await event.publish();

  res.status(204)
}
