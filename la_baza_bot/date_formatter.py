from datetime import datetime
from babel.dates import format_date


def format_date_russian(date_str: str) -> str:
    current_year = datetime.now().year

    date_obj = datetime.strptime(f"{date_str}.{current_year}", "%d.%m.%Y")

    formatted_date = format_date(date_obj, "d MMMM yyyy (EEEE)", locale='ru')

    return formatted_date
