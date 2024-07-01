from telebot import TeleBot
import sqlite3
import threading
from date_formatter import format_date


class MafiaBot:
    def __init__(self, token):
        self.bot = TeleBot(token)
        self.conn = sqlite3.connect('event.db', check_same_thread=False)
        self.lock = threading.Lock()
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.setup_handlers()
        self.date = 'default date'
        self.time = '18:00'
        self.location = 'https://maps.app.goo.gl/LLHVqSW4Do9ALm5R8?g_st=atm'
        self.registration_open = False

    def open_registration(self):
        self.registration_open = True

    def close_registration(self):
        self.registration_open = False

    def create_tables(self):
        with self.lock:
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_user_id INTEGER UNIQUE,
                username TEXT
            )
            ''')

            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS registrations (
                registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_time TEXT,
                registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            ''')
            self.conn.commit()

    def setup_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            self.bot.reply_to(message,
                              'Добро пожаловать! Вы можете зарегистрироваться с помощью команды "@la_baza_bot '
                              'регистрация <Ваш ник>", либо записаться с помощью команды "@la_baza_bot запись <Время>"')

        @self.bot.message_handler(func=lambda message: '@la_baza_bot' in message.text)
        def handle_message(message):
            try:
                parts = message.text.split(' ', 2)

                tag, action, data = parts[0], parts[1].lower().strip(), parts[2].lower().strip()
                if action == 'открыть':
                    self.start_registration(data, message)

                if action == 'регистрация':
                    self.register_user(message.from_user.id, data, message)
                if action == 'запись':
                    self.register_for_event(message.from_user.id, data, message)
                else:
                    self.bot.reply_to(message,
                                      'Неверная команда. Используйте "@la_baza_bot регистрация <Ваш ник>" или '
                                      '"@la_baza_bot запись <Время>"')
            except ValueError:
                self.bot.reply_to(message, 'Неверный формат команды. Используйте "@la_baza_bot <Команда> <Данные>"')
            except Exception as e:
                self.bot.reply_to(message, f'Произошла ошибка: {e}')

    def start_registration(self, data, message):
        self.open_registration()
        data_list = data.split(' ')
        self.date = format_date(data_list[0])
        if len(data_list) == 2:
            self.location = data_list[1]
        if len(data_list) == 3:
            self.time = data_list[2]
        self.bot.reply_to(message, f'{self.date}, Запись открыта!\n\n {self.time}\n {self.location}')

    def register_user(self, tg_user_id, username, message):
        with self.lock:
            self.cursor.execute('''
            INSERT OR REPLACE INTO users (tg_user_id, username)
            VALUES (?, ?)
            ''', (tg_user_id, username))
            self.conn.commit()
        self.bot.reply_to(message, f'Вы успешно зарегистрированы под ником {username}!')

    def register_for_event(self, tg_user_id, event_time, message):
        with self.lock:
            self.cursor.execute('''
            SELECT user_id, username FROM users WHERE tg_user_id = ?
            ''', (tg_user_id,))
            user = self.cursor.fetchone()
            if not self.event.registration_open:
                self.bot.reply_to(message, 'Нет активной записи на игры.')
            if user:
                user_id, username = user
                self.cursor.execute('''
                INSERT INTO registrations (user_id, event_time)
                VALUES (?, ?)
                ''', (user_id, event_time))
                self.conn.commit()

                self.cursor.execute('''
                SELECT u.username, r.event_time
                FROM registrations r
                JOIN users u ON r.user_id = u.user_id
                ORDER BY r.registration_time
                ''')
                registrations = self.cursor.fetchall()

                registration_list = '\n'.join(
                    [f'{i + 1}. {reg[0]}' + (f' {reg[1]}' if reg[1] != event_time else '') for i, reg in
                     enumerate(registrations)]
                )

                self.bot.reply_to(message,
                                  f'{self.date}, Запись открыта!\n{registration_list}\n {self.time}\n {self.location}')
                if len(registrations) > 12:
                    self.close_registration()
            else:
                self.bot.reply_to(message,
                                  'Сначала зарегистрируйтесь с помощью команды "@la_baza_bot регистрация <Ваш ник>".')

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
