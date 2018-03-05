from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters

import logging

chess_token = open('telegram_token').readline().strip()

updater = Updater(token=chess_token)
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


class Words:

    def __init__(self, long_word=None):
        self.max_steps = 20

        self.long_word = long_word
        self.words = []
        self.message = '0_o'
        self.users = []
        self.scores = {}  # telegram.User : score
        self.can_add_user = True
        self.current_user = -1

    @staticmethod
    def readable_name(user):
        if user.name:
            return user.name
        else:
            return str(user.id)

    @staticmethod
    def telegram_help():
        return '/game <word>: start a new game\n' \
               '/word <word>: new word\n' \
               '/слово <слово>: предложить слово\n' \
               '/с <слово>: предложить слово\n' \
               '/scores: print current scores\n' \
               '/used: print all used words\n' \
               '/rules: правила игры'

    @staticmethod
    def rules():
        return 'Правила игры:\n' \
               'Смысл игры заключается в составлении слов из букв ' \
               'некого изначального (желательно длинного) слова.\n' \
               'Игроки ходят по очереди, предлагая свои слова. ' \
               'Очки за ход начисляются по количеству букв в предложенном ' \
               'игроком слове.'

    def add_word(self, word, user):
        if self.long_word is None:
            self.message = "You should start a new game before entering words!"
            return
        next_user = None
        if user not in self.scores:
            if self.can_add_user:
                self.users.append(user)
                self.scores[user] = 0
            else:
                self.message = "I'm sorry, but it seems that the game " \
                               "is already in progress now. If you want to " \
                               "join, consider starting a new game"
                return
        else:
            # somebody made a turn, we should check turns order
            next_user = (self.current_user + 1) % len(self.users)
            if len(self.users) == 1 and self.current_user == 0:
                # only one user, and he has already made a turn
                self.message = "Single player is not supported yet, " \
                               "somebody else should make a turn "
                return
            elif user != self.users[next_user]:
                self.message = \
                    "Not so fast, " + self.readable_name(user) + "! " + \
                    "Now it is " + self.readable_name(self.users[next_user]) + "'s turn!"
                return
            elif self.scores[user] > 0:
                # some existing user is making his second turn, cannot add more users
                self.can_add_user = False

        if word in self.words:
            self.message = "'" + word + "' was already used"
            return
        lw = self.long_word
        valid = True
        for l in word:
            if l in lw:
                lw = lw.replace(l, '0', 1)
            else:
                valid = False
                break
        if valid:
            self.words.append(word)
            self.scores[user] += len(word)
            self.message = self.long_word + ": OK, added '" +\
                           word + "' (" + str(len(word)) + ")"
            if next_user is not None:
                self.current_user = next_user
        else:
            self.message = "'" + word + "' cannot be used"

    def get_scores(self):
        self.message = ''
        for user, score in self.scores.items():
            self.message += self.readable_name(user) + ': ' + str(score) + '\n'
        return self.message

    def get_words(self):
        self.message = 'Used words:'
        for w in self.words:
            self.message += '\n' + w
        return self.message


chats = {}


def need_help(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text='/start: start talking/gaming with me\n'
                          '/help: print this message\n'
                          + Words.telegram_help() +
                          '\nOr just text me, I am very friendly')


def rules(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=Words.rules())


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="Hey there, let's talk!")
    need_help(bot, update)


def game(bot, update, args):
    global chats
    try:
        # use 0-th arg if we don't have space between slach and command name
        # and 1-th otherwise
        if update.message.text.split()[0] != '/':
            param = args[0].lower()
        else:
            param = args[1].lower()
        chats[update.message.chat_id] = Words(param)
        words = chats[update.message.chat_id]
        bot.send_message(chat_id=update.message.chat_id,
                         text="Let's rock! We use word '" + words.long_word + "'")
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /game <word>")


def word(bot, update, args):
    global chats
    try:
        # use 0-th arg if we don't have space between slach and command name
        # and 1-th otherwise
        if update.message.text.split()[0] != '/':
            param = args[0].lower()
        else:
            param = args[1].lower()
        words = chats[update.message.chat_id]
        words.add_word(param, update.message.from_user)
        bot.send_message(chat_id=update.message.chat_id, text=words.message)
    except KeyError:
        update.message.reply_text(
            "You should start a new game before entering words!")
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /word <word>")


def scores(bot, update):
    global chats
    try:
        words = chats[update.message.chat_id]
        bot.send_message(chat_id=update.message.chat_id, text=words.get_scores())
    except KeyError:
        update.message.reply_text(
            "You should start a new game before checking scores!")


def used_words(bot, update):
    global chats
    try:
        words = chats[update.message.chat_id]
        bot.send_message(chat_id=update.message.chat_id, text=words.get_words())
    except KeyError:
        update.message.reply_text(
            "You should start a new game before checking used words!")


def blah_blah(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='blah-blah-blah')


def mention(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="You mentioned someone")


def hashtag(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Hashtag?!")


def unknown_command(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


def error(bot, update, error):
    print('Update "%s" caused error "%s"', update, error)
    # logger.warning('Update "%s" caused error "%s"', update, error)


handlers = [CommandHandler('start', start),
            CommandHandler('help', need_help),
            CommandHandler('game', game, pass_args=True),
            CommandHandler('word', word, pass_args=True),
            CommandHandler('слово', word, pass_args=True),
            CommandHandler('с', word, pass_args=True),
            CommandHandler('c', word, pass_args=True),
            CommandHandler('scores', scores),
            CommandHandler('used', used_words),
            CommandHandler('rules', rules),
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
