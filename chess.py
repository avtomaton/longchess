from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters

import logging

chess_token = open('telegram_token').readline().strip()

updater = Updater(token=chess_token)
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


class UserData:
    def __init__(self, index, last_word=None):
        self.score = 0
        self.turns = 0
        self.index = index  # user index in round
        self.last_word = last_word


class PendingData:
    def __init__(self, user, word):
        self.user = user
        self.word = word


class Words:
    params_list = ['turns']

    def __init__(self, long_word=None):
        self.max_turns = 5
        self.lang = 'ru'

        self.long_word = long_word
        self.words = []
        self.message = '0_o'
        self.user_list = []
        self.users = {}  # telegram.User : UserData
        self.can_add_user = True
        self.current_user = -1
        self.over = False
        self.pending_data = None

    @staticmethod
    def readable_name(user):
        if user.name:
            return user.name
        else:
            return str(user.id)

    def telegram_help(self):
        if self.lang == 'ru':
            return Words.telegram_help_ru()
        else:
            return Words.telegram_help_en()

    @staticmethod
    def telegram_help_ru():
        return '/игра <слово>: начать новую игру\n' \
               '/слово <слово>: предложить слово\n' \
               '/c <слово>: предложить слово\n' \
               '/да: есть такое слово\n' \
               '/нет: такого слова нет!\n' \
               '/счёт: текущий счёт\n' \
               '/список: вывести все уже использованные слова\n' \
               '/правила: правила игры\n' \
               '/set turns <number>: установить кол-во ходов игры (5 по умолчанию)'

    @staticmethod
    def telegram_help_en():
        return '/game <word>: start a new game\n' \
               '/word <word>: new word\n' \
               '/c <word>: new word\n' \
               '/approve: agree with the last word\n' \
               '/decline: do not agree with the last word\n' \
               '/scores: print current scores\n' \
               '/used: print all used words\n' \
               '/rules: game rules\n' \
               '/set turns <number>: set game duration in turns (default is 5)'

    @staticmethod
    def rules_ru():
        return 'Правила игры:\n' \
               'Смысл игры заключается в составлении слов из букв ' \
               'некого изначального (желательно длинного) слова.\n' \
               'Игроки ходят по очереди, предлагая свои слова. ' \
               'Очки за ход начисляются по количеству букв в предложенном ' \
               'игроком слове. Разрешается использовать только существительные, ' \
               'нарицательные.'

    @staticmethod
    def rules_en():
        text = 'I am sorry, but rules in English are not available now. ' \
               'Nevertheless, I suggest you Russian version. ' \
               'I hope that you are playing with your Russian friend, ' \
               'and he/she can explain them to you =)\n'
        text += Words.rules_ru()
        return text

    def add_word(self, word, user):
        if self.long_word is None:
            self.message = "You should start a new game before entering words!"
            return
        if self.over:
            self.message = "Current game is over, you can view scores or start a new one"
            return
        if user not in self.users:
            if self.can_add_user:
                self.user_list.append(user)
                self.users[user] = UserData(len(self.users))
            else:
                self.message = "I'm sorry, but it seems that the game " \
                               "is already in progress now. If you want to " \
                               "join, consider starting a new game"
                return
        else:
            # somebody made a turn, we should check turns order
            next_user = (self.current_user + 1) % len(self.user_list)
            if len(self.user_list) == 1 and self.current_user == 0:
                # only one user, and he has already made a turn
                self.message = "Single player is not supported yet, " \
                               "somebody else should make a turn "
                return
            elif user != self.user_list[next_user]:
                self.message = \
                    "Not so fast, " + self.readable_name(user) + "! " + \
                    "Now it is " + self.readable_name(self.user_list[next_user]) + "'s turn!"
                return
            elif self.users[user].turns > 0:
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
            self.pending_data = PendingData(user, word)
            self.message = "OK, waiting for somebody else's approve"
        else:
            self.message = "'" + word + "' cannot be used"

    def approve_word(self, user):
        if self.pending_data is None:
            self.message = 'Nothing to approve'
            return

        data = self.users[self.pending_data.user]
        if user not in self.users and data.turns > 0:
            self.message = "You do not play this game and cannot approve words"
            return

        if user == self.pending_data.user:
            self.message = "Somebody else should approve your word"
            return

        word = self.pending_data.word
        self.words.append(word)
        data.score += len(word)
        data.turns += 1
        data.last_word = word
        self.message = self.long_word + ": OK, added '" + \
                       word + "' (" + str(len(word)) + ")"
        # last user, last turn
        if data.turns >= self.max_turns and data.index == len(self.users) - 1:
            self.over = True
        self.current_user = data.index

        self.pending_data = None

    def decline_word(self):
        if self.pending_data is None:
            self.message = 'Nothing to decline'
            return

        self.pending_data = None
        self.message = "Disregarding the last word"

    def get_scores(self):
        self.message = ''
        for user, data in self.users.items():
            self.message += self.readable_name(user) + ': ' + str(data.score) + '\n'
        return self.message

    def get_words(self):
        self.message = 'Used words:'
        for w in self.words:
            self.message += '\n' + w
        return self.message

    def set_turns(self, turns):
        self.max_turns = int(turns)
        self.message = 'OK, set ' + str(self.max_turns) + ' turns as a game duration'
        return self.message


# chat_id : (BotSettings, game)
chats = {}


class BotSettings:
    def __init__(self):
        self.lang = 'ru'


def command_arg(text, args, index):
    # use i-th arg if we don't have space between slash and command name
    # and (i+1)-th otherwise
    if text.split()[0] != '/':
        param = args[index].lower()
    else:
        param = args[index + 1].lower()
    return param


def get_language(update):
    global chats
    try:
        if chats[update.message.chat_id][0].lang == 'ru':
            return 'ru'
        else:
            return 'en'
    except (IndexError, ValueError):
        pass

    return 'ru'


def start(bot, update):
    global chats
    chats[update.message.chat_id] = (BotSettings(), None)
    if get_language(update) == 'ru':
        text = 'Отлично! Играем?'
    else:
        text = "Hey there, let's talk!"
        bot.send_message(chat_id=update.message.chat_id, text=Words.rules_en())
    bot.send_message(chat_id=update.message.chat_id, text=text)
    need_help(bot, update)


def need_help(bot, update):
    if get_language(update) == 'ru':
        text = '/start: начать разговор/игру\n' \
               '/help: подсказка'
        text += Words.telegram_help_ru()
        text += '\nИли просто напишите мне, я довольно дружелюбный'
    else:
        text = '/start: start talking/gaming with me\n' \
               '/help: print this message\n'
        text += Words.telegram_help_en()
        text += '\nOr just text me, I am very friendly'

    bot.send_message(chat_id=update.message.chat_id, text=text)


def rules(bot, update):
    if get_language(update) == 'ru':
        bot.send_message(chat_id=update.message.chat_id, text=Words.rules_ru())
    else:
        bot.send_message(chat_id=update.message.chat_id, text=Words.rules_en())


def game(bot, update, args):
    global chats

    # create chat with parameters if it does not exist
    try:
        w = chats[update.message.chat_id][1]
    except IndexError:
        chats[update.message.chat_id] = (BotSettings(), None)

    try:
        param = command_arg(update.message.text, args, 0)
        chats[update.message.chat_id][1] = Words(param)
        words = chats[update.message.chat_id]
        if get_language(update) == 'ru':
            text = "Начнём же! Ваше слово '" + words.long_word + "'"
        else:
            text = "Let's rock! We use word '" + words.long_word + "'"
        bot.send_message(chat_id=update.message.chat_id, text=text)
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /game <word>")


def set_game_param(bot, update, args):
    try:
        param = command_arg(update.message.text, args, 0)
        if param not in Words.params_list:
            raise IndexError
        words = chats[update.message.chat_id][1]
        param = command_arg(update.message.text, args, 1)
        words.set_turns(param)
        bot.send_message(chat_id=update.message.chat_id, text=words.message)
    except (IndexError, ValueError):
        update.message.reply_text("Wrong /set command format")
        need_help(bot, update)
    except KeyError:
        update.message.reply_text('Game was not started, please start it '
                                  'before setting parameters!')


def word(bot, update, args):
    global chats
    try:
        param = command_arg(update.message.text, args, 0)
        words = chats[update.message.chat_id][1]
        words.add_word(param, update.message.from_user)
        bot.send_message(chat_id=update.message.chat_id, text=words.message)
        if words.over:
            bot.send_message(chat_id=update.message.chat_id, text=words.get_scores())
    except KeyError:
        update.message.reply_text(
            "You should start a new game before entering words!")
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /word <word>")


def approve(bot, update):
    global chats
    try:
        words = chats[update.message.chat_id][1]
        words.approve_word(update.message.from_user)
        bot.send_message(chat_id=update.message.chat_id, text=words.message)
        if words.over:
            bot.send_message(chat_id=update.message.chat_id, text=words.get_scores())
    except KeyError:
        update.message.reply_text(
            "You should start a new game before entering words!")


def decline(bot, update):
    global chats
    try:
        words = chats[update.message.chat_id][1]
        words.decline_word()
        bot.send_message(chat_id=update.message.chat_id, text=words.message)
    except KeyError:
        update.message.reply_text(
            "You should start a new game before entering words!")


def scores(bot, update):
    global chats
    try:
        words = chats[update.message.chat_id][1]
        bot.send_message(chat_id=update.message.chat_id, text=words.get_scores())
    except KeyError:
        update.message.reply_text(
            "You should start a new game before checking scores!")


def used_words(bot, update):
    global chats
    try:
        words = chats[update.message.chat_id][1]
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
    if get_language(update) == 'ru':
        text = "Извините, но я не понимаю, что вы от меня хотите"
    else:
        text = "Sorry, I didn't understand that command."
    bot.send_message(chat_id=update.message.chat_id, text=text)


def error(bot, update, error):
    print('Update "%s" caused error "%s"', update, error)
    # logger.warning('Update "%s" caused error "%s"', update, error)


handlers = [CommandHandler('start', start),
            CommandHandler('help', need_help),
            CommandHandler('game', game, pass_args=True),
            CommandHandler('игра', game, pass_args=True),
            CommandHandler('word', word, pass_args=True),
            CommandHandler('слово', word, pass_args=True),
            CommandHandler('с', word, pass_args=True),
            CommandHandler('c', word, pass_args=True),
            CommandHandler('approve', approve),
            CommandHandler('да', approve),
            CommandHandler('decline', decline),
            CommandHandler('нет', decline),
            CommandHandler('scores', scores),
            CommandHandler('счет', scores),
            CommandHandler('счёт', scores),
            CommandHandler('used', used_words),
            CommandHandler('список', used_words),
            CommandHandler('rules', rules),
            CommandHandler('правила', rules),
            CommandHandler('set', set_game_param, pass_args=True),
            MessageHandler(Filters.command, unknown_command),
            MessageHandler(Filters.entity('mention'), mention),
            MessageHandler(Filters.entity('hashtag'), hashtag)
            # MessageHandler(Filters.text, blah_blah)
            ]

dispatcher.add_error_handler(error)

for h in handlers:
    dispatcher.add_handler(h)

updater.start_polling()
updater.idle()
