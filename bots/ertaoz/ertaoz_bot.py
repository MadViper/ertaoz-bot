#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import random
from datetime import datetime

import pickledb as pickledb
import pytz
import requests
from telegram import ParseMode, Message, Chat
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater
from telegram.ext.dispatcher import run_async
from transliterate import detect_language, translit
from transliterate.exceptions import LanguageDetectionError

from bots import env
from bots.apis.imageflit_api import ImageflipAPI, ImageFlipApiException
from bots.apis.random_api import RandomAPI, RandomNotImplemented, ResourceType
from bots.apis.weather_api import Weather
from bots.apis.corona_api import Corona
from bots.apis.minify_api import MinifyAPI, MinifyAPIException
from bots.utils.emoji import strip_emoji, strip_spaces
from bots.utils.permissions import admin_required, group_required
from bots.utils.typing import send_typing_action
from contributors import CONTRIBUTORS
from dal import DataAccessLayer
import validators

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

logger = logging.getLogger(__name__)

"""
Create database object
Database schema:
<chat_id>_adm -> user id of the user who invited the bot
<chat_id>_spb -> user id of the user who is target of  mocking spongebob
chats -> list of chat ids where the bot has received messages in.
"""

# Create database object
db = pickledb.load("bot.db", True)

if not db.get("chats"):
    db.set("chats", [])

dal = DataAccessLayer()

TOKEN = "726693597:AAGuNw5J2QiDc-C7DKr2Sa4gaQFJy51E4Bc"
BOT_USERNAME = "ertaoz_bot"

HELP_TEXT = """ერთაოზი ძუყნურიდან!

დახმარება:
/help {ბრძანება} - დახმარება

ბრძანებები:
/minify - URL-ის შემცირება
/cat - კატის ფოტოს გამოგზავნა
/order - ჩატში წესრიგის დამყარება
/weather - მიმდინარე ამინდი
/weather_forecast - ამინდის პროგნოზი
/corona - ინფორმაცია COVID-19 ზე
/wisdom - შერეკილების სიბრძნე
/about - ინფორმაცია შემქმნელებზე
/ertaoz - ინფორმაცია ერთაოზზე
/shonzo_way - სად ვჭამო თბილისში
/random - შემთხვევითი

-- admin --
/unleash_spongebob - გააქტიურე სპანჩ ბობი {user_id}
/restrain_spongebob - დააოკე სპანჩ ბობი

"""

TEST_GROUP_ID = -353748767
NONAME_GROUP_ID = -360632460


@run_async
def send_async(update, context, *args, **kwargs):
    context.bot.sendMessage(chat_id=update.effective_chat.id, **kwargs)


@run_async
def send_async_gif(update, context, *args, **kwargs):
    context.bot.sendAnimation(chat_id=update.effective_chat.id, *args, **kwargs)


@send_typing_action
def start(update, context):
    update.message.reply_text("ერთაოზ ბრეგვაძე ძუყნურიდან!")


@send_typing_action
def cat(update, context):
    cat_photo_url = "https://cataas.com/cat/"
    if context.args:
        cat_photo_params = "/".join(context.args)
        cat_photo_url = cat_photo_url + cat_photo_params
    if cat_photo_url.endswith("/"):
        cat_photo_url = cat_photo_url[:-1]
    try:
        if "gif" in context.args:
            context.bot.sendAnimation(chat_id=update.effective_chat.id, animation=cat_photo_url)
        else:
            context.bot.sendPhoto(chat_id=update.effective_chat.id, photo=cat_photo_url)
    except BadRequest:
        send_async(update, context, text="ფისო ვერ მოიძებნა :(")


@send_typing_action
def order(update, context):
    send_async_gif(
        update, context, caption="დახურეთ საინფორმაციო წყარო!", animation="https://s4.gifyu.com/images/shush.gif",
    )


@send_typing_action
def minify(update, context):
    link = context.args[0] if len(context.args) > 0 else None
    if link == None or not validators.url(link):
        send_async(update, context, text="/minify {url} აუცილებელია გადმოსცეთ URL")
        return

    minifier = MinifyAPI()
    try:
        minified = minifier.minify_link(link)
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError: by {e}")
    except MinifyAPIException as e:
        logger.error(f"MinifyAPIException: by {e}")
    else:
        send_async(update, context, text=minified)


@send_typing_action
def who_is_ertaoz(update, context):
    text = """Info about Ertaoz... Bregvadze... Son of Mizana Bregvadze:
    Hobbies: physics, building ცათმფრენი, ტიტანური იდეები
    Love interest: მარგალიტა
    Friends: შავი დედალი, ბიძია-ბაბუა (ქრისტეფორე მგალობლიშვილი გარიყულადან)
    ნაციხარი: yes
    Net worth: შავი დედალი
    """
    send_async(update, context, text=text)


@send_typing_action
def shonzo_way(update, context):
    random_place = dal.places.fetch_random()
    message = f"{random_place.name}\n{random_place.url}"
    send_async(update, context, text=message)


@send_typing_action
def wisdom(update, context):
    random_wisdom = dal.wisdoms.fetch_random()
    send_async_gif(update, context, caption=random_wisdom.text, animation=random_wisdom.animation)


@send_typing_action
def about(update, context):
    *head, last = [f'<a href="{contributor.github_url}">{contributor.github}</a>' for contributor in CONTRIBUTORS]
    gratitude = f"ჩემო შემქმნელნო - {', '.join(head)} და {last} ყელამდე ვარ თქვენი პატივისცემით!"
    send_async(update, context, text=gratitude, parse_mode=ParseMode.HTML)


# Introduce the bot to a chat its been added to
def introduce(update, context):
    """
    Introduces the bot to a chat its been added to and saves the user id of the
    user who invited us.
    """

    chat_id = update.effective_chat.id
    invited = update.message.from_user.id

    logger.info("Invited by {} to chat {} ({})".format(invited, chat_id, update.message.chat.title))

    db.set(str(chat_id) + "_adm", invited)

    text = f"გამარჯობა {update.message.chat.title}! მე ვარ ერთაოზ ბრეგვაძე ძუყნურიდან. :)"
    send_async(update, context, text=text)


@send_typing_action
def welcome(update, context, new_chat_member):
    """ Welcomes a user to the chat """

    message = update.message
    chat_id = message.chat.id
    logger.info("{} joined to chat {} ({})".format(new_chat_member["first_name"], chat_id, message.chat.title))

    text = """გამარჯობა {username}! კეთილი იყოს შენი მობრძანება {title}-ში :)

    {username} დაწერე რა დღეებში ხარ საქართველოში.

    გისურვებ ბედნიერ ახალი წლის დღეებს :) <3
    """

    # Replace placeholders and send message
    text = text.format(username=new_chat_member["first_name"], title=message.chat.title)
    send_async(update, context, text=text)


def goodbye(update, context):
    """ Sends goodbye message when a user left the chat """

    message = update.message
    chat_id = update.effective_chat.id
    logger.info("{} left chat {} ({})".format(message.left_chat_member.first_name, chat_id, message.chat.title))

    text = "ნახვამდის, $username! :( "

    # Replace placeholders and send message
    text = text.replace("$username", message.left_chat_member.first_name).replace("$title", message.chat.title)
    send_async(update, context, text=text, parse_mode=ParseMode.HTML)


def empty_message(update, context):
    """
    Empty messages could be status messages, so we check them if there is a new
    group member, someone left the chat or if the bot has been added somewhere.
    """

    # Keep chatlist
    chats = db.get("chats")

    if update.message.chat.id not in chats:
        chats.append(update.message.chat.id)
        db.set("chats", chats)
        logger.info("I have been added to %d chats" % len(chats))

    if hasattr(update.message, "new_chat_members") and len(update.message.new_chat_members) > 0:
        new_members = update.message.new_chat_members
        for new_chat_member in new_members:
            # Bot was added to a group chat
            if new_chat_member["username"] == BOT_USERNAME:
                return introduce(update, context)
            # Another user joined the chat
            else:
                return welcome(update, context, new_chat_member)

    # Someone left the chat
    elif hasattr(update.message, "left_chat_member"):
        if update.message.left_chat_member.username != BOT_USERNAME:
            return goodbye(update, context)


def mocking_spongebob(update, context):
    message = update.message
    chat = message.chat
    if (
        chat
        and update.effective_user["is_bot"] == False
        and str(update.effective_user["id"]) == db.get(f"{str(chat.id)}_spb")
    ):
        imageflip = ImageflipAPI()

        first_name = update.effective_user["first_name"]
        user_message = update.message["text"]

        # skip short messages
        if user_message is None or len(user_message) < 5 or len(user_message) > 150 or "http" in user_message:
            return
        # Strip emoji
        user_message = strip_emoji(user_message)
        user_message = strip_spaces(user_message)
        lang = "en"

        # Transliteration
        try:
            lang = detect_language(user_message)
        except LanguageDetectionError:
            logger.error(f"Failed to detect language {user_message}")
        if lang and lang != "en":
            user_message = translit(user_message, lang, reversed=True)

        # Meme text setup
        top = f"{first_name}: {user_message}"
        mocked_line = "".join(random.choice([k.upper(), k]) for k in user_message)
        bottom = f"ME: {mocked_line}"
        try:
            url = imageflip.mocking_spongebob_url(top, bottom)
        except ImageFlipApiException:
            logger.error(f"Failed to generate meme {top}, {bottom}")
        else:
            context.bot.sendPhoto(chat_id=update.effective_chat.id, photo=url)


@group_required
@admin_required(db=db)
def unleash_spongebob(update, context):
    chat_id = update.message.chat_id
    chat_str = str(chat_id)
    target_user_id = context.args[0] if len(context.args) > 0 else None
    if target_user_id is None:
        context.bot.sendMessage(chat_id=chat_id, text="user_id აუცილებელია!")
        return
    db.set(f"{chat_str}_spb", target_user_id)
    context.bot.sendMessage(chat_id=chat_id, text="შესრულებულია")


@group_required
@admin_required(db=db)
def restrain_spongebob(update, context):
    chat_id = update.message.chat_id
    chat_str = str(chat_id)
    db.set(f"{chat_str}_spb", None)
    context.bot.sendMessage(chat_id=chat_id, text="შესრულებულია")


def error(update, context):
    """Log Errors caused by Updates."""
    message = f"Update {update} \n\n error: \n\n {context.error}"
    logger.warning(message)
    if env.bool("ERROR_REPORTING", False):
        context.bot.send_message(chat_id=env.int("ERROR_REPORTING_CHAT_ID", TEST_GROUP_ID), text=message)


@send_typing_action
def help(update, context):
    command = context.args[0] if len(context.args) > 0 else None
    if command == "random":
        text = (
            "ბრძანება შემთხვევითი \n"
            "გამოაგზავნის ფოტოს, ფაქტს ანიმაციას და ა.შ. \n"
            "მუშაობს მხოლოდ ქვემოთ ჩამოთვლილი კატეგორიები. \n\n"
            "/random \n"
            "/random cat \n"
            "/random cat fact \n"
            "/random {cat, dog, panda, fox, bird, koala} \n"
            "/random {cat, dog, panda, fox, bird, koala} fact \n"
        )
        send_async(update, context, text=text)
    else:
        send_async(update, context, text=HELP_TEXT)


def random_handler(update, context):
    random_api = RandomAPI()
    try:
        resource = None
        params = {}
        if len(context.args) > 0:
            resource, tail = context.args[0], context.args[1:]
            if "fact" in tail:
                params["fact"] = True
        r = random_api.fetch(resource, **params)
    except RandomNotImplemented:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text="ინფორმაცია ვერ მოვიძიე :(")
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTPError: by {e}")
    else:
        if r.type == ResourceType.IMG:
            context.bot.sendPhoto(chat_id=update.effective_chat.id, photo=r.content)
        elif r.type == ResourceType.GIF:
            context.bot.sendAnimation(chat_id=update.effective_chat.id, animation=r.content)
        elif r.type == ResourceType.TEXT:
            context.bot.sendMessage(chat_id=update.effective_chat.id, text=r.content)


def weather(update, context):
    api = Weather()
    if context.args:
        weather_info = api.weather(context.args[0])
    else:
        weather_info = api.weather("Tallinn")

    send_async(update, context, text=weather_info)


def weather_forecast(update, context):
    api = Weather()
    if context.args:
        weather_info = api.weather_forecast(context.args[0])
    else:
        weather_info = api.weather_forecast("Tallinn")

    send_async(update, context, text=weather_info)


def corona(update, context):
    api = Corona()
    if context.args:
        corona_info = api.corona(context.args[0])
    else:
        corona_info = api.corona("Estonia")

    send_async(update, context, text=corona_info)


def run(token: str):
    """Run bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(token, use_context=True)
    job = updater.job_queue

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("cat", cat))
    dp.add_handler(CommandHandler("order", order))
    dp.add_handler(CommandHandler("wisdom", wisdom))
    dp.add_handler(CommandHandler("about", about))
    dp.add_handler(CommandHandler("weather", weather))
    dp.add_handler(CommandHandler("weather_forecast", weather_forecast))
    dp.add_handler(CommandHandler("corona", corona))
    dp.add_handler(CommandHandler("ertaoz", who_is_ertaoz))
    dp.add_handler(CommandHandler("shonzo_way", shonzo_way))
    dp.add_handler(CommandHandler("minify", minify))
    dp.add_handler(CommandHandler("random", random_handler))

    dp.add_handler(CommandHandler("unleash_spongebob", unleash_spongebob))
    dp.add_handler(CommandHandler("restrain_spongebob", restrain_spongebob))

    dp.add_handler(MessageHandler(Filters.status_update, empty_message))
    dp.add_handler(MessageHandler(Filters.text, mocking_spongebob))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()
