# ABBot
A simple telegram bot using ChatGPT to automate some basic tasks

## Summary
ABBot stands for **A**tl **B**itlab **Bot**. 

Basic tasks that ABBot can automate include:
1. Content gathering, organization and summarization
2. Content creation and marketing
3. Payments
4. Answering questions and basic AI chat interactions
5. Nostr

## Requirements
- Must have python3
- Must have telegram bot API key
  - DM the [Bot Father](https://www.telegram.me/BotFather)
  - Recommend creating 2 bots: @your_telegram_bot and @test_your_telegram_bot
  - See step 7. for how this comes in handy
- Must have openai API key
  - Create an account at [https://platform.openai.com](https://platform.openai.com) 
  - Go create an API key [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys)
- Must have a lightning payment method
  - Abbot is shipped with a Strike Merchant integration and requires a Strike API key out-of-the-box
  - We are working on offering multiple payment ingtegrations
  - Feel free to fork and contribute to [#2](https://github.com/ATLBitLab/abbot/issues/2)

## Install & Run
1. Clone repo && go to dir
```
git clone https://github.com/ATLBitLab/abbot.git && cd abbot
```

2. Copy sample env file into `lib/`
```
cp sample.env.py lib/env.py
```

3. Enter your keys into the appropriate positions

4. Create virtual env
```
python3 -m venv .env
```

5. Activate virtual env
```
source .env/bin/activate
```

6. Install requirements.txt
```
pip3 install -r requirements.txt
```

7. Did you create a test bot per the [Requirements](#Requirements) section? Run the test bot. Otherwise, go to step 8.
```
cd src
python3 cli.py --dev
```

8. Didn't create a test bot? Run the bot normally.
```
cd src
python3 cli.py
```

10. Go to your telegram and DM your bot! That's it!

Found bugs? Need help? Submit a [Bug Report Issue](https://github.com/ATLBitLab/abbot/issues/new?assignees=&labels=&projects=&template=bug_report.md&title=)
Feel free to contact me: https://nonni.io
