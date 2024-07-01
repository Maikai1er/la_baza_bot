from telebot import TeleBot
import sqlite3


class MafiaBot:
    def __init__(self, token):
        self.bot = TeleBot(token)
        self.conn = sqlite3.connect('event.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.setup_handlers()

    def create_tables(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            event_time TEXT,
            registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        self.conn.commit()

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            tg_user_id INTEGER,
            username TEXT,
            smiley TEXT
        )
        ''')

    def setup_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            first_name = message.from_user.first_name
            last_name = message.from_user.last_name
            full_name = f'{first_name} {last_name}' if last_name else first_name
            self.bot.reply_to(message, f'Welcome, {full_name}!')

        @self.bot.message_handler(func=lambda message: '@la_baza_bot' in message.text)
        def execute_registration(message):
            try:
                tag, action, event_time = message.text.split(' ')
                if action == 'запись':
                    user_id = message.from_user.id
                    first_name = message.from_user.first_name
                    last_name = message.from_user.last_name

                    self.cursor.execute('''
                    INSERT OR REPLACE INTO registrations (user_id, first_name, last_name, event_time)
                    VALUES (?, ?, ?, ?)
                    ''', (user_id, first_name, last_name, event_time))
                    self.conn.commit()

                    full_name = f'{first_name} {last_name}' if last_name else first_name
                    self.bot.reply_to(message, f'Вы успешно записаны на мероприятие, {full_name}!')
                else:
                    self.bot.reply_to(message, 'Неверная команда. Используйте @la_baza_bot запись HH:MM')
            except ValueError:
                self.bot.reply_to(message, 'Неверный формат команды. Используйте @la_baza_bot запись HH:MM')
            except Exception as e:
                self.bot.reply_to(message, f'Произошла ошибка: {e}')

    def start_polling(self):
        print('Running telebot...')
        self.bot.polling()

    def stop(self):
        self.conn.close()


if __name__ == "__main__":
    TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
    bot = MafiaBot(TOKEN)
    try:
        bot.start_polling()
    except KeyboardInterrupt:
        bot.stop()
