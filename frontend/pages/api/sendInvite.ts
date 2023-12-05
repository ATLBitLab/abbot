import type { NextApiRequest, NextApiResponse } from 'next'
import NDK, { NDKEvent, NDKPrivateKeySigner, NDKUser, NDKTag } from "@nostr-dev-kit/ndk";

import { RELAYS, NOSTR_CHANNEL_INVITE } from "../../lib/constants"
import { NOSTR_ATL_BITLAB_SK, NOSTR_ABBOT_PK } from "../../lib/env";

interface RequestBody {
  channelId: string,
  platform: string,
}

const createNostrInviteEvent = (ndk: NDK, abbot: NDKUser, channelId: string): NDKEvent => {
  const event = new NDKEvent(ndk);

  event.kind = NOSTR_CHANNEL_INVITE;
  event.tags.push(["e", channelId]);
  event.tag(abbot);

  return event;
};

const handleNostr = async (channelId: string) => {
  const signer = new NDKPrivateKeySigner(NOSTR_ATL_BITLAB_SK);

  const ndk = new NDK({ explicitRelayUrls: RELAYS, signer });
  await ndk.connect();

  const abbot = new NDKUser({ npub: NOSTR_ABBOT_PK });

  const event = createNostrInviteEvent(ndk, abbot, channelId);

  await event.sign();
  await event.publish();
  return event
}

const handleTelegram = async (channelId: string) => {
  // TODO: how to do this
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  try {
    if (req.method !== 'POST') return;
    const { platform } = req.query;
    const { channelId }: RequestBody = req.body;
    let data;
    if (platform === "nostr") {
      data = await handleNostr(channelId);
    } else {
      data = await handleTelegram(channelId);
    }
    res.status(204).json({ success: true, data });
  } catch (error) {
    res.status(500).json({ success: false, data: error })
  }
}
