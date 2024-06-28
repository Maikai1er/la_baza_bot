from telebot import TeleBot
import sqlite3

message_cache = []


class MafiaBot:
    def __init__(self, token):
        self.bot = TeleBot(token)
        self.conn = sqlite3.connect('event.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_event_table()
        self.setup_handlers()

    def create_event_table(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            event_time TEXT,
            registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        self.conn.commit()

    def setup_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            first_name = message.from_user.first_name
            last_name = message.from_user.last_name
            full_name = f'{first_name} {last_name}' if last_name else first_name
            self.bot.reply_to(message, f'Welcome, {full_name}!')

        @self.bot.message_handler(func=lambda message: '@la_baza_bot' in message.text)
        def execute_registration(message):
            tag, action, time = message.text.split(' ')
            match action:
                case 'запись':
                    reply = f'{message.from_user.id}'
                    message_cache.append(reply)
                    self.bot.reply_to(message, text='\n'.join(message_cache))

    def start_polling(self):
        print('Running telebot...')
        self.bot.polling()

    def stop(self):
        self.conn.close()


if __name__ == "__main__":
    TOKEN = '7489778031:AAFW7ZxD4H3wQcQ4rMmSOOFFzY_-4vRCeMg'
    bot = MafiaBot(TOKEN)
    try:
        bot.start_polling()
    except KeyboardInterrupt:
        bot.stop()
