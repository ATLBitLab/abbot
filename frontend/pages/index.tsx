/* eslint-disable react-hooks/exhaustive-deps */
import Head from "next/head";
import Image from "next/image";
import React, { useState } from "react";
import { Space_Mono } from "next/font/google";
import abbot from "@/public/abbot.jpeg";
import Button from "@/components/Button";
import { useRouter } from "next/router";
import Row from "@/components/Row";

const spacemono = Space_Mono({
  subsets: ["latin"],
  weight: ["400", "700"],
  display: "swap",
});

export default function Abbot() {
  const router = useRouter();
  const [abbotState, setAbbotState] = useState<number | null>(null);
  const [channelId, setChannelId] = useState<string>("");

  return (
    <>
      <Head>
        <title>
          Meet Abbot: the helpful Atlanta bitcoiner bot | ATL BitLab
        </title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/atl-bitlab-favicon.png" />

        <meta property="og:title" content="Abbot" />
        <meta
          property="og:image"
          content="https://atlbitlab.com/abbot/abbot.jpeg"
        />
        <meta property="og:site_name" content="Telegram" />
        <meta
          property="og:description"
          content="Helpful bitcoiner bot from Atlanta by ATL BitLab. Est. block 797812."
        />

        <meta property="twitter:title" content="Abbot" />
        <meta
          property="twitter:image"
          content="https://atlbitlab.com/abbot/abbot.jpeg"
        />
        <meta property="twitter:site" content="@Telegram" />

        <meta property="al:ios:app_store_id" content="686449807" />
        <meta property="al:ios:app_name" content="Telegram Messenger" />
        <meta
          property="al:ios:url"
          content="tg://resolve?domain=atl_bitlab_bot"
        />

        <meta
          property="al:android:url"
          content="tg://resolve?domain=atl_bitlab_bot"
        />
        <meta property="al:android:app_name" content="Telegram" />
        <meta property="al:android:package" content="org.telegram.messenger" />

        <meta name="twitter:card" content="summary" />
        <meta name="twitter:site" content="@Telegram" />
        <meta
          name="twitter:description"
          content="Helpful bitcoiner bot from Atlanta by ATL BitLab. Est. block 797812."
        />
        <meta name="twitter:app:name:iphone" content="Telegram Messenger" />
        <meta name="twitter:app:id:iphone" content="686449807" />
        <meta
          name="twitter:app:url:iphone"
          content="tg://resolve?domain=atl_bitlab_bot"
        />
        <meta name="twitter:app:name:ipad" content="Telegram Messenger" />
        <meta name="twitter:app:id:ipad" content="686449807" />
        <meta
          name="twitter:app:url:ipad"
          content="tg://resolve?domain=atl_bitlab_bot"
        />
        <meta name="twitter:app:name:googleplay" content="Telegram" />
        <meta
          name="twitter:app:id:googleplay"
          content="org.telegram.messenger"
        />
        <meta
          name="twitter:app:url:googleplay"
          content="https://t.me/atl_bitlab_bot"
        />
      </Head>

      <main
        className={
          spacemono.className +
          " mx-auto max-w-4xl text-white flex flex-col items-center gap-2 my-16 pb-16 px-8"
        }
      >
        <div className="flex flex-col items-center w-2/3 gap-8 text-center">
          <a href="tg://resolve?domain=atl_bitlab_bot">
            <Image src={abbot} alt={"Abbot ATL BitLab Bot"} />
          </a>
          <h4>Sup fam, I&apos;m Abbot</h4>
          <h5>
            I&apos;m a helpful bitcoiner bot from Atlanta created by ATL BitLab.
            Est. block 797812.
          </h5>
          <Row className="w-full">
            <Button
              className="w-full border-[#08252E] border-2 px-8"
              type="button"
              onClick={() => router.push("/policies")}
            >
              Terms & policies 📑
            </Button>
          </Row>
          <Row className="w-full">
            <Button
              className={`w-full border-[#08252E] border-2 mr-1 ${
                abbotState !== null && abbotState !== null && abbotState === 0
                  ? "bg-[#08252E] text-white"
                  : ""
              }`}
              type="button"
              onClick={() =>
                (window.location.href = "tg://resolve?domain=atl_bitlab_bot")
              }
            >
              Telegram 🤖
            </Button>
            <Button
              className={`w-full border-[#08252E] border-2 ml-1 ${
                abbotState !== null && abbotState > 0
                  ? "bg-[#08252E] text-white"
                  : ""
              }`}
              type="button"
              onClick={() => setAbbotState(1)}
            >
              Nostr 🟣
            </Button>
          </Row>
          {abbotState !== null && abbotState >= 1 && (
            <Row className="w-full">
              <Button
                className="w-full border-[#08252E] border-2 mr-1"
                type="button"
                onClick={() =>
                  (window.location.href =
                    "https://www.nostrchat.io/dm/npub1agq3p0xznd07eactnzv2lur7nd62uaj0vuar328et3u0kzjprzxqxcqvrk")
                }
              >
                DM 🟣
              </Button>
              <Button
                className={`w-full border-[#08252E] border-2 ml-1 ${
                  abbotState === 2 ? "bg-[#08252E] text-white" : ""
                }`}
                type="button"
                onClick={() => setAbbotState(2)}
              >
                Channel 🟣
              </Button>
            </Row>
          )}
          {abbotState !== null && abbotState === 2 && (
            <Row className="w-full">
              <form
                className="w-full flex justify-between items-center"
                onSubmit={(e) => {
                  e.preventDefault();
                  console.log("Channel ID submitted:", channelId); // Placeholder for form submission handling
                }}
              >
                <input
                  type="text"
                  placeholder="Enter your channel ID"
                  pattern="[a-f0-9]{64}"
                  title="Channel ID should be 64 lowercase hex characters"
                  className="border-2 border-[#08252E] px-2 text-black flex-grow"
                  value={channelId}
                  onChange={(e) => setChannelId(e.target.value)}
                  required
                />
                <button
                  type="submit"
                  className="border-2 border-[#08252E] px-8 bg-[#08252E] text-white ml-2"
                >
                  Join
                </button>
              </form>
            </Row>
          )}
          <Row className="w-full">
            <Button
              className="w-full border-[#08252E] border-2 px-8"
              type="button"
              onClick={() => router.push("/team")}
            >
              Abbot Team 🫂
            </Button>
          </Row>
        </div>
      </main>
    </>
  );
}
