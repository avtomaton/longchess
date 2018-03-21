from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from telegram import KeyboardButton
from telegram import ReplyKeyboardMarkup

import logging

chess_token = open('telegram_token').readline().strip()

updater = Updater(token=chess_token)
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


# ugly simplest translation solution
# TODO: use gettext() instead
# https://docs.python.org/3/library/gettext.html
def _(s):
    lang = 'ru'
    russian_strings = {'Hello world!': 'Привет мир!'}
    spanish_strings = {'Hello world!': 'Hola Mundo!'}

    if lang == 'sp':
        return spanish_strings[s]
    elif lang == 'ru':
        return russian_strings[s]
    else:
        return s


class UserData:
    last_id = 0

    def __init__(self, name, index=0, id=None, last_word=None):
        if id is not None:
            self.id = id
        else:
            self.id = UserData.last_id + 1
            UserData.last_id += 1
        self.name = name
        self.score = 0
        self.turns = 0
        self.index = index  # user index in round
        self.last_word = last_word


class PendingData:
    def __init__(self, user, word):
        self.user = user
        self.word = word


class WrongUserError(RuntimeError):
    pass


class Words:
    params_list = ['turns']

    def __init__(self, long_word=None):
        self.max_turns = 5
        self.lang = 'ru'
        self.states = ['CLEAN', 'NEED_APPROVAL']
        self.state = 'CLEAN'

        if long_word is not None:
            self.long_word = long_word.strip().lower()
        else:
            self.long_word = None
        self.words = []
        self.message = '0_o'
        self.user_list = []
        self.users = {}  # user id : UserData
        self.can_add_user = True
        self.current_user = -1
        self.over = False
        self.pending_data = None

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
               '/склероз: напомнить изначальное слово\n' \
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
               '/remind: remind initial word\n' \
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

    def have_user(self, user_id):
        if user_id in self.users:
            return True
        else:
            return False

    def add_user(self, user_id, user_name):
        if not self.can_add_user:
            raise WrongUserError("I'm sorry, but it seems that the game "
                                 "is already in progress now. If you want to"
                                 "join, consider starting a new game")

        self.user_list.append(user_id)
        self.users[user_id] = UserData(user_name, id=user_id, index=len(self.users))

    def add_word(self, word, user_id):
        word = word.strip().lower()
        if self.long_word is None:
            self.message = "You should start a new game before entering words!"
            return
        if self.over:
            self.message = "Current game is over, you can view scores or start a new one"
            return
        if word == self.long_word:
            self.message = "Cannot score the initial long word"
            return

        # somebody made a turn, we should check turns order
        user = self.users[user_id]
        next_user_idx = (self.current_user + 1) % len(self.user_list)
        if len(self.user_list) == 1 and self.current_user == 0:
            # only one user, and he has already made a turn
            raise WrongUserError("Single player is not supported yet, "
                                 "somebody else should make a turn ")
        elif user_id != self.user_list[next_user_idx]:
            raise WrongUserError("Not so fast, " + user.name + "! " +\
                                 "Now it is " + self.users[self.user_list[next_user_idx]].name +\
                                 "'s turn!")
        elif user.turns > 0:
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

    def approve_word(self, user_id):
        if self.pending_data is None:
            self.message = 'Nothing to approve'
            return

        data = self.users[self.pending_data.user.id]
        if user_id not in self.users and data.turns > 0:
            raise WrongUserError("You do not play this game and cannot approve words")

        if user_id == self.pending_data.user.id:
            raise WrongUserError("Somebody else should approve your word")

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
            self.message += data.name + ': ' + str(data.score) + '\n'
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
        self.state = 'CLEAN'  # 'NEED_WORD' 'NEED_APPROVAL'


def readable_name(user):
    if user.name:
        return user.name
    else:
        return str(user.id)


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
    chats[update.message.chat_id] = [BotSettings(), None]
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
               '/help: подсказка\n'
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


def game_menu_buttons(bot, update, text):
    keyboard = [[KeyboardButton('/слово')]]
    mk = ReplyKeyboardMarkup(keyboard)
    bot.send_message(chat_id=update.message.chat_id, text=text, reply_markup=mk)


def word_greeting(update):
    if get_language(update) == 'ru':
        text = "Замечательно! Итак, ваше слово:"
    else:
        text = "Splendid! Now type your word!"
    return text


def yes_or_no_buttons(bot, update):
    keyboard = [[KeyboardButton('/да'), KeyboardButton('/нет')]]
    mk = ReplyKeyboardMarkup(keyboard)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Waiting for approval...', reply_markup=mk)


def ensure_exists(update):
    """
    Ensure that the chat was added to all active chats
    :param update: telegram.Update object
    """
    global chats
    # create chat with parameters if it does not exist
    try:
        w = chats[update.message.chat_id][1]
    except (KeyError, IndexError):
        chats[update.message.chat_id] = [BotSettings(), None]


def game_is_started(update):
    """
    Check whether game was started or not
    :param update: telegram.Update object
    :return: True if game was started, False otherwise
    """
    global chats
    w = chats[update.message.chat_id][1]
    return w is not None


def game(bot, update, args):
    global chats
    ensure_exists(update)

    try:
        param = command_arg(update.message.text, args, 0)
        chats[update.message.chat_id][1] = Words(param)
        chats[update.message.chat_id][0].state = 'CLEAN'
        words = chats[update.message.chat_id][1]
        if get_language(update) == 'ru':
            text = "Начнём же! Ваше слово '" + words.long_word + "'"
        else:
            text = "Let's rock! We use word '" + words.long_word + "'"
        game_menu_buttons(bot, update, text)
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /game <word>")


def remind_long_word(bot, update):
    global chats
    ensure_exists(update)
    if not game_is_started(update):
        update.message.reply_text(
            "You should start a new game before getting a word!")
        return

    words = chats[update.message.chat_id][1]
    bot.send_message(chat_id=update.message.chat_id, text=words.long_word)


def set_game_param(bot, update, args):
    ensure_exists(update)
    if not game_is_started(update):
        update.message.reply_text('Game was not started, please start it '
                                  'before setting parameters!')
        return

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


def get_word(bot, update, word):
    global chats
    try:
        if chats[update.message.chat_id][0].state != 'NEED_WORD':
            bot.send_message(chat_id=update.message.chat_id,
                             text='Aargh! We do not wait word now!')
            return
        words = chats[update.message.chat_id][1]
        words.add_word(word, update.message.from_user.id)
        bot.send_message(chat_id=update.message.chat_id, text=words.message)
        if words.pending_data:
            chats[update.message.chat_id][0].state = 'NEED_APPROVAL'
            yes_or_no_buttons(bot, update)
    except WrongUserError as e:
        update.message.reply_text(str(e))
    except (KeyError, AttributeError):
        update.message.reply_text("It should never happen (2)")
    except (IndexError, ValueError):
        update.message.reply_text("It should never happen (3)")


def word_command(bot, update, args):
    global chats
    ensure_exists(update)
    if not game_is_started(update):
        update.message.reply_text(
            "You should start a new game before entering words!")
        return

    words = chats[update.message.chat_id][1]
    user = update.message.from_user
    if not words.have_user(user.id):
        try:
            words.add_user(user.id, readable_name(user))
        except WrongUserError as e:
            update.message.reply_text(str(e))
            return

    try:
        param = command_arg(update.message.text, args, 0)
        chats[update.message.chat_id][0].state = 'NEED_WORD'
        get_word(bot, update, param)
    except (IndexError, ValueError):
        try:
            chats[update.message.chat_id][0].state = 'NEED_WORD'
            bot.send_message(chat_id=update.message.chat_id, text=word_greeting(update))
        except (IndexError, KeyError, AttributeError):
            bot.send_message(chat_id=update.message.chat_id,
                             text='It should never happen =(')


def approve(bot, update):
    global chats
    ensure_exists(update)
    if not game_is_started(update):
        update.message.reply_text("No any active game")
        return

    words = chats[update.message.chat_id][1]
    try:
        words.approve_word(update.message.from_user.id)
        if words.over:
            chats[update.message.chat_id][0].state = 'CLEAN'
            bot.send_message(chat_id=update.message.chat_id, text=words.message)
            bot.send_message(chat_id=update.message.chat_id, text=words.get_scores())
        elif words.pending_data is None:
            chats[update.message.chat_id][0].state = 'CLEAN'
            game_menu_buttons(bot, update, words.message)
        else:
            bot.send_message(chat_id=update.message.chat_id, text=words.message)
    except WrongUserError as e:
        update.message.reply_text(str(e))


def decline(bot, update):
    global chats
    ensure_exists(update)
    if not game_is_started(update):
        update.message.reply_text("No any active game")
        return

    words = chats[update.message.chat_id][1]
    words.decline_word()
    game_menu_buttons(bot, update, words.message)


def scores(bot, update):
    global chats
    ensure_exists(update)
    if not game_is_started(update):
        update.message.reply_text("You should start a new game before checking scores!")
        return

    words = chats[update.message.chat_id][1]
    bot.send_message(chat_id=update.message.chat_id, text=words.get_scores())


def used_words(bot, update):
    global chats
    ensure_exists(update)
    if not game_is_started(update):
        update.message.reply_text("You should start a new game before checking used words!")
        return

    words = chats[update.message.chat_id][1]
    bot.send_message(chat_id=update.message.chat_id, text=words.get_words())


def blah_blah(bot, update):
    global chats
    try:
        word = update.message.text.split()[0].strip()
        if chats[update.message.chat_id][0].state == 'NEED_WORD':
            get_word(bot, update, word)
    except (KeyError, IndexError, AttributeError):
        update.message.reply_text('nobody started me :(')


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
            CommandHandler('word', word_command, pass_args=True),
            CommandHandler('слово', word_command, pass_args=True),
            CommandHandler('с', word_command, pass_args=True),
            CommandHandler('c', word_command, pass_args=True),
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
            CommandHandler('remind', remind_long_word),
            CommandHandler('склероз', remind_long_word),
            CommandHandler('set', set_game_param, pass_args=True),
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
