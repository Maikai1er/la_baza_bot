import datetime
import locale

locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')


def format_date(date_str):
    current_year = datetime.datetime.now().year

    date_obj = datetime.datetime.strptime(f'{date_str}.{current_year}', '%d.%m.%Y')

    formatted_date = date_obj.strftime('%d %B %Y (%A)')

    return formatted_date

