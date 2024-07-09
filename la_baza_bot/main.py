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
                    username TEXT,
                    event_time TEXT,
                    registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                self.conn.commit()

    def setup_handlers(self) -> None:
        @self.bot.message_handler(commands=['start'])
        def handle_start(message: Message):
            if not self.is_allowed_thread(message):
                self.bot.reply_to(message, 'Вы не можете использовать команды в этом топике.')
                return
            else:
                self.bot.reply_to(message, f'Добро пожаловать! Используйте /help для получения списка команд '
                                           f'{message.message_thread_id}.')
                return

        @self.bot.message_handler(commands=['help'])
        def handle_help(message: Message):
            if not self.is_allowed_thread(message):
                self.bot.reply_to(message, 'Вы не можете использовать команды в этом топике.')
                return
            self.bot.reply_to(message, 'Доступные команды:\n'
                                       '/start - Начать взаимодействие с ботом.\n'
                                       '/help - Список команд.\n'
                                       '/register <Ваш никнейм> - Зарегистрироваться.\n'
                                       '/join [Комментарий] - Записаться на игровой вечер.\n'
                                       '/invite <Никнейм> [Комментарий].\n'
                                       '/cancel [Никнейм] - Отменить запись на игровой вечер.\n'
                                       'ТОЛЬКО ДЛЯ ЛОЛЫ:'
                                       '/open <Дата> [Место] [Время] - Открыть запись на игровой вечер.\n'
                                       '/clear - Очистить список записанных участников.\n'
                                       '* <Обязательно>, [Необязательно].')

        @self.bot.message_handler(commands=['register'])
        def handle_register(message: Message):
            if not self.is_allowed_thread(message):
                self.bot.reply_to(message, 'Вы не можете использовать команды в этом топике.')
                return
            try:
                username = message.text.split(maxsplit=1)[1]
                with self.lock:
                    with self.conn:
                        cursor = self.conn.cursor()
                        cursor.execute('''
                        INSERT OR REPLACE INTO users (tg_user_id, username)
                        VALUES (?, ?)
                        ''', (message.from_user.id, username))
                        self.conn.commit()
                self.bot.reply_to(message, f'Вы успешно зарегистрированы под ником {username}!')
            except IndexError:
                self.bot.reply_to(message, 'Неверный формат команды. Используйте /register <Ваш никнейм>.')

        @self.bot.message_handler(commands=['join'])
        def handle_join(message: Message):
            if not self.is_allowed_thread(message):
                self.bot.reply_to(message, 'Вы не можете использовать команды в этом топике.')
                return
            try:
                parts = message.text.split(maxsplit=1)
                if len(parts) == 1:
                    event_time = self.time
                else:
                    event_time = parts[1]
                self.register_for_event(message.from_user.id, event_time, message)
            except IndexError:
                self.bot.reply_to(message, 'Неверный формат команды. Используйте /join [Комментарий].')

        @self.bot.message_handler(commands=['invite'])
        def handle_invite(message: Message):
            if not self.is_allowed_thread(message):
                self.bot.reply_to(message, 'Вы не можете использовать команды в этом топике.')
                return
            try:
                parts = message.text.split(' ')
                event_time = self.time if len(parts) == 2 else parts[2]
                nickname = parts[1]
                self.invite_registration(nickname, event_time, message)
            except IndexError:
                self.bot.reply_to(message, 'Неверный формат команды. Используйте /invite <Никнейм> [Комментарий].')

        @self.bot.message_handler(commands=['open'])
        def handle_open(message: Message):
            if not self.is_group_admin(message.chat.id, message.from_user.id):
                self.bot.reply_to(message, 'Вы не являетесь администратором группы.')
                return
            if not self.is_allowed_thread(message):
                self.bot.reply_to(message, 'Вы не можете использовать команды в этом топике.')
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
            if not self.is_allowed_thread(message):
                self.bot.reply_to(message, 'Вы не можете использовать команды в этом топике.')
                return
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
            if not self.is_allowed_thread(message):
                self.bot.reply_to(message, 'Вы не можете использовать команды в этом топике.')
                return
            try:
                parts = message.text.split(maxsplit=1)
                if len(parts) == 1:
                    tg_user_id = message.from_user.id
                    self.cancel_registration_by_id(tg_user_id, message)
                elif len(parts) == 2:
                    username = parts[1]
                    self.cancel_registration_by_username(username, message)
                else:
                    self.bot.reply_to(message, 'Неверный формат команды. Используйте /cancel или /cancel <Никнейм>.')
            except IndexError:
                self.bot.reply_to(message, 'Неверный формат команды. Используйте /cancel или /cancel <Никнейм>.')

    def is_allowed_thread(self, message: Message) -> bool:
        try:
            if message.message_thread_id == 2:
                return True
            else:
                return False
        except Exception:
            self.bot.reply_to(message, 'Произошла непредвиденная ошибка.')
            return False

    def register_for_event(self, tg_user_id: int, event_time: str, message: Message) -> None:
        try:
            with self.lock:
                with self.conn:
                    cursor = self.conn.cursor()

                    cursor.execute('''
                    SELECT username FROM users WHERE tg_user_id = ?
                    ''', (tg_user_id,))
                    user = cursor.fetchone()
                    if not self.registration_open:
                        self.bot.reply_to(message, 'Нет активной записи на игровой вечер.')
                        return
                    if user:
                        username = user[0]
                        cursor.execute('''
                        SELECT * FROM registrations WHERE username = ?
                        ''', (username,))
                        existing_registration = cursor.fetchone()

                        if existing_registration:
                            cursor.execute('''
                            UPDATE registrations SET event_time = ? WHERE username = ?
                            ''', (event_time, username))
                        else:
                            cursor.execute('''
                            INSERT INTO registrations (username, event_time)
                            VALUES (?, ?)
                            ''', (username, event_time))

                        self.conn.commit()

                        self.send_registration_list(message)
                    else:
                        self.bot.reply_to(message, 'Сначала зарегистрируйтесь с помощью команды /register '
                                                   '<Ваш никнейм>.')
        except sqlite3.Error:
            self.bot.reply_to(message, 'Произошла ошибка при записи на игровой вечер.')

    def invite_registration(self, username: str, event_time: str, message: Message) -> None:
        try:
            with self.lock:
                with self.conn:
                    cursor = self.conn.cursor()

                    if not self.registration_open:
                        self.bot.reply_to(message, 'Нет активной записи на игровой вечер.')
                        return

                    cursor.execute('''
                    SELECT * FROM registrations WHERE username = ?
                    ''', (username,))
                    existing_registration = cursor.fetchone()

                    if existing_registration:
                        cursor.execute('''
                        UPDATE registrations SET event_time = ? WHERE username = ?
                        ''', (event_time, username))
                    else:
                        cursor.execute('''
                        INSERT INTO registrations (username, event_time)
                        VALUES (?, ?)
                        ''', (username, event_time))

                    self.conn.commit()

                    self.send_registration_list(message)

        except sqlite3.Error:
            self.bot.reply_to(message, 'Произошла ошибка при записи на игровой вечер.')

    def cancel_registration_by_id(self, tg_user_id: int, message: Message) -> None:
        try:
            with self.lock:
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute('''
                    SELECT username FROM users WHERE tg_user_id = ?
                    ''', (tg_user_id,))
                    user = cursor.fetchone()

                    if not user:
                        self.bot.reply_to(message, 'Вы не зарегистрированы на игровой вечер.')
                        return

                    username = user[0]
                    cursor.execute('''
                    SELECT * FROM registrations WHERE username = ?
                    ''', (username,))
                    existing_registration = cursor.fetchone()

                    if existing_registration:
                        cursor.execute('''
                        DELETE FROM registrations WHERE username = ?
                        ''', (username,))
                        self.conn.commit()

                        self.send_registration_list(message)
                    else:
                        self.bot.reply_to(message, 'У вас нет активной записи на игровой вечер.')
        except sqlite3.Error:
            self.bot.reply_to(message, 'Произошла ошибка при отмене записи на игровой вечер.')

    def cancel_registration_by_username(self, username: str, message: Message) -> None:
        try:
            with self.lock:
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute('''
                    SELECT * FROM registrations WHERE username = ?
                    ''', (username,))
                    existing_registration = cursor.fetchone()

                    if existing_registration:
                        cursor.execute('''
                        DELETE FROM registrations WHERE username = ?
                        ''', (username,))
                        self.conn.commit()

                        self.send_registration_list(message)
                    else:
                        self.bot.reply_to(message, 'У этого игрока нет активной записи на игровой вечер.')
        except sqlite3.Error:
            self.bot.reply_to(message, 'Произошла ошибка при отмене записи на игровой вечер.')

    def send_registration_list(self, message: Message) -> None:
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT username, event_time
            FROM registrations
            ORDER BY registration_time
            ''')
            registrations = cursor.fetchall()

            registration_list = '\n'.join(
                [f'{i + 1}. {reg[0]}' + (f' {reg[1]}' if reg[1] != self.time else '') for i, reg in
                 enumerate(registrations)]
            )
            registration_state = 'открыта' if len(registrations) < 12 else 'закрыта'
            self.bot.reply_to(message, f'{self.date}, Запись {registration_state}! 😎\n\n{registration_list}\n\n🕐 '
                              f'{self.time}\n🗺 {self.location}')
            if len(registrations) == 12:
                self.close_registration()

    def start_polling(self) -> None:
        print('Running telebot...')
        self.bot.polling(none_stop=True)

    def stop(self) -> None:
        self.conn.close()


if __name__ == '__main__':
    # TOKEN = os.getenv('TOKEN')
    TOKEN = '7489778031:AAFW7ZxD4H3wQcQ4rMmSOOFFzY_-4vRCeMg'
    bot = MafiaBot(TOKEN)
    try:
        bot.start_polling()
    except KeyboardInterrupt:
        bot.stop()
