from telebot import TeleBot

TOKEN = '7489778031:AAFW7ZxD4H3wQcQ4rMmSOOFFzY_-4vRCeMg'
bot = TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    full_name = f'{first_name} {last_name}' if last_name else first_name
    bot.reply_to(message, f'Welcome, {full_name}!')


@bot.message_handler(func=lambda message: '@la_baza_bot' in message.text)
def reply(message):
    bot.reply_to(message, text='You said "@la_baza_bot"')


def run_telebot():
    print('Running telebot...')
    bot.polling()


run_telebot()
