#!/opt/bin python3
# -*- coding: utf-8 -*-
import pickle
import time
from datetime import date as dt
from datetime import datetime, timedelta
from multiprocessing.context import Process

import holidays
import pytz

from data.menu import callback_inline, help, help_location, location
from data.methods import send_message
from data.model import make_request
from settings import CHAT_ID, ID_ADMIN, bot, PATH_BOT

LAST_TIME = 0


class ScheduleMessage():
    def try_send_schedule():
        while True:
            try:
                time.sleep(1)
                cur_time = int(time.time())

                if cur_time % 60 == 0:
                    check_note_and_send_message(cur_time)

            except Exception as exc:
                send_message(
                    ID_ADMIN, f'ошибка главного процесса - {exc}'
                )

    def start_process():
        p1 = Process(target=ScheduleMessage.try_send_schedule, args=())
        p1.start()


def read_file() -> float:
    """Считываем время из файла для проверки."""
    try:
        with open(f'{PATH_BOT}/check_time.pickle', 'rb') as fb:
            return pickle.load(fb)
    except OSError:
        return 0


def write_file(check_time: float) -> None:
    """Записываем текущее время в файл для проверки на следующем цикле."""
    with open(f'{PATH_BOT}/check_time.pickle', 'wb') as fb:
        pickle.dump(check_time, fb)


def check_note_and_send_message(cur_time):
    """Основной модуль оповещающий о событиях в чатах."""
    # проверка на пропуск минут в случаях отказов оборудования
    last_time_to_check = read_file()

    if cur_time - 60 > last_time_to_check:
        hour_start = datetime.fromtimestamp(
            last_time_to_check
        ).strftime('%H:%M')
        hour_end = datetime.fromtimestamp(
            cur_time
        ).strftime('%H:%M')
        send_message(
            ID_ADMIN,
            f"пропуск времени с {hour_start} до {hour_end}"
        )
    write_file(cur_time)

    # поиск в базе событий для вывода в текущую минуту
    date_today = dt.today()
    date_today_str = datetime.strftime(date_today, '%d.%m.%Y')
    date_birthday = datetime.strftime(date_today, '%d.%m')
    date_delta_birth = datetime.strftime(
        date_today + timedelta(days=7),
        '%d.%m'
    )
    tasks = make_request(
        'execute',
        """ SELECT date, time, type, task, id
            FROM tasks
            WHERE date=? OR date=? OR date=?
            ;""",
        (date_today_str, date_birthday, date_delta_birth),
        fetch='all'
    )
    del_id = []
    time_zone = pytz.timezone('Europe/Moscow')

    time_for_warning = datetime.strftime(
        datetime.now(time_zone) + timedelta(hours=4),
        '%H:%M'
    )
    cur_time_msk = datetime.strftime(datetime.now(time_zone), '%H:%M')

    if cur_time_msk == '08:00':
        ru_holidays = holidays.RU()
        if date_today in ru_holidays:
            hd = ru_holidays.get(date_today)
            bot.send_message(
                CHAT_ID,
                f'Господа, поздравляю вас с праздником - *{hd}*',
                parse_mode='Markdown'
            )
    elif cur_time_msk == '07:15':
        send_flag_note = False
        send_flag_birth = False
        send_flag_birth_ahead = False
        text_note = '*На сегодня в планах:*\n'
        text_birthday = f'*Не забудьте что, ежегодно {date_birthday}-ого:*\n'
        text_birthday_ahead = '*Не забудьте что, через 7 дней*\n'

        for item in tasks:
            if date_today_str in item and cur_time_msk in item:
                send_flag_note = True
                text_note += f'- {item[3]}\n'
                del_id.append(item[4])

            if date_birthday in item and cur_time_msk in item:
                send_flag_birth = True
                text_birthday += f'- {item[3]}\n'

            if date_delta_birth in item and cur_time_msk in item:
                if '🎁' in item[3]:
                    send_flag_birth_ahead = True
                    text_birthday_ahead += f'- {item[3]}\n'

        if send_flag_note:
            bot.send_message(
                CHAT_ID,
                text_note,
                parse_mode='Markdown'
            )
        if send_flag_birth:
            bot.send_message(
                CHAT_ID,
                text_birthday,
                parse_mode='Markdown'
            )
        if send_flag_birth_ahead:
            bot.send_message(
                CHAT_ID,
                text_birthday_ahead,
                parse_mode='Markdown'
            )

    if time_for_warning != '07:15':
        send_flag = False
        text_note = '*Напоминаю, что у вас есть планы 🧾:*\n'
        for item in tasks:
            if date_today_str and time_for_warning in item:
                text_note += f'- {item[3]}\n'
                send_flag = True
                del_id.append(item[4])
        if send_flag:
            bot.send_message(CHAT_ID, text_note, parse_mode='Markdown')

    if len(del_id) > 0:
        tuple_del_id = tuple(del_id) if len(del_id) > 1 else f'({del_id[0]})'

        make_request(
            'execute',
            """DELETE FROM tasks WHERE id IN %(list)s ;""" %
            {"list": tuple_del_id}
        )


@bot.message_handler(commands=['help'])
def handler_help(message):
    help(message)


@bot.message_handler(content_types=['location'])
def handler_location(message):
    location(message)


@bot.message_handler(commands=['help_location'])
def handler_help_location(message):
    help_location(message)


@bot.callback_query_handler(func=lambda call: True)
def handler_callback(call):
    callback_inline(call)


def main():
    ScheduleMessage.start_process()
    try:
        bot.delete_webhook()
        bot.polling(none_stop=True)
    except Exception as exc:
        bot.send_message(ID_ADMIN, f'ошибочка polling - {exc}')


if __name__ == '__main__':
    main()
