#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.
#
# THIS EXAMPLE HAS BEEN UPDATED TO WORK WITH THE BETA VERSION 12 OF PYTHON-TELEGRAM-BOT.
# If you're still using version 11.1.0, please see the examples at
# https://github.com/python-telegram-bot/python-telegram-bot/tree/v11.1.0/examples

import logging

from telegram import ParseMode
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters
from telegram.ext.dispatcher import run_async

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

TOKEN = "726693597:AAGuNw5J2QiDc-C7DKr2Sa4gaQFJy51E4Bc"
BOTNAME = "ertaoz_bot"


@run_async
def send_async(update, context, *args, **kwargs):
    context.bot.sendMessage(chat_id=update.effective_chat.id, **kwargs)


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    update.message.reply_text("ერთაოზ ბრეგვაძე ძუკნურიდან!")


# Introduce the bot to a chat its been added to
def introduce(update, context):
    """
    Introduces the bot to a chat its been added to and saves the user id of the
    user who invited us.
    """

    chat_id = update.effective_chat.id
    invited = update.message.from_user.id

    logger.info(
        "Invited by {} to chat {} ({})".format(
            invited, chat_id, update.message.chat.title
        )
    )

    text = "გამარჯობა {}! მე ვარ ერთაოზ ბრეგვაძე ძუკნურიდან. მე მივესალმები ხოლმე ყველას ვინც შემოგვიერთდება :)".format(
        update.message.chat.title
    )
    send_async(update, context, text=text)


def welcome(update, context, new_chat_member):
    """ Welcomes a user to the chat """

    message = update.message
    chat_id = message.chat.id
    logger.info(
        "{} joined to chat {} ({})".format(
            new_chat_member["first_name"], chat_id, message.chat.title
        )
    )

    text = "გამარჯობა $username! კეთილი იყოს შენი მობრძანება $title-ში :)"

    # Replace placeholders and send message
    text = text.replace("$username", new_chat_member["first_name"]).replace(
        "$title", message.chat.title
    )
    send_async(update, context, text=text, parse_mode=ParseMode.HTML)


def goodbye(update, context):
    """ Sends goodbye message when a user left the chat """

    message = update.message
    chat_id = update.effective_chat.id
    logger.info(
        "{} left chat {} ({})".format(
            message.left_chat_member.first_name, chat_id, message.chat.title
        )
    )

    text = "ნახვამდის, $username! :( "

    # Replace placeholders and send message
    text = text.replace("$username", message.left_chat_member.first_name).replace(
        "$title", message.chat.title
    )
    send_async(update, context, text=text, parse_mode=ParseMode.HTML)


def empty_message(update, context):
    """
    Empty messages could be status messages, so we check them if there is a new
    group member, someone left the chat or if the bot has been added somewhere.
    """

    if (
        hasattr(update.message, "new_chat_members")
        and len(update.message.new_chat_members) > 0
    ):
        new_members = update.message.new_chat_members
        for new_chat_member in new_members:
            # Bot was added to a group chat
            if new_chat_member["username"] == BOTNAME:
                return introduce(update, context)
            # Another user joined the chat
            else:
                return welcome(update, context, new_chat_member)

    # Someone left the chat
    elif hasattr(update.message, "left_chat_member"):
        if update.message.left_chat_member.username != BOTNAME:
            return goodbye(update, context)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Run bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", start))

    dp.add_handler(MessageHandler(Filters.status_update, empty_message))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    main()