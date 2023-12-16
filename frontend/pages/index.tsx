import React, { useState } from "react";
import Head from "next/head";
import Image from "next/image";
import Link from "next/link";
import abbot from "@/public/abbot.jpeg";
import Button from "@/components/Button";
import Row from "@/components/Row";
import { useRouter } from "next/router";
import Toast from "awesome-toast-component";
import ChannelForm from "./ChannelForm";

export default function Abbot() {
  const router = useRouter();
  const [channelId, setChannelId] = useState<any>("");
  const [loading, setLoading] = useState<any>(false);
  const [platform, setPlatform] = useState<any>(null); // 'nostr' or 'telegram'
  const [channelMode, setChannelMode] = useState<any>(false); // true when a channel button is clicked
  const [manualAddIsClicked, setManualAddIsClicked] = useState<any>(false);
  const [telegramAddIsClicked, setTelegramAddIsClicked] = useState<any>(false);

  // Function to send NOSTR channel invite
  const sendInvite = async (channelId: string, platform: string) => {
    try {
      const response = await fetch("/api/sendInvite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channelId, platform }),
      });
      const { success, data } = await response.json();
      new Toast(data, {
        style: {
          container: [["background-color", "green"]],
          message: [["color", "white"]],
        },
        position: "top",
      });
    } catch (error) {
      console.error(error);
    }
  };

  // Function to handle platform and channel button selection
  const handleNostrClick = () => {
    setPlatform("nostr");
    setChannelMode(false); // Reset channel mode when switching platforms
  };
  const handleTelegramClick = () => {
    setPlatform("telegram");
    setChannelMode(false); // Reset channel mode when switching platforms
  };

  // Function to reset to initial state
  const handleBackClick = () => {
    setPlatform(null);
    setChannelMode(false);
    setChannelId("");
  };

  // Function to handle form submission
  const handleFormSubmit = async (e: any) => {
    e.preventDefault();
    setLoading(true);
    await sendInvite(channelId, platform);
    console.log(`Channel invite sent for ${channelId}`);
    setLoading(false);
  };

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
      <main className="mx-auto max-w-4xl flex flex-col items-center gap-2 my-16 pb-16 px-8">
        {loading ? (
          <div className="flex justify-center mt-[40%]"></div>
        ) : (
          <div className="flex flex-col items-center w-2/3 gap-8 text-center">
            <a href="tg://resolve?domain=atl_bitlab_bot">
              <Image src={abbot} alt={"Abbot ATL BitLab Bot"} />
            </a>
            <h4>Sup fam, I&apos;m Abbot</h4>
            <h5>
              I&apos;m a helpful bitcoiner bot from Atlanta created by ATL
              BitLab. Est. block 797812.
            </h5>
            <Button
              className="w-full border-[#08252E] border-2 px-8 mt-4"
              type="button"
              onClick={() => router.push("/policies")}
            >
              Terms & Policies 📜
            </Button>
            <PlatformButtons
              onNostrClick={handleNostrClick}
              onTelegramClick={handleTelegramClick}
              platform={platform}
            />
            {platform && (
              <ChannelInteraction
                platform={platform}
                setChannelMode={setChannelMode}
                channelMode={channelMode}
                channelId={channelId}
                setChannelId={setChannelId}
                loading={loading}
                handleFormSubmit={handleFormSubmit}
                manualAddIsClicked={manualAddIsClicked}
                setManualAddIsClicked={setManualAddIsClicked}
                telegramAddIsClicked={telegramAddIsClicked}
                setTelegramAddIsClicked={setTelegramAddIsClicked}
              />
            )}
            {platform && (
              <Button
                className="w-full border-[#08252E] border-2 px-8 mt-4"
                type="button"
                onClick={handleBackClick}
              >
                Back
              </Button>
            )}
            <Row className="w-full">
              <Button
                className="w-full border-[#08252E] border-2 mr-1"
                type="button"
                onClick={() => router.push("/team")}
              >
                Meet the Team 🫂
              </Button>
              <Button
                className="w-full border-[#08252E] border-2 mr-1"
                type="button"
                onClick={() => router.push("/help")}
              >
                Abbot Help 🚀
              </Button>
            </Row>
          </div>
        )}
      </main>
    </>
  );
}

function PlatformButtons({ onNostrClick, onTelegramClick, platform }: any) {
  return (
    <Row className="w-full">
      <Button
        className={`w-full border-[#08252E] border-2 ${platform === "nostr" ? "bg-[#08252E] text-white" : ""}`}
        type="button"
        onClick={onNostrClick}
      >
        Use Nostr 🟣
      </Button>
      <Button
        className={`w-full border-[#08252E] border-2 ml-1 ${platform === "telegram" ? "bg-[#08252E] text-white" : ""}`}
        type="button"
        onClick={onTelegramClick}
      >
        Use Telegram 🤖
      </Button>
    </Row>
  );
}

function ManualInstructions() {
  return (
    <div className="w-5/6">
        <ul className="list-decimal text-left">
        <li>Open Telegram and find your group</li>
        <li>In group settings, select &#34;Add&#34;</li>
        <li>Search for and select &#34;Abbot - ATL BitLab Bot&#34;</li>
        <li>Click &#34;Add&#34;</li>
        <li>Go to group chat and run /start or /start@atl_bitlab_bot</li>
      </ul>
    </div>
  );
}

function TelegramInstructions() {
  return (
    <>
      <div className="w-5/6">
        <ul className="list-decimal text-left">
          <li>Ensure your device has the Telegram app installed</li>
          <li>Click the &#34;ADD ABBOT&#34; button below or scan the QR code</li>
          <li>Select your group from the drop down list on Telegram</li>
          <li>For non-admin, group members, click &#34;OK&#34;</li>
          <li>For admin group members, click &#34;ADD AS ADMIN&#34;</li>
          <li>Go to your group chat and follow the instructions Abbot sends</li>
          <li>
            For help, visit the
            {" "}
            <Link
              href={"/help"}
              className="text-blue-600 underline"
            >
              help
            </Link>
            {" "}
            page or contact
            {" "}
            <Link
              className="text-blue-600
            underline" href="https://t.me/nonni_io"
            >
              @nonni_io
            </Link>
            {" "}
            on Telegram</li>
        </ul>
      </div>
      <Button
        onClick={() => {
          console.log("Button C clicked");
          window.open("https://t.me/atl_bitlab_bot?startgroup=true", "_blank");
        }}
        type="button"
      >
        <Link href="https://t.me/atl_bitlab_bot?startgroup=true">
          Add Abbot
        </Link>
      </Button>
    </>
  );
}

function ChannelInteraction({
  platform,
  setChannelMode,
  channelMode,
  channelId,
  setChannelId,
  loading,
  handleFormSubmit,
  manualAddIsClicked,
  setManualAddIsClicked,
  telegramAddIsClicked,
  setTelegramAddIsClicked,
}: any) {
  const isTelegram = platform === "telegram";


  return (
    <>
      <Row className="w-full">
        <Button
          className="w-full border-[#08252E] border-2 mr-1"
          type="button"
          onClick={() => {
            if (isTelegram) {
              window.location.href = "tg://resolve?domain=atl_bitlab_bot";
            } else {
              window.location.href =
                "https://www.nostrchat.io/dm/npub1agq3p0xznd07eactnzv2lur7nd62uaj0vuar328et3u0kzjprzxqxcqvrk";
            }
          }}
        >
          {isTelegram ? "DM 🤖" : "DM 🟣"}
        </Button>
        <Button
          className={`w-full border-[#08252E] border-2 mr-1 ${channelMode ? "bg-[#08252E] text-white" : ""}`}
          type="button"
          onClick={() => setChannelMode(true)}
        >
          {isTelegram ? "Group Chat 🤖" : "Channel 🟣"}
        </Button>
      </Row>
      {channelMode && (
        <>
          {
            isTelegram && (
              <Row className="w-full">
                <Button
                  className={`w-full border-[#08252E] border-2 mr-1 ${telegramAddIsClicked && "bg-[#08252E] text-white"}`}
                  type="button"
                  onClick={() => {
                    if (!isTelegram) {
                      return window.location.href =
                        "https://www.nostrchat.io/dm/npub1agq3p0xznd07eactnzv2lur7nd62uaj0vuar328et3u0kzjprzxqxcqvrk";
                    }
                    setManualAddIsClicked(false);
                    setTelegramAddIsClicked(true);
                  }}
                >
                  Quick add 🤖
                </Button>
                <Button
                  className={`w-full border-[#08252E] border-2 mr-1 ${manualAddIsClicked && "bg-[#08252E] text-white"}`}
                  type="button"
                  onClick={() => {
                    setTelegramAddIsClicked(false);
                    setManualAddIsClicked(true);
                  }}
                >
                  Manual add 🤖
                </Button>
              </Row>
            ) || (
              <ChannelForm
                value={channelId}
                onChange={setChannelId}
                disabled={loading}
                onSubmit={handleFormSubmit}
                required
              />
            )
          }

          {manualAddIsClicked && <ManualInstructions />}
          {telegramAddIsClicked && <TelegramInstructions />}
        </>
      )}
    </>
  );
}

/*
  function ChannelForm({ channelId, setChannelId, loading, handleFormSubmit }: any) {
    return (
      <Row className="w-full">
        <form
          className="w-full flex justify-between items-center"
          onSubmit={handleFormSubmit}
        >
          <input
            type="text"
            placeholder="Enter your NOSTR channel ID"
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
            disabled={loading}
          >
            {loading ? "Loading..." : "Join"}
          </button>
        </form>
      </Row>
    );
  }
*/