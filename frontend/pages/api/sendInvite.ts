import type { NextApiRequest, NextApiResponse } from 'next'
import NDK, { NDKEvent, NDKPrivateKeySigner, NDKUser, NDKTag } from "@nostr-dev-kit/ndk";

import { RELAYS, NOSTR_CHANNEL_INVITE } from "../../lib/constants"
import { NOSTR_ATL_BITLAB_SK, NOSTR_ABBOT_PK } from "../../lib/env";


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

  const signer = new NDKPrivateKeySigner(NOSTR_ATL_BITLAB_SK);

  const ndk = new NDK({ explicitRelayUrls: RELAYS, signer });
  await ndk.connect();

  const abbot = new NDKUser({ npub: NOSTR_ABBOT_PK });

  const body: RequestBody = req.body;
  const event = createInviteEvent(ndk, abbot, body.channelId);

  await event.sign();
  await event.publish();

  res.status(204)
}
