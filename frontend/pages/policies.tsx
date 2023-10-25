/* eslint-disable react-hooks/exhaustive-deps */
import Head from "next/head";
import Image from "next/image";
import React from "react";
import { Space_Mono } from "next/font/google";
import abbot from "public/abbot/abbot.jpeg";
import Button from "@/components/Button";
import { useRouter } from 'next/router';
import Row from "@/components/Row";

const spacemono = Space_Mono({
    subsets: ["latin"],
    weight: ['400', '700'],
    display: 'swap'
});

export default function Policies() {
    const router = useRouter();
    return (
        <>
            <Head>
                <title>Meet Abbot: the helpful Atlanta bitcoiner bot | ATL BitLab</title>
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <link rel="icon" href="/atl-bitlab-favicon.png" />

                <meta property="og:title" content="Abbot" />
                <meta property="og:image" content="https://atlbitlab.com/abbot/abbot.jpeg" />
                <meta property="og:site_name" content="Telegram" />
                <meta property="og:description" content="Helpful bitcoiner bot from Atlanta by ATL BitLab. Est. block 797812." />

                <meta property="twitter:title" content="Abbot" />
                <meta property="twitter:image" content="https://atlbitlab.com/abbot/abbot.jpeg" />
                <meta property="twitter:site" content="@Telegram" />

                <meta property="al:ios:app_store_id" content="686449807" />
                <meta property="al:ios:app_name" content="Telegram Messenger" />
                <meta property="al:ios:url" content="tg://resolve?domain=atl_bitlab_bot" />

                <meta property="al:android:url" content="tg://resolve?domain=atl_bitlab_bot" />
                <meta property="al:android:app_name" content="Telegram" />
                <meta property="al:android:package" content="org.telegram.messenger" />

                <meta name="twitter:card" content="summary" />
                <meta name="twitter:site" content="@Telegram" />
                <meta name="twitter:description" content="Helpful bitcoiner bot from Atlanta built by ATL BitLab. Est. block 797812." />
                <meta name="twitter:app:name:iphone" content="Telegram Messenger" />
                <meta name="twitter:app:id:iphone" content="686449807" />
                <meta name="twitter:app:url:iphone" content="tg://resolve?domain=atl_bitlab_bot" />
                <meta name="twitter:app:name:ipad" content="Telegram Messenger" />
                <meta name="twitter:app:id:ipad" content="686449807" />
                <meta name="twitter:app:url:ipad" content="tg://resolve?domain=atl_bitlab_bot" />
                <meta name="twitter:app:name:googleplay" content="Telegram" />
                <meta name="twitter:app:id:googleplay" content="org.telegram.messenger" />
                <meta name="twitter:app:url:googleplay" content="https://t.me/atl_bitlab_bot" />
            </Head>
            <main className={spacemono.className + " mx-auto max-w-5xl text-white flex flex-col items-center gap-2 my-16 pb-16"}>
                <div className="flex flex-col items-center w-[50%] gap-8 text-center">
                    <a href="tg://resolve?domain=atl_bitlab_bot">
                        <Image src={abbot} alt={"Abbot ATL BitLab Bot"} />
                    </a>
                </div>
                <br />
                <h3>What data does Abbot collect?</h3>
                <ul>
                    <li>Abbot collects and stores messages sent in a DM or in a channel.</li>
                    <li>Abbot uses stored messages to remain current with the chat context.</li>
                    <li>Abbot the chat context to respond in a relevant and useful way.</li>
                </ul>
                <br />
                <h3>How do I opt-in and start using Abbot?</h3>
                <ul>
                    <li>If you are in a DM, simply run /start.</li>
                    <li>If you are in a group channel, have a channel admin run /start.</li>
                </ul>
                <br />
                <h3>How do I opt-out and stop using Abbot?</h3>
                <ul>
                    <li>Run the /stop command.</li>
                    <li>If you are in a group channel, remove Abbot from the group.</li>
                </ul>
                <br />
                <h3>How do I remove my data from Abbot?</h3>
                <ul>
                    <li>/amnesia wipes all messages between two points in time.</li>
                    <li>/neuralyze wipes all messages between you (or your group) and Abbot.</li>
                </ul>
                <Row className="w-2/3 my-10">

                    <Button
                        className="w-full border-[#08252E] border-2 ml-6 px-8"
                        type="button"
                        onClick={() => router.push("/abbot")}
                    >
                        Back
                    </Button>
                </Row>
            </main>
        </>
    )
}