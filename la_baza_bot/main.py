import os

from telebot import TeleBot
from telebot.types import Message
import sqlite3
import threading
from date_formatter import format_date_russian


class MafiaBot:
    def __init__(self, token: str):
        self.bot = TeleBot(token)
        self.conn = sqlite3.connect('../event.db', check_same_thread=False, timeout=10)
        self.lock = threading.Lock()
        self.create_tables()
        self.setup_handlers()
        self.date = 'default date'
        self.time = '18:00'
        self.location = 'https://maps.app.goo.gl/LLHVqSW4Do9ALm5R8?g_st=atm'
        self.registration_open = False

    def is_group_admin(self, chat_id: int, user_id: int) -> bool:
        try:
            chat_member = self.bot.get_chat_member(chat_id, user_id)
            return chat_member.status in ['creator', 'administrator']
        except Exception:
            print(f'Ошибка при получении информации о пользователе.')
            return False

    def open_registration(self) -> None:
        self.registration_open = True

    def close_registration(self) -> None:
        self.registration_open = False

    def create_tables(self) -> None:
        with self.lock:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_user_id INTEGER UNIQUE,
                    username TEXT
                )
                ''')
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS registrations (
                    registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_time TEXT,
                    registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
                ''')
                self.conn.commit()

    def setup_handlers(self) -> None:
        @self.bot.message_handler(func=lambda message: any(keyword in message.text.lower()
                                                           for keyword in ['мраз', 'бля', 'хуй', 'пизд', 'еба']))
        def handle_message(message: Message):
            self.bot.reply_to(message, 'Грубиян!')
            return

        @self.bot.message_handler(commands=['start'])
        def handle_start(message: Message):
            self.bot.reply_to(message, 'Добро пожаловать! Используйте /help для получения списка команд.')

        @self.bot.message_handler(commands=['help'])
        def handle_help(message: Message):
            self.bot.reply_to(message, 'Доступные команды:\n'
                                       '/start - Начать взаимодействие с ботом.\n'
                                       '/help - Список команд.\n'
                                       '/register <Ваш ник> - Зарегистрироваться.\n'
                                       '/join [Время] - Записаться на мероприятие.\n'
                                       '/open <Дата> [Место] [Время] - Открыть запись на мероприятие.\n'
                                       '/clear - Очистить список зарегистрированных участников.\n'
                                       '/cancel - Отменить запись на мероприятие.\n'
                                       '[Необязательные аргументы], <Обязательные аргументы>.')

        @self.bot.message_handler(commands=['register'])
        def handle_register(message: Message):
            try:
                username = message.text.split(maxsplit=1)[1]
                with self.lock:
                    with self.conn:
                        cursor = self.conn.cursor()
                        cursor.execute('''
                        INSERT OR REPLACE INTO users (tg_user_id, username)
                        VALUES (?, ?)
                        ''', (message.from_user.id, username.capitalize()))
                        self.conn.commit()
                self.bot.reply_to(message, f'Вы успешно зарегистрированы под ником {username.capitalize()}!')
            except IndexError:
                self.bot.reply_to(message, 'Неверный формат команды. Используйте /register <Ваш ник>.')

        @self.bot.message_handler(commands=['join'])
        def handle_join(message: Message):
            try:
                parts = message.text.split(maxsplit=1)
                if len(parts) == 1:
                    event_time = self.time
                else:
                    event_time = parts[1]
                self.register_for_event(message.from_user.id, event_time, message)
            except IndexError:
                self.bot.reply_to(message, 'Неверный формат команды. Используйте /join [Время].')

        @self.bot.message_handler(commands=['open'])
        def handle_open(message: Message):
            if not self.is_group_admin(message.chat.id, message.from_user.id):
                self.bot.reply_to(message, 'Вы не являетесь администратором группы.')
                return
            try:
                data = message.text.split(maxsplit=1)[1]
                self.open_registration()
                data_list = data.split(' ')
                self.date = format_date_russian(data_list[0])
                if len(data_list) > 1:
                    self.location = data_list[1]
                if len(data_list) > 2:
                    self.time = data_list[2]
                self.bot.reply_to(message, f'{self.date}, Запись открыта! 😎\n\n🕐 {self.time}\n🗺 {self.location}.')
            except IndexError:
                self.bot.reply_to(message, 'Неверный формат команды. Используйте /open <Дата> [Место] [Время].')

        @self.bot.message_handler(commands=['clear'])
        def handle_clear(message: Message):
            if not self.is_group_admin(message.chat.id, message.from_user.id):
                self.bot.reply_to(message, 'Вы не являетесь администратором группы.')
                return

            try:
                with self.lock:
                    with self.conn:
                        cursor = self.conn.cursor()
                        cursor.execute('DELETE FROM registrations')
                        self.conn.commit()
                self.bot.reply_to(message, 'Список зарегистрированных успешно очищен!')
            except IndexError:
                self.bot.reply_to(message, f'Неверный формат команды. Используйте /clear.')

        @self.bot.message_handler(commands=['cancel'])
        def handle_cancel(message: Message):
            try:
                tg_user_id = message.from_user.id
                self.cancel_registration(tg_user_id, message)
            except IndexError:
                self.bot.reply_to(message, 'Неверный формат команды. Используйте /cancel.')

    def register_for_event(self, tg_user_id: int, event_time: str, message: Message) -> None:
        try:
            with self.lock:
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute('''
                    SELECT user_id, username FROM users WHERE tg_user_id = ?
                    ''', (tg_user_id,))
                    user = cursor.fetchone()
                    if not self.registration_open:
                        self.bot.reply_to(message, 'Нет активной записи на игры.')
                        return
                    if user:
                        user_id, username = user
                        cursor.execute('''
                        SELECT * FROM registrations WHERE user_id = ?
                        ''', (user_id,))
                        existing_registration = cursor.fetchone()

                        if existing_registration:
                            cursor.execute('''
                            UPDATE registrations SET event_time = ? WHERE user_id = ?
                            ''', (event_time, user_id))
                        else:
                            cursor.execute('''
                            INSERT INTO registrations (user_id, event_time)
                            VALUES (?, ?)
                            ''', (user_id, event_time))

                        self.conn.commit()

                        cursor.execute('''
                        SELECT u.username, r.event_time
                        FROM registrations r
                        JOIN users u ON r.user_id = u.user_id
                        ORDER BY r.registration_time
                        ''')
                        registrations = cursor.fetchall()

                        registration_list = '\n'.join(
                            [f'{i + 1}. {reg[0]}' + (f' {reg[1]}' if reg[1] != self.time else '') for i, reg in
                             enumerate(registrations)]
                        )

                        self.bot.reply_to(message,
                                          f'{self.date}, Запись открыта! 😎\n\n{registration_list}\n\n🕐 '
                                          f'{self.time}\n🗺 {self.location}')
                        if len(registrations) > 12:
                            self.close_registration()
                    else:
                        self.bot.reply_to(message, 'Сначала зарегистрируйтесь с помощью команды /register <Ваш ник>.')
        except sqlite3.Error:
            self.bot.reply_to(message, f'Произошла ошибка при записи на мероприятие.')

    def cancel_registration(self, tg_user_id: int, message: Message) -> None:
        try:
            with self.lock:
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute('''
                    SELECT user_id, username FROM users WHERE tg_user_id = ?
                    ''', (tg_user_id,))
                    user = cursor.fetchone()

                    if user:
                        user_id, username = user
                        cursor.execute('''
                        SELECT * FROM registrations WHERE user_id = ?
                        ''', (user_id,))
                        existing_registration = cursor.fetchone()

                        if existing_registration:
                            cursor.execute('''
                            DELETE FROM registrations WHERE user_id = ?
                            ''', (user_id,))
                            self.conn.commit()

                            cursor.execute('''
                            SELECT u.username, r.event_time
                            FROM registrations r
                            JOIN users u ON r.user_id = u.user_id
                            ORDER BY r.registration_time
                            ''')
                            registrations = cursor.fetchall()

                            registration_list = '\n'.join(
                                [f'{i + 1}. {reg[0]}' + (f' {reg[1]}' if reg[1] != self.time else '') for i, reg in
                                 enumerate(registrations)]
                            )

                            self.bot.reply_to(message,
                                              f'{self.date}, Запись открыта! 😎\n\n{registration_list}\n\n🕐 '
                                              f'{self.time}\n🗺 {self.location}')
                            if len(registrations) > 12:
                                self.close_registration()
                        else:
                            self.bot.reply_to(message, 'У вас нет активной записи на мероприятие.')
                    else:
                        self.bot.reply_to(message, 'Вы не зарегистрированы на мероприятие.')

        except sqlite3.Error:
            self.bot.reply_to(message, f'Произошла ошибка при отмене записи на мероприятие.')

    def start_polling(self) -> None:
        print('Running telebot...')
        self.bot.polling(none_stop=True)

    def stop(self) -> None:
        self.conn.close()


if __name__ == '__main__':
    TOKEN = os.getenv('TOKEN')
    bot = MafiaBot(TOKEN)
    try:
        bot.start_polling()
    except KeyboardInterrupt:
        bot.stop()
