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


def start(bot, update):
    global words
    words = Words("распатронка")
    bot.send_message(chat_id=update.message.chat_id, text="We use word '" + words.long_word + "'")
    bot.send_message(chat_id=update.message.chat_id, text="Hey there, let's talk")


def need_help(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='/start: start the game\n/word: new word')


def word(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='I got it.')
    bot.send_message(chat_id=update.message.chat_id, text='Just kidding, I am still not so smart =)')


def scores(bot, update):
    global words
    bot.send_message(chat_id=update.message.chat_id, text=words.scores())


def echo(bot, update):
    global words
    # bot.send_message(chat_id=update.message.chat_id, text=update.message.text)
    bot.send_message(chat_id=update.message.chat_id, text='blah-blah-blah')
    words.add_word(update.message.text, update.message.from_user)
    bot.send_message(chat_id=update.message.chat_id, text=words.message)


def mention(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="You mentioned someone")


def hashtag(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Hashtag?!")


def unknown_command(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


def error(bot, update, error):
    bot.send_message(chat_id=update.message.chat_id, text="Error (DEBUG MODE ENABLED).")
    # logger.warning('Update "%s" caused error "%s"', update, error)


start_handler = CommandHandler('start', start)
help_handler = CommandHandler('help', need_help)
word_handler = CommandHandler('word', word)
scores_handler = CommandHandler('scores', scores)
echo_handler = MessageHandler(Filters.text, echo)
mention_handler = MessageHandler(Filters.entity('mention'), mention)
hashtag_handler = MessageHandler(Filters.entity('hashtag'), hashtag)
unknown_command_handler = MessageHandler(Filters.command, unknown_command)
dispatcher.add_error_handler(error)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(help_handler)
dispatcher.add_handler(word_handler)
dispatcher.add_handler(scores_handler)
dispatcher.add_handler(mention_handler)
dispatcher.add_handler(hashtag_handler)
dispatcher.add_handler(echo_handler)
dispatcher.add_handler(unknown_command_handler)

updater.start_polling()
updater.idle()

