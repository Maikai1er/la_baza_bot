from telebot import TeleBot
import sqlite3
import threading


class MafiaBot:
    def __init__(self, token):
        self.bot = TeleBot(token)
        self.conn = sqlite3.connect('event.db', check_same_thread=False)
        self.lock = threading.Lock()  # Блокировка для обеспечения потокобезопасности
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.setup_handlers()

    def create_tables(self):
        with self.lock:  # Использование блокировки для безопасного доступа к БД
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
                              'Добро пожаловать! Вы можете зарегистрироваться с помощью команды "@la_baza_bot регистрация <Ваш ник>"')

        @self.bot.message_handler(func=lambda message: '@la_baza_bot' in message.text)
        def handle_message(message):
            try:
                parts = message.text.split(' ', 2)
                if len(parts) < 3:
                    self.bot.reply_to(message, 'Неверный формат команды. Используйте "@la_baza_bot команда данные"')
                    return

                tag, action, data = parts
                action = action.lower()

                if action == 'регистрация':
                    tg_user_id = message.from_user.id
                    username = data.strip()

                    with self.lock:
                        self.cursor.execute('''
                        INSERT OR REPLACE INTO users (tg_user_id, username)
                        VALUES (?, ?)
                        ''', (tg_user_id, username))
                        self.conn.commit()

                    self.bot.reply_to(message, f'Вы успешно зарегистрированы под ником {username}!')

                elif action == 'запись':
                    event_time = data.strip()
                    tg_user_id = message.from_user.id

                    with self.lock:
                        self.cursor.execute('''
                        SELECT user_id, username FROM users WHERE tg_user_id = ?
                        ''', (tg_user_id,))
                        user = self.cursor.fetchone()

                        if user:
                            user_id, username = user
                            self.cursor.execute('''
                            INSERT INTO registrations (user_id, event_time)
                            VALUES (?, ?)
                            ''', (user_id, event_time))
                            self.conn.commit()
                            self.bot.reply_to(message,
                                              f'Вы успешно записаны на мероприятие, {username}, на время {event_time}!')
                        else:
                            self.bot.reply_to(message,
                                              'Сначала зарегистрируйтесь с помощью команды "@la_baza_bot регистрация <Ваш ник>".')

                else:
                    self.bot.reply_to(message,
                                      'Неверная команда. Используйте "@la_baza_bot регистрация <Ваш ник>" или "@la_baza_bot запись HH:MM"')
            except ValueError:
                self.bot.reply_to(message, 'Неверный формат команды. Используйте "@la_baza_bot команда данные"')
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
