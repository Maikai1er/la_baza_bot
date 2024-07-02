from telebot import TeleBot
from telebot.types import Message
import sqlite3
import threading
from date_formatter import format_date_russian


class MafiaBot:
    def __init__(self, token: str):
        self.bot = TeleBot(token)
        self.conn = sqlite3.connect('event.db', check_same_thread=False, timeout=10)
        self.lock = threading.Lock()
        self.create_tables()
        self.setup_handlers()
        self.date = 'default date'
        self.time = '18:00'
        self.location = 'https://maps.app.goo.gl/LLHVqSW4Do9ALm5R8?g_st=atm'
        self.registration_open = False

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
        @self.bot.message_handler(commands=['start'])
        def handle_start(message: Message):
            self.bot.reply_to(message, 'Добро пожаловать! Используйте /help для списка команд.')

        @self.bot.message_handler(commands=['help'])
        def handle_help(message: Message):
            self.bot.reply_to(message, 'Доступные команды:\n'
                                       '/start - Начать взаимодействие с ботом\n'
                                       '/help - Список команд\n'
                                       '/register <Ваш ник> - Зарегистрироваться\n'
                                       '/join <Время> - Записаться на мероприятие\n'
                                       '/open <Дата> [Место] [Время] - Открыть запись на мероприятие\n'
                                       '/clear - Очистить список зарегистрированных участников')

        @self.bot.message_handler(commands=['register'])
        def handle_register(message: Message):
            try:
                username = message.text.split(maxsplit=1)[1]
                self.register_user(message.from_user.id, username, message)
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
                self.bot.reply_to(message, 'Неверный формат команды. Используйте /join <Время>.')

        @self.bot.message_handler(commands=['open'])
        def handle_open(message: Message):
            try:
                data = message.text.split(maxsplit=1)[1]
                self.start_registration(data, message)
            except IndexError:
                self.bot.reply_to(message, 'Неверный формат команды. Используйте /open <Дата> [Место] [Время].')

        @self.bot.message_handler(commands=['clear'])
        def handle_clear(message: Message):
            self.clear_registrations(message)

    def start_registration(self, data: str, message: Message) -> None:
        self.open_registration()
        data_list = data.split(' ')
        self.date = format_date_russian(data_list[0])
        if len(data_list) > 1:
            self.location = data_list[1]
        if len(data_list) > 2:
            self.time = data_list[2]
        self.bot.reply_to(message, f'{self.date}, Запись открыта! 😎\n\n🕐 {self.time}\n🗺 {self.location}')

    def register_user(self, tg_user_id: int, username: str, message: Message) -> None:
        try:
            with self.lock:
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute('''
                    INSERT OR REPLACE INTO users (tg_user_id, username)
                    VALUES (?, ?)
                    ''', (tg_user_id, username.capitalize()))
                    self.conn.commit()
            self.bot.reply_to(message, f'Вы успешно зарегистрированы под ником {username.capitalize()}!')
        except sqlite3.Error as e:
            self.bot.reply_to(message, f'Произошла ошибка при регистрации: {e}')

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
                                          f'{self.date}, Запись открыта! 😎\n\n{registration_list}\n\n🕐 {self.time}\n🗺 {self.location}')
                        if len(registrations) > 12:
                            self.close_registration()
                    else:
                        self.bot.reply_to(message, 'Сначала зарегистрируйтесь с помощью команды /register <Ваш ник>.')
        except sqlite3.Error as e:
            self.bot.reply_to(message, f'Произошла ошибка при записи на мероприятие: {e}')

    def clear_registrations(self, message: Message) -> None:
        try:
            with self.lock:
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute('DELETE FROM registrations')
                    self.conn.commit()
            self.bot.reply_to(message, 'Список зарегистрированных успешно очищен!')
        except sqlite3.Error as e:
            self.bot.reply_to(message, f'Произошла ошибка при очистке списка зарегистрированных: {e}')

    def start_polling(self) -> None:
        print('Running telebot...')
        self.bot.polling()

    def stop(self) -> None:
        self.conn.close()


if __name__ == "__main__":
    TOKEN = '7489778031:AAFW7ZxD4H3wQcQ4rMmSOOFFzY_-4vRCeMg'
    bot = MafiaBot(TOKEN)
    try:
        bot.start_polling()
    except KeyboardInterrupt:
        bot.stop()
