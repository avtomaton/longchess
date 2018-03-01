from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters

import logging

chess_token='461221539:AAF-Fa1r8WcrtC1N4GAoVUE38Vz047xvXuo'

updater = Updater(token=chess_token)
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


class Words:

    def __init__(self, long_word=None):
        self.long_word = long_word
        self.words = []
        self.message = '0_o'
        self.users = {}

    def add_word(self, word, user):
        if user not in self.users:
            self.users[user] = 0
        if word in self.words:
            self.message = "'" + word + "' was already used"
            return
        lw = self.long_word
        valid = True
        for l in word:
            if l in lw:
                lw.replace(l, '0', 1)
            else:
                valid = False
                break
        if valid:
            self.users[user] += len(word)
            self.words.append(word)
            self.message = 'OK, got it'
        else:
            self.message = "'" + word + "' cannot be used"

    def scores(self):
        self.message = ''
        for user, score in self.users.items():
            self.message += user.username + ': ' + str(score) + '\n'
        return self.message


words = Words()


def need_help(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text='/start: start the conversation with me\n'
                          '/help: print this message\n'
                          '/game <word>: start a new game\n'
                          '/word <word>: new word\n'
                          '/scores: print current scores\n'
                          '\nOr just text me, I am very friendly')


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="Hey there, let's talk!")
    need_help(bot, update)


def game(bot, update, args):
    global words
    try:
        words = Words(args[0])
        bot.send_message(chat_id=update.message.chat_id,
                         text="Let's rock! "
                              "We use word '" + words.long_word + "'")
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /game <word>")


def word(bot, update, args):
    global words
    try:
        words.add_word(args[0], update.message.from_user)
        bot.send_message(chat_id=update.message.chat_id, text=words.message)
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /word <word>")


def scores(bot, update):
    global words
    bot.send_message(chat_id=update.message.chat_id, text=words.scores())


def blah_blah(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='blah-blah-blah')


def mention(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="You mentioned someone")


def hashtag(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Hashtag?!")


def unknown_command(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


def error(bot, update, error):
    bot.send_message(chat_id=update.message.chat_id, text="Error (DEBUG MODE ENABLED).")
    # logger.warning('Update "%s" caused error "%s"', update, error)


handlers = [CommandHandler('start', start),
            CommandHandler('help', need_help),
            CommandHandler('game', game, pass_args=True),
            CommandHandler('word', word, pass_args=True),
            CommandHandler('scores', scores),
            MessageHandler(Filters.command, unknown_command),
            MessageHandler(Filters.entity('mention'), mention),
            MessageHandler(Filters.entity('hashtag'), hashtag),
            MessageHandler(Filters.text, blah_blah)
            ]

dispatcher.add_error_handler(error)

for h in handlers:
    dispatcher.add_handler(h)

updater.start_polling()
updater.idle()

