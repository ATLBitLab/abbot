import json
import time
import re
import io

from random import randrange
from help_menu import help_menu_message
from uuid import uuid4

from datetime import datetime

now = datetime.now()
now_iso = now.isoformat()
now_iso_clean = now_iso.split("+")[0].split("T")[0]

from telegram import Update
from telegram.ext import ContextTypes

from lib.utils import get_dates, try_get, qr_code, debug

from lib.api.strike import Strike
from lib.bot.abbot import Abbot, ChatGPT

from env import _STRIKE_API_KEY, _BOT_TOKEN, _TEST_BOT_TOKEN
from constants import (
    DEV_MODE,
    BOT_HANDLE,
    BOT_NAME,
    BOT_UNLEASH_ARGS,
    BOT_UNLEASH_LEASH_ARGS,
    BOT_CHEEKY_RESPONSES,
    CHAT_IDS_TO_IGNORE,
    CHAT_IDS_TO_INCLUDE_UNLEASH,
    CHATS_MAPING_NAME_TO_SHORT_NAME,
    TELEGRAM_HANDLE_WHITELIST,
    RAW_MESSAGE_JL_FILE,
    MESSAGES_JL_FILE,
    SUMMARY_LOG_FILE,
    MESSAGES_PY_FILE,
    PROMPTS_BY_DAY_FILE,
)

_TOKEN = _TEST_BOT_TOKEN if DEV_MODE else _BOT_TOKEN
_NAME = f"t{BOT_NAME}" if DEV_MODE else BOT_NAME
_HANDLE = f"test_{BOT_HANDLE}" if DEV_MODE else BOT_HANDLE

abbot = Abbot(_TOKEN, _NAME, _HANDLE)
prompt_gpt = ChatGPT(abbot, "prompt")
summary_gpt = ChatGPT(abbot, "summary")
group_gpt = ChatGPT(abbot, "group")
private_gpt = ChatGPT(abbot, "private")


async def bot_handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    debug(f"main => bot_handle_message => Raw update {update}")
    mpy = io.open(MESSAGES_PY_FILE, "a")
    mpy.write(update.to_json())
    mpy.write("\n")
    mpy.close()

    message = try_get(update, "effective_message") or update.effective_message
    message_text = try_get(message, "text") or update.effective_chat
    debug(f"main => bot_handle_message => Raw message {message}")
    username = try_get(message, "from_user", "username")
    date = (try_get(message, "date") or now).isoformat().split("+")[0].split("T")[0]

    chat = try_get(update, "effective_chat")
    debug(f"main => bot_handle_message => Raw chat {chat}")
    name = try_get(chat, "first_name", default=username)
    chat_id = try_get(chat, "id")
    chat_title = try_get(
        CHATS_MAPING_NAME_TO_SHORT_NAME,
        try_get(chat, "title"),
        default="atlantabitdevs",
    )
    chat_type = try_get(chat, "type")
    chat_id = try_get(chat, "id")
    private_chat = chat_type == "private"

    if chat_id in CHAT_IDS_TO_IGNORE:
        debug(f"main => bot_handle_message => Chat ignored {chat_id}")
        return
    if not summary_gpt.started:
        debug(f"main => bot_handle_message => {summary_gpt.name} stopped")
        return await message.reply_text(
            f"{summary_gpt.name} stopped, please run /start @{BOT_HANDLE}"
        )
    message_dump = json.dumps(
        {
            **message.to_dict(),
            **chat.to_dict(),
            "title": chat_title,
            "from": username,
            "name": name,
            "date": date,
            "new": True,
        }
    )
    debug(f"main => bot_handle_message => message_dump={message_dump}")
    if private_chat:
        debug(f"main => bot_handle_message => Private chat={private_chat}")
        return

    rm_jl = io.open(RAW_MESSAGE_JL_FILE, "a")
    rm_jl.write(message_dump)
    rm_jl.write("\n")
    rm_jl.close()

    handle_in_message = f"@{group_gpt.handle}" in message_text
    if private_chat and (private_gpt and try_get(private_gpt, "unleashed")):
        private_gpt.update_messages(message)
        answer = private_gpt.chat_completion()
        if not answer:
            emoji = "✅" if group_gpt.leash() else "⛔️"
            answer = f"Please try again later. {group_gpt.name} leashed {emoji}"
            return await message.reply_text(answer)

    elif (
        group_gpt and try_get(group_gpt, "unleashed")
    ) and chat_id in CHAT_IDS_TO_INCLUDE_UNLEASH:
        group_gpt.update_messages(message)
        debug(f"not private_chat => message_text={message_text}")
        if handle_in_message:
            answer = group_gpt.chat_completion()
            if not answer:
                emoji = "✅" if group_gpt.leash() else "⛔️"
                answer = f"Please try again later. {group_gpt.name} leashed {emoji}"
            return await message.reply_text(answer)
        elif len(group_gpt.messages) % 5 == 0:
            answer = group_gpt.chat_completion()
            if not answer:
                emoji = "✅" if group_gpt.leash() else "⛔️"
                answer = f"Please try again later. {group_gpt.name} leashed {emoji}"
            return await message.reply_text(answer)


def bot_clean_jsonl_data():
    debug(f"bot_clean_jsonl_data => Deduping messages")
    seen = set()
    with io.open(RAW_MESSAGE_JL_FILE, "r") as infile, io.open(
        MESSAGES_JL_FILE, "w"
    ) as outfile:
        for line in infile:
            obj = json.loads(line)
            if not obj.get("text"):
                continue
            obj_hash = hash(json.dumps(obj, sort_keys=True))
            if obj_hash not in seen:
                seen.add(obj_hash)
                obj_date = obj.get("date")
                plus_in_date = "+" in obj_date
                t_in_date = "T" in obj_date
                plus_and_t = plus_in_date and t_in_date
                if plus_and_t:
                    obj["date"] = obj_date.split("+")[0].split("T")[0]
                elif plus_in_date:
                    obj["date"] = obj_date.split("+")[0]
                elif t_in_date:
                    obj["date"] = obj_date.split("T")[0]
                obj_text = obj.get("text")
                apos_in_text = "'" in obj_text
                if apos_in_text:
                    obj["text"] = obj_text.replace("'", "")
                outfile.write(json.dumps(obj))
                outfile.write("\n")
    infile.close()
    outfile.close()
    debug(f"bot_clean_jsonl_data => Deduping done")
    return "Cleaning done!"


async def bot_clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_message.from_user.username
    debug(f"main => bot_clean => /clean executed by {sender}")
    if update.effective_message.from_user.username not in TELEGRAM_HANDLE_WHITELIST:
        return await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=BOT_CHEEKY_RESPONSES[randrange(len(BOT_CHEEKY_RESPONSES))],
        )
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Cleaning ... please wait"
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=bot_clean_jsonl_data()
    )


async def bot_both(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await bot_clean(update, context)
    await bot_summary(update, context)
    return "Messages cleaned. Summaries:"


def bot_whitelist_gate(sender):
    return sender not in TELEGRAM_HANDLE_WHITELIST


def bot_summarize_messages(chat, days=None):
    # Separate the key points with an empty line, another line with 10 equal signs, and then another empty line. \n
    try:
        summaries = []
        prompts_by_day = {k: "" for k in days}
        for day in days:
            prompt_content = ""
            messages_file = io.open(MESSAGES_JL_FILE, "r")
            for line in messages_file.readlines():
                message = json.loads(line)
                message_date = try_get(message, "date")
                if day == message_date:
                    text = try_get(message, "text")
                    sender = try_get(message, "from")
                    message = f"{sender} said {text} on {message_date}\n"
                    prompt_content += message
            if prompt_content == "":
                continue
            prompts_by_day[day] = prompt_content
        messages_file.close()
        prompts_by_day_file = io.open(PROMPTS_BY_DAY_FILE, "w")
        prompts_by_day_dump = json.dumps(prompts_by_day)
        prompts_by_day_file.write(prompts_by_day_dump)
        prompts_by_day_file.close()
        debug(
            f"main => bot_summarize_messages => Prompts by day = {prompts_by_day_dump}"
        )
        summary_file = io.open(SUMMARY_LOG_FILE, "a")
        prompt = "Summarize the text after the asterisk. Split into paragraphs where appropriate. Do not mention the asterisk. * \n"
        for day, content in prompts_by_day.items():
            summary_gpt.update_messages(f"{prompt}{content}")
            answer = summary_gpt.chat_completion()
            debug(f"main => bot_summarize_messages => OpenAI Response = {answer}")
            summary = f"Summary {day}:\n{answer.strip()}"
            summary_file.write(f"{summary}\n--------------------------------\n\n")
            summaries.append(summary)
        summary_file.close()
        return True, summaries
    except Exception as e:
        debug(f"main => bot_summarize_messages => error: {e}")
        return False, e


async def bot_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.effective_message
        sender = message.from_user.username
        debug(f"main => bot_summary => /summary executed by {sender}")
        if bot_whitelist_gate(sender):
            return await message.reply_text(
                BOT_CHEEKY_RESPONSES[randrange(len(BOT_CHEEKY_RESPONSES))],
            )

        args = try_get(context, "args")
        arg_len = len(args)
        if arg_len > 3:
            return await message.reply_text("Bad args: too many args")

        date_regex = "^\d{4}-\d{2}-\d{2}$"
        dates = get_dates()
        chat = try_get(args, 0).replace(" ", "").lower()

        if chat != "atlantabitdevs":
            return await message.reply_text("Bad args: Expecting 'atlantabitdevs'")
        response_message = f"Generating {chat} summary for {dates}"
        if arg_len == 2:
            date = try_get(args, 1)
            if not re.search(date_regex, date):
                error = f"Bad args: for 2 args, expecting '/command <chatname> <date>', received {''.join(args)}; e.g. /summary atlantabitdevs 2023-01-01"
                return await message.reply_text(error)
            dates = [date]
            response_message = f"Generating {chat} summary for {dates}"
        elif arg_len == 3:
            dates = try_get(args[1:])
            response_message = f"Generating {chat} summary for {dates}"
            for date in dates:
                if not re.search(date_regex, date):
                    error = f"Bad args: expecting '/summary <chatname> <date> <date>', received {''.join(args)}; e.g. /summary atlantabitdevs 2023-01-01 2023-01-03"
                    return await message.reply_text(error)
        else:
            response_message = f"Generating {chat} summary for {dates}"

        await message.reply_text(response_message)
        success, response = bot_summarize_messages(chat, dates)
        if not success:
            return await message.reply_text(response)
        for summary in response:
            await message.reply_text(summary)
    except Exception as error:
        debug(f"main => bot_summary => error: {error}")
        return await message.reply_text(f"Error: {error}")


async def bot_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sender = update.effective_message.from_user.username
        message = update.effective_message
        debug(
            f"main => bot_prompt => /prompt executed => sender={sender} message={message}"
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Working on your request"
        )
        args = context.args
        debug(f"main => bot_prompt => args: {args}")
        if len(args) <= 0:
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Error: You didn't provide a prompt",
            )
        prompt = " ".join(args)
        strike = Strike(
            _STRIKE_API_KEY,
            str(uuid4()),
            f"ATL BitLab Bot: Payer => {sender}, Prompt => {prompt}",
        )
        invoice, expiration = strike.invoice()
        qr = qr_code(invoice)
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=qr,
            caption=f"Please pay the invoice to get the answer to the question:\n{prompt}",
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"`{invoice}`",
            parse_mode="MarkdownV2",
        )
        while not strike.paid():
            if expiration == 0:
                strike.expire_invoice()
                return await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Invoice expired. Retry?",
                )
            if expiration % 10 == 7:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Invoice expires in {expiration} seconds",
                )
            expiration -= 1
            time.sleep(1)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Thank you for supporting ATL BitLab!",
        )
        prompt_gpt.update_messages(prompt)
        answer = prompt_gpt.chat_completion()
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"{answer}"
        )
        debug(f"main => bot_prompt => Answer: {answer}")
    except Exception as error:
        debug(f"main => bot_prompt => /prompt Error: {error}")
        await message.reply_text(f"Error: {error}")


async def bot_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_message.from_user.username
    message = update.effective_message
    message_text = message.text
    debug(f"main => bot_stop => /stop executed by {sender}")
    if sender not in TELEGRAM_HANDLE_WHITELIST:
        return await message.reply_text(
            BOT_CHEEKY_RESPONSES[randrange(len(BOT_CHEEKY_RESPONSES))],
        )
    if f"@{BOT_HANDLE}" not in message_text:
        return await message.reply_text(
            f"To bot_stop, tag @{BOT_HANDLE} in the help command: e.g. /stop @{BOT_HANDLE}"
        )

    await context.bot.stop_poll(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.id,
        text=f"@{BOT_HANDLE} stopped! Use /start @{BOT_HANDLE} to restart bot",
    )


async def bot_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sender = update.effective_message.from_user.username
        debug(f"main => bot_help => /help executed by {sender}")
        message = update.effective_message
        message_text = update.message.text
        if bot_whitelist_gate(sender):
            return await message.reply_text(
                BOT_CHEEKY_RESPONSES[randrange(len(BOT_CHEEKY_RESPONSES))],
            )
        if f"@{BOT_HANDLE}" not in message_text:
            return await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"For help, tag @{BOT_HANDLE} in the help command: e.g. /help @{BOT_HANDLE}",
            )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=help_menu_message,
        )
    except Exception as e:
        error = e.with_traceback(None)
        debug(f"unleash_the_abbot => Error: {error}")
        await message.reply_text(text=f"Error: {error}")


async def unleash_the_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        message = update.effective_message
        message_text = update.message.text
        sender = message.from_user.username

        bot_toggle = try_get(context, "args", 0, default="False").capitalize()
        bot_type = try_get(context, "args", 1, default="group")
        possible_bot_types = ("group", "private")

        if bot_type not in possible_bot_types:
            err = f"Bad arg: expecting one of {possible_bot_types}"
            return await message.reply_text(err)

        debug(f"unleash_the_abbot => /unleash {args} executed by {sender}")
        if sender not in TELEGRAM_HANDLE_WHITELIST:
            cheek = BOT_CHEEKY_RESPONSES[randrange(len(BOT_CHEEKY_RESPONSES))]
            return await message.reply_text(cheek)
        elif f"@{BOT_HANDLE}" not in message_text:
            return await message.reply_text(
                f"To unleash @{BOT_HANDLE}, run unleash with proper args: e.g. /unleash 1 group @{BOT_HANDLE}",
            )

        if bot_toggle not in BOT_UNLEASH_LEASH_ARGS:
            err = f"Bad arg: expecting one of {BOT_UNLEASH_LEASH_ARGS}"
            return await message.reply_text(err)

        which_bot = group_gpt
        which_bot_name = group_gpt.name
        if bot_type == "private":
            which_bot = private_gpt
            which_bot_name = private_gpt.name

        if bot_toggle in BOT_UNLEASH_ARGS:
            which_bot.unleash()
            await message.reply_text(f"{which_bot_name} unleashed ✅")
        else:
            which_bot.leash()
            await message.reply_text(f"{which_bot_name} leashed ⛔️")

        debug(f"unleash_the_abbot => Unleashed={which_bot.unleashed}")
    except Exception as e:
        error = e.with_traceback(None)
        debug(f"unleash_the_abbot => Error: {error}")
        await message.reply_text(text=f"Error: {error}")
