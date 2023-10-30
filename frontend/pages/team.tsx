/* eslint-disable react-hooks/exhaustive-deps */
import Head from "next/head";
import Image from "next/image";
import React, { useState } from "react";
import { Space_Mono } from "next/font/google";
import abbot from "@/public/abbot.jpeg";
import Member from "@/components/Member";
import Button from "@/components/Button";
import Row from "@/components/Row";
import router from "next/router";

const spacemono = Space_Mono({
  subsets: ["latin"],
  weight: ["400", "700"],
  display: "swap",
});

export default function Team() {
  const members = [
    {
      name: "bryan",
      image: "/team/bryan.jpeg",
      bio: ` 
           🤖 abbot's dad<br>
           ⚡️ running <a href="https://atlbitlab.com">ATL BitLab</a><br>
           🟣 <a href="https://primal.net/p/npub1nh0klcapjnfnpfkxufu2gv4wzvy72txqskrj2jen0585j8ml7epqp5scfr">nonni@atlbitlab.com</a><br>
        `,
    },
    {
      name: "aida",
      image: "/team/aida.jpeg",
      bio: `
            👨🏼‍💻 technical product manager<br>
            💻 <a href="https://www.linkedin.com/in/aidacelys/">https://linkedin.com/in/aidacelys/</a><br>
            🟣 <a href="https://snort.social/p/npub1gs2zeuadlkfkd0mfp6sh46arcvu8xzqtgv7chwtgc9hcvcfa4gxs07wvwg">zestyplastic01@walletofsatoshi</a>
            
        `,
    },
    {
      name: "annie",
      image: "/team/annie.jpeg",
      bio: `
            👨🏼‍💻 full stack software engineer<br>
            💻 <a href="https://www.linkedin.com/in/annie-seth/">https://linkedin.com/in/annie-seth/</a><br>
            🟣 <a href="https://snort.social/p/npub1jm8tv9ltgxluf3za8ql7njwcuu5ukf9hrnv5074zxn3z5gl9n0aqu8lqg5">annie@atlbitlab.com</a><br>
            
        `,
    },
    {
      name: "jordan",
      image: "/team/jordan.jpeg",
      bio: `
            👨🏼‍💻 full stack software engineer<br>
            💻 <a href="https://jordan.bravo.cc">https://jordan.bravo.cc</a><br>
            🟣 <a href="https://snort.social/p/npub1f6ntw2f4dnpdwkccqgg7ef7yagf9kdkrfn7l07kr9uz0q8e9k94sje7kur">jordan@nostrplebs.com</a><br>
            
        `,
    },
    {
      name: "w3irdrobot",
      image: "/team/w3irdrobot.png",
      bio: `
            👨🏼‍💻 software engineer<br>
            💻 <a href="https://w3ird.tech/">https://w3ird.tech/</a><br>
            🟣 <a href="https://snort.social/p/npub17q5n2z8naw0xl6vu9lvt560lg33pdpe29k0k09umlfxm3vc4tqrq466f2y">rob@w3ird.tech</a><br>
            
        `,
    },
    {
      name: "brandon",
      image: "/team/brandon.jpeg",
      bio: `
            👨🏼‍💻 software engineer<br>
            💻 <a href="https://saucy.tech">https://saucy.tech</a><br>
            🟣 <a href="https://snort.social/p/npub14dd9x5uhdctewu6kv7yaunccsuk2fpda7ckttj28l90t2dj38f5spgt54z">saucy@getalby.com</a><br>
        `,
    },
  ];

  return (
    <>
      <Head>
        <title>Team: meet the creators of abbot | ATL BitLab </title>
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
        {" "}
        <div className="flex flex-col items-center w-2/3 gap-8 text-center">
          <a href="tg://resolve?domain=atl_bitlab_bot">
            <Image src={abbot} alt={"Abbot ATL BitLab Bot"} />
          </a>
          <h4>Yo, meet my rad fam!</h4>
          <h5>
            No cap, these are the real wizards behind the scenes. They brought
            me into this world and raised me to be the great bot I am today.
          </h5>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "60px",
            marginTop: "50px",
          }}
        >
          {
            members.map((member, index) => (
              <Member key={index} {...member} />
            ))
          }
        </div>
        <Row className="w-full mt-20">
          <Button
            className="w-full border-[#08252E] border-2 px-8"
            type="button"
            onClick={() => router.push("/")}
          >
            Home 🏠
          </Button>
        </Row>
      </main>
    </>
  );
}
