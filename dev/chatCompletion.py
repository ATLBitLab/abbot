import json
import openai

openai.api_key = "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"

response = openai.ChatCompletion.create(
    messages=[
        {
            "content": "\ud83d\udcf0 The ATL BitLab Weekly Update is out: https://bit.ly/atlbitlab-2023-07-07",
            "name": "Stephen",
            "role": "user",
        },
        {
            "content": "Well they are conveniently located atop Murder Kroger nowadays.\n\nThese lyrics are great stuff. Old Ponce actually was dangerous.\n\nhttps://youtu.be/ozAVtHKlzqQ",
            "name": "Citizen",
            "role": "user",
        },
        {
            "content": "\ud83c\udf7b ndgoHODL is hosting an informal bitcoiner hangout at Tucker Brewing tonight at 7pm! Im going to go check it out for a bit. https://twitter.com/ndgoHODL/status/1674619236562370560",
            "name": "Stephen",
            "role": "user",
        },
        {
            "content": "\ud83e\udde0 Tomorrow, were jamming on AI bitcoin stuff in the Lab. Stop by if youd like to participate in the hackathon! https://www.meetup.com/atlbitlab/events/294567934/",
            "name": "Stephen",
            "role": "user",
        },
        {"content": "/tip 666", "name": "Stephen", "role": "user"},
        {
            "content": "https://lightning.engineering/posts/2023-07-05-l402-langchain/",
            "name": "Giii",
            "role": "user",
        },
        {
            "content": "I cant make it tomorrow, but happy hacking, all \ud83d\udcbb",
            "name": "Jordan",
            "role": "user",
        },
        {"content": "\ud83d\ude02", "name": "bryan", "role": "user"},
        {"content": "\ud83d\ude02 @jf1tt", "name": "bryan", "role": "user"},
        {
            "content": "\ud83d\ude02 meme credit: @jf1tt",
            "name": "bryan",
            "role": "user",
        },
        {"content": "Ai meets bitcoin", "name": "Giii", "role": "user"},
        {
            "content": "Ya gotta get up awfully early to beat Stephen to the punch. GM\n\nDefinitely not AI generated.",
            "name": "Citizen",
            "role": "user",
        },
        {
            "content": "Woooowww. This is the earliest I\u2019ve ever seen you willingly interact with the group\n\ud83d\udc4f\ud83c\udffc GM sir \ud83e\udee1",
            "name": "bryan",
            "role": "user",
        },
        {
            "content": "Reminder for myself and others:\n\nCheckTemplateVerify (CTV) and AnyPrevOut (APO) are soft fork proposals for Bitcoin.\n\nHere is a summary comparison:\n\nhttps://stacker.news/items/7093",
            "name": "Jordan",
            "role": "user",
        },
    ],
    model="gpt-3.5-turbo-16k-0613",
    temperature=0,
)
print(f"response={response}")
