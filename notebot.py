#!/bin/env python3
# -*- coding: utf-8 -*-
import difflib
import os
import re
import sqlite3
import sys
import time
from datetime import date as dt
from datetime import datetime, timedelta
from multiprocessing.context import Process
from random import choice
from typing import Tuple

import holidays
import pytz
import requests
import schedule
from bs4 import BeautifulSoup
from telebot import TeleBot, types

from config import (CHAT_ID, ID_ADMIN, ID_CHILDREN, OW_API_ID, TOKEN,
                    YANDEX_GEO_API)

PATH_BOT = f'{os.path.dirname(sys.argv[0])}'

bot = TeleBot(TOKEN)

conn = sqlite3.connect(
    f'{PATH_BOT}/data_for_notebot.db', check_same_thread=False)
cur = conn.cursor()

cur.executescript("""   CREATE TABLE IF NOT EXISTS users(
                        userid INT PRIMARY KEY,
                        fname TEXT,
                        lname TEXT);
                    CREATE TABLE IF NOT EXISTS requests(
                    dateid INT PRIMARY KEY,
                    userid INT UNIQUE,
                    chatid INT,
                    messegeid INT);
                        CREATE TABLE IF NOT EXISTS tasks(
                        id INT PRIMARY KEY,
                        date TEXT,
                        time TEXT,
                        type TEXT,
                        task TEXT,
                        userid INT);
                    CREATE TABLE IF NOT EXISTS geolocation(
                    iddate INT PRIMARY KEY,
                    userid INT,
                    longitude TEXT,
                    latitude TEXT);
                        CREATE TABLE IF NOT EXISTS reactions(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        word TEXT,
                        answer TEXT);
                    CREATE TABLE IF NOT EXISTS checktime(
                    chtime INT PRIMARY KEY,
                    test TEXT UNIQUE);
                    """)
conn.commit()


class ParsingMessege:
    """Разбираем сообщение на комплектующие."""
    __slots__ = ('date', 'message', 'time', 'type_note')

    def __init__(self,
                 date: str,
                 message: str,
                 time: str,
                 type_note: str,
                 ) -> None:
        self.date = date
        self.message = message
        self.time = time
        self.type_note = type_note

    def add_todo(self, user_id: int) -> bool:
        """Добавляем задачу в БД."""
        cur.execute(""" SELECT id, date, time, task
                        FROM tasks
                        WHERE date=?
                    ;""", (self.date,))
        tasks = cur.fetchall()

        if len(tasks) > 0:
            for item in tasks:
                simil = similarity(item[3], self.message)
                if simil > 0.618:
                    return False
        id = round(time.time() * 100000)
        new_tasks = (id, self.date, self.time,
                     self.type_note, self.message, user_id)

        cur.execute(
            """INSERT INTO tasks VALUES(?, ?, ?, ?, ?, ?);""",
            new_tasks
            )
        conn.commit()
        return True


class ScheduleMessage():
    def try_send_schedule():
        while True:
            schedule.run_pending()
            time.sleep(1)

    def start_process():
        p1 = Process(target=ScheduleMessage.try_send_schedule, args=())
        p1.start()


def getter_data_for_parsing_messege(message):
    type_note = 'todo'

    if re.search(r'\d+[./-]\d+[./-]\d+', message):
        date_found = re.search(r'\d+[./-]\d+[./-]\d+', message).group()
        date_found = re.sub(r'[/-]', '.', date_found)

        if len(date_found.split(".")[2]) == 2:
            year = f'20{date_found.split(".")[2]}'
        else:
            year = date_found.split(".")[2]

        date = datetime(int(year), int(date_found.split(".")[
                        1]), int(date_found.split(".")[0]))
        date_str = datetime.strftime(date, '%d.%m.%Y')

    elif re.search(r'\d+[./-]\d+', message):
        date_found = re.search(r'\d+[./-]\d+', message).group()
        date = datetime(2000, int(date_found.split(
            ".")[1]), int(date_found.split(".")[0]))
        date_str = datetime.strftime(date, '%d.%m')
        type_note = 'birthday'

    elif re.search(r'[Сс]егодня|[Зз]автра', message):
        date_found = re.search(r'[Сс]егодня|[Зз]автра', message).group()
        today = datetime.strftime(dt.today(), '%d.%m.%Y')
        tomorrow = datetime.strftime(
            dt.today() + timedelta(days=1), '%d.%m.%Y'
            )
        near_future = {
            'сегодня': today,
            'завтра': tomorrow,
            }
        date_str = near_future[date_found.lower()]
    else:
        date_found = ''
        date_str = None

    if re.search(r'\d+[:]\d{2}', message):
        time_found = re.search(r'\d+[:]\d{2}', message).group()
        time = datetime(2000, 1, 1, int(time_found.split(":")[
                        0]), int(time_found.split(":")[1]))
        time_str = datetime.strftime(time, '%H:%M')
    else:
        time_str = '07:15'

    message_without_date = re.sub(date_found, '', message)
    message_without_date = re.sub(
        r'\s+', ' ', message_without_date
        ).strip()

    return [date_str, message_without_date, time_str, type_note]


def replace_messege_id(user_id: int, messege_id: int, chat_id: int) -> None:
    """Заменяем последний ID сообщения user в БД."""
    iddate = round(time.time() * 100000)
    new_request = (iddate, user_id, chat_id, messege_id)
    cur.execute("REPLACE INTO requests VALUES(?, ?, ?, ?);", new_request)
    conn.commit()


@bot.message_handler(commands=['help'])
def help(message):
    """Выводим кнопки основного меню на экран."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    add_note = types.InlineKeyboardButton(
        text="💬 добавить запись", callback_data='add'
        )
    del_note = types.InlineKeyboardButton(
        text="❌ удалить запись", callback_data='del'
        )
    get_note_random = types.InlineKeyboardButton(
        text="🙏 отработать провинность", callback_data='random'
        )
    get_all_birthdays = types.InlineKeyboardButton(
        "🚼 календарь рождений", callback_data='birthdays'
        )
    get_note_on_date = types.InlineKeyboardButton(
        "📅 планы на дату", callback_data='show'
        )
    get_all_note = types.InlineKeyboardButton(
        "📝 все планы", callback_data='show_all'
        )
    get_joke = types.InlineKeyboardButton("🎭 анекдот", callback_data='joke')
    get_many_joke = types.InlineKeyboardButton(
        "🎪 много анекдотов", callback_data='joke_many'
        )
    where_to_go = types.InlineKeyboardButton(
        "🏄 список мероприятий в СПб", callback_data='where_to_go'
        )

    keyboard.add(add_note, del_note, get_note_random, get_all_birthdays,
                 get_note_on_date, get_all_note, get_joke, get_many_joke)
    keyboard.add(where_to_go)

    menu_text = (
        "* 💡  ГЛАВНОЕ МЕНЮ  💡 *".center(28, "~")
        + "\n"
        + f"для пользователя {message.from_user.first_name}".center(28, "~")
        )

    menu_id = bot.send_message(message.chat.id,
                               menu_text,
                               reply_markup=keyboard,
                               parse_mode='Markdown').message_id

    replace_messege_id(message.from_user.id, menu_id, message.chat.id)

    message_id = message.message_id
    bot.delete_message(message.chat.id, message_id)

    add_new_user = (message.from_user.id,
                    message.from_user.first_name,
                    message.from_user.last_name)

    cur.execute("""REPLACE INTO users VALUES(?, ?, ?);""", add_new_user)
    conn.commit()


@bot.message_handler(content_types=['location'])
def location(message):
    """Кнопки меню погоды в только личном чате с ботом"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    weather_per_day = types.InlineKeyboardButton(
        text="🌈 погода сейчас", callback_data='weather_per_day'
        )
    get_weather_for_4_day = types.InlineKeyboardButton(
        text="☔️ прогноз погоды на 4 дня", callback_data='weather'
        )
    get_my_position = types.InlineKeyboardButton(
        text="🛰 моя позиция для группы", callback_data='my_position'
        )
    keyboard.add(weather_per_day, get_weather_for_4_day, get_my_position)

    menu_text = "* 💡  МЕНЮ ПОГОДЫ  💡 *".center(28, "~")

    menu_id = bot.send_message(message.chat.id,
                               menu_text,
                               reply_markup=keyboard,
                               parse_mode='Markdown').message_id

    chat_id = message.chat.id
    lat = message.location.latitude
    lon = message.location.longitude

    replace_messege_id(message.from_user.id, menu_id, chat_id)

    iddate = round(time.time() * 100000)
    geo = (iddate, message.from_user.id, lon, lat)
    cur.execute("""INSERT INTO geolocation VALUES(?, ?, ?, ?);""", geo)
    conn.commit()

    message_id = message.message_id
    bot.delete_message(message.chat.id, message_id)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    """Распределяем функции согласно нажатой кнопки."""
    message = call.message

    cur.execute(""" SELECT MAX(dateid), chatid, messegeid
                    FROM requests
                    WHERE userid=? and chatid=?
                    ;""", (call.from_user.id,  message.chat.id))
    menu_id = cur.fetchall()
    bot.delete_message(menu_id[0][1], menu_id[0][2])

    if call.data == 'random':
        message.from_user.id = call.from_user.id
        message.from_user.first_name = call.from_user.first_name
        add_random_task(message)
    elif call.data == 'birthdays':
        message.from_user.first_name = call.from_user.first_name
        show_all_birthdays(message)
    elif call.data == 'show_all':
        message.from_user.first_name = call.from_user.first_name
        show_all_notes(message)
    elif call.data == 'joke':
        show_joke(message)
    elif call.data == 'joke_many':
        show_joke_many(message)
    elif call.data == 'add':
        req_text = (f'*{call.from_user.first_name}*,'
                    'введите текст заметки с датой и временем')
        msg = bot.send_message(message.chat.id,
                               req_text,
                               parse_mode='Markdown')

        replace_messege_id(call.from_user.id, msg.message_id, message.chat.id)

        bot.register_next_step_handler(msg, add_notes)
    elif call.data == 'del':
        req_text = (f'*{call.from_user.first_name}*,'
                    ' введите дату и фрагмент текста заметки для её удаления')
        msg = bot.send_message(message.chat.id,
                               req_text,
                               parse_mode='Markdown')

        replace_messege_id(call.from_user.id, msg.message_id, message.chat.id)

        bot.register_next_step_handler(msg, del_note)
    elif call.data == 'show':
        req_text = (f'*{call.from_user.first_name}*,'
                    ' введите нужную дату для отображения заметок')
        msg = bot.send_message(message.chat.id,
                               req_text,
                               parse_mode='Markdown')

        replace_messege_id(call.from_user.id, msg.message_id, message.chat.id)

        bot.register_next_step_handler(msg, show_note_on_date)
    elif call.data == 'where_to_go':
        where_to_go(message)
    elif call.data == 'weather':
        message.from_user.id = call.from_user.id
        weather_forecast(message)
    elif call.data == 'weather_per_day':
        message.from_user.id = call.from_user.id
        current_weather(message)
    elif call.data == 'my_position':
        message.from_user.first_name = call.from_user.first_name
        message.from_user.id = call.from_user.id
        my_current_geoposition(message)


def where_to_go(message):
    """Опрос api kudago.com с формированием списка событий в СПб."""
    try:
        date_yesterday = dt.today() - timedelta(days=1)
        date_tomorrow = dt.today() + timedelta(days=1)
        date_yesterday = time.mktime(date_yesterday.timetuple())
        date_tomorrow = time.mktime(date_tomorrow.timetuple())

        resp = requests.get('https://kudago.com/public-api/v1.4/events/', {
            'actual_since': date_yesterday,
            'actual_until': date_tomorrow,
            'location': 'spb',
            'is_free': True,
        })

        next_data = resp.json()

        date_today = datetime.strftime(dt.today(), '%Y-%m-%d')
        text = ('[BCЕ МЕРОПРИЯТИЯ НА СЕГОДНЯ](https://kudago.com/spb/festival/'
                f'?date={date_today}&hide_online=y&only_free=y)\n\n')

        excluded_list = ['197880', '198003', '187745', '187466', '187745']

        for item in next_data['results']:
            if item['id'] not in excluded_list:
                text += (f"- {item['title'].capitalize()} [>>>]"
                         f"(https://kudago.com/spb/event/{item['slug']}/)\n")
                text += '-------------\n'

        bot.send_message(message.chat.id, text, parse_mode='Markdown')

    except Exception as exc:
        bot.send_message(message.chat.id, f'ошибочка вышла - {exc}')


@bot.message_handler(commands=['help_locatoin'])
def help_locatoin(message):
    """Создаём кнопку для получения геокоординат в его личном чате."""

    keyboard = types.ReplyKeyboardMarkup(row_width=1,
                                         resize_keyboard=True)
    button_geo = types.KeyboardButton(
        text="☀️ получить погоду и 👣 моё местоположение",
        request_location=True
        )

    keyboard.add(button_geo)
    bot.send_message(message.chat.id,
                     'появилась кнопочка погоды по Вашим координатам',
                     reply_markup=keyboard)
    message_id = message.message_id
    bot.delete_message(message.chat.id, int(message_id))


def get_address_from_coords(coords: str) -> str:
    """Опрос api geocode-maps.yandex для получения адреса местонахождения."""
    params = {
        "apikey": YANDEX_GEO_API,
        "format": "json",
        "lang": "ru_RU",
        "kind": "house",
        "geocode": coords,
        }
    try:
        r = requests.get(
            url="https://geocode-maps.yandex.ru/1.x/", params=params
            )

        json_data = r.json()

        return json_data["response"]["GeoObjectCollection"][
            "featureMember"][0]["GeoObject"][
            "metaDataProperty"]["GeocoderMetaData"][
            "AddressDetails"]["Country"]["AddressLine"]

    except Exception as exc:
        return exc


def status_weather(description_weather: str) -> str:
    """Добавление картинки в описание."""
    try:
        dict_weather = {
            'ясно': ' ☀️ ясно',
            'переменная облачность': ' 🌤 переменная облачность',
            'небольшая облачность': ' 🌤 переменная облачность',
            'облачно с прояснениями': ' ⛅️ облачно с прояснениями',
            'пасмурно': ' ☁️ пасмурно',
            'небольшой дождь': ' 🌦 небольшой дождь',
            'сильный дождь': ' ⛈ сильный дождь',
            'дождь': ' 🌧 дождь',
            }
        return dict_weather[description_weather]

    except Exception:
        return description_weather


def get_geo_coordinates(user_id: int) -> Tuple[int, str, str]:
    """Считывание последних геокоординат User из БД."""
    cur.execute(""" SELECT MAX(iddate), longitude, latitude
                    FROM geolocation
                    WHERE userid=?
                    ;""", (user_id,))
    return cur.fetchone()


def my_current_geoposition(message):
    """Вывод адреса местонахождения в группу."""
    coordinates = get_geo_coordinates(message.from_user.id)
    geo = f"{coordinates[1]},{coordinates[2]}"

    send_text = ("Согласно полученных геокоординат, "
                 f"{message.from_user.first_name} находится:\n"
                 f"[{get_address_from_coords(geo)}]"
                 "(https://yandex.ru/maps/?whatshere[point]="
                 f"{geo}&whatshere[zoom]=17)\n")

    bot.send_message(CHAT_ID, send_text, parse_mode='Markdown')


def current_weather(message):
    """Вывод погоды по текущим геокоординатам."""
    coordinates = get_geo_coordinates(message.from_user.id)
    try:
        res = requests.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params={
                'lat': coordinates[2],
                'lon': coordinates[1],
                'units': 'metric',
                'lang': 'ru',
                'APPID': OW_API_ID
                }
            )
        data = res.json()

        wind_directions = (
            "Сев", "Сев-Вост", "Вост", "Юго-Вост",
            "Южный", "Юго-Зап", "Зап", "Сев-Зап"
            )
        direction = (int((data['wind']['speed']) + 22.5) // 45 % 8)
        wind_speed = int(data['wind']['speed'])
        pressure = round(int(data['main']['pressure']*0.750063755419211))

        weather = [
            f" *{status_weather(data['weather'][0]['description'])}*",
            f" 💧 влажность: *{data['main']['humidity']}*%",
            f" 🌀 давление:   *{pressure}*мм рт.ст",
            f" 💨 ветер: *{wind_speed}м/сек ⤗ {wind_directions[direction]}*",
            f" 🌡 текущая: *{'{0:+3.0f}'.format(data['main']['temp'])}*°C",
            f" 🥶 мин:  *{'{0:+3.0f}'.format(data['main']['temp_min'])}*°C",
            f" 🥵 макс: *{'{0:+3.0f}'.format(data['main']['temp_max'])}*°C"
        ]

        st = "По данным ближайшего метеоцентра сейчас на улице:\n"
        max_len = max(len(x) for x in weather)
        for item in weather:
            st += (f'{item.rjust(max_len, "~")}\n')

        bot.send_message(message.chat.id, st, parse_mode='Markdown')

    except Exception as exc:
        bot.send_message(message.chat.id, f'ошибочка вышла - {exc}')


def weather_forecast(message):
    """Вывод прогноза погоды на 4 дня по последним User геокоординатам."""
    coordinates = get_geo_coordinates(message.from_user.id)

    try:
        res = requests.get(
            "http://api.openweathermap.org/data/2.5/forecast?",
            params={
                'lat': coordinates[2],
                'lon': coordinates[1],
                'units': 'metric',
                'lang': 'ru',
                'APPID': OW_API_ID
                }
            )
        data = res.json()

        sunrise_time = datetime.utcfromtimestamp(
            int(data['city']['sunrise']) + int(data['city']['timezone']))
        sunset_time = datetime.utcfromtimestamp(
            int(data['city']['sunset']) + int(data['city']['timezone']))

        city = data['city']['name']
        text_weather = f"Прогноз в месте с названием\n*{city}*:\n"

        for record in range(0, 40, 8):
            temp_max_min_day = []
            temp_max_min_night = []

            date_j = data['list'][record]['dt_txt'][:10]
            text_weather += f"*{date_j}*\n".rjust(25, '~')

            description = status_weather(
                data['list'][record]['weather'][0]['description'])
            text_weather += f"*{description}*\n"

            for i in range(40):
                if (data['list'][i]['dt_txt'][:10]
                        == data['list'][record]['dt_txt'][:10]):

                    if (sunset_time.hour
                            > int(data['list'][i]['dt_txt'][11:13])
                            > sunrise_time.hour):

                        temp_max_min_day.append(
                            data['list'][i]['main']['temp_min']
                            )
                        temp_max_min_day.append(
                            data['list'][i]['main']['temp_max']
                            )
                    else:
                        temp_max_min_night.append(
                            data['list'][i]['main']['temp_min'])
                        temp_max_min_night.append(
                            data['list'][i]['main']['temp_max'])

            if len(temp_max_min_day) > 0:
                text_weather += (
                    f"🌡🌞 *{'{0:+3.0f}'.format(max(temp_max_min_day))}* "
                    f"... *{'{0:+3.0f}'.format(min(temp_max_min_day))}*°C\n")

            if len(temp_max_min_night) > 0:
                text_weather += (
                    f"      🌙 *{'{0:+3.0f}'.format(max(temp_max_min_night))}* "
                    f"... *{'{0:+3.0f}'.format(min(temp_max_min_night))}*°C\n")
            coeff_celsia = 0.750063755419211
            pressure_c = int(
                data['list'][record]['main']['pressure']*coeff_celsia)
            text_weather += (f"давление *{pressure_c}*мм рт.ст\n")

        text_weather += "-\n".rjust(30, '-')
        text_weather += f"      ВОСХОД в *{sunrise_time.strftime('%H:%M')}*\n"
        text_weather += f"      ЗАКАТ     в *{sunset_time.strftime('%H:%M')}*"
        bot.send_message(message.chat.id, text_weather, parse_mode='Markdown')

    except Exception as exc:
        bot.send_message(message.chat.id, f'ошибочка вышла - {exc}')
        pass


def similarity(s1: str, s2: str) -> float:
    """Сравнение записей в модуле difflib
       [https://docs.python.org/3/library/difflib.html]."""
    normalized1 = s1.lower()
    normalized2 = s2.lower()
    matcher = difflib.SequenceMatcher(None, normalized1, normalized2)
    return matcher.ratio()


def add_notes(message):
    """Добавление записи в БД."""
    try:
        data = getter_data_for_parsing_messege(message.text)
        pars_mess = ParsingMessege(*data)
        date = pars_mess.date
        t_time = pars_mess.time
        type_note = pars_mess.type_note
        task = pars_mess.message
        user_id = message.from_user.id

        if date is None:
            text_send = (
                f'Дата в запросе *<{message.text}>* '
                'не найдена, напоминание не записано'
                        )
            bot.send_message(message.chat.id,
                             text_send, parse_mode='Markdown')

        elif pars_mess.add_todo(user_id) is False:
            text_send = (
                'Есть более чем на 61% схожая запись на дату'
                f' *{date}*,\nсообщение *<{task}>* не добавлено'
                        )
            bot.send_message(message.chat.id,
                             text_send, parse_mode='Markdown')
        else:
            if type_note == 'todo':
                text_send = (
                    f'{message.from_user.first_name}, напоминание, *<{task}>* '
                    f'добавлена на дату <{date}> на время <{t_time}>'
                            )
                bot.send_message(message.chat.id,
                                 text_send, parse_mode='Markdown')

            elif type_note == 'birthday':
                text_send = (
                    f'{message.from_user.first_name}, ежегодное '
                    f'напоминание о *<{task}>* добавлена на дату <{date}>'
                            )
                bot.send_message(message.chat.id,
                                 text_send, parse_mode='Markdown')

        cur.execute(""" SELECT MAX(dateid), chatid, messegeid
                        FROM requests
                        WHERE userid=? and chatid=?
                    ;""", (user_id, message.chat.id))
        question_id = cur.fetchall()
        bot.delete_message(question_id[0][1], question_id[0][2])

        message_id = message.message_id
        bot.delete_message(message.chat.id, message_id)

    except Exception as exc:
        bot.send_message(message.chat.id, f'ошибочка вышла - {exc}')


def del_note(message):
    """Удаление записи из БД."""
    try:
        command_text = re.sub(r'/del ', '', message.text)
        pars_mess = ParsingMessege(command_text)
        date = pars_mess.date
        task = pars_mess.massege

        if date is None:
            send_text = (
                f'*{message.from_user.first_name}*, '
                'дата в запросе не найдена! Начните операцию заново.')
            bot.send_message(message.chat.id,
                             send_text, parse_mode='Markdown')
        else:
            cur.execute(""" SELECT id, task
                            FROM tasks
                            WHERE date=? AND task LIKE ('%' || ? || '%')
                        ;""", (date, task))
            tasks = cur.fetchone()

            if tasks is None:
                send_text = (
                    f'{message.from_user.first_name}, '
                    f'нет заметок с текстом *<{task}>* на эту дату!'
                )
                bot.send_message(message.chat.id,
                                 send_text, parse_mode='Markdown')
            else:
                cur.execute("""DELETE FROM tasks WHERE id=?""", (tasks[0],))
                conn.commit()
                send_text = (
                    f"{message.from_user.first_name}, "
                    f"запись *<{tasks[1]}>* на дату {date} удалена")

                bot.send_message(message.chat.id,
                                 send_text, parse_mode='Markdown')

        cur.execute(""" SELECT MAX(dateid), chatid ,messegeid
                        FROM requests
                        WHERE userid=? and chatid=?
                    ;""", (message.from_user.id, message.chat.id))
        question_id = cur.fetchone()
        bot.delete_message(question_id[1], question_id[2])

        message_id = message.message_id
        bot.delete_message(message.chat.id, int(message_id))

    except Exception as exc:
        bot.send_message(message.chat.id, f'ошибочка вышла - {exc}')
        pass


def show_note_on_date(message):
    """Вывод записей из БД на конкретую дату."""
    command_text = re.sub(r'/show ', '', message.text)
    pars_mess = ParsingMessege(command_text)
    date = pars_mess.date
    date_every_year = '.'.join([date.split('.')[0], date.split('.')[1]])

    if date is None:
        send_text = (
            f'*{message.from_user.first_name}*, '
            'дата в запросе не найдена! Начните операцию сначала.'
        )
        bot.send_message(
            message.chat.id,
            send_text,
            parse_mode='Markdown')
    else:
        cur.execute(""" SELECT date, type, task
                        FROM tasks
                        WHERE date=? or date=?
                    ;""", (date_every_year, date))
        tasks = cur.fetchall()

        text_notes = (f'*{message.from_user.first_name}, '
                      'на {date} запланировано:*\n')
        send_note = False
        text_birthday = (
            f'*{message.from_user.first_name}, '
            'на выбранную дату {date} найдено ежегодное напоминание:*\n')
        send_birthday = False

        for item in tasks:
            if item[1] == 'todo':
                text_notes += f'- {item[2]}'
                send_note = True
            if item[1] == 'birthday':
                text_birthday += f'- {item[2]}'
                send_birthday = True

        if send_note:
            bot.send_message(message.chat.id,
                             text_notes,
                             parse_mode='Markdown')
        if send_note and send_birthday:
            bot.send_message(message.chat.id,
                             'и ешё,',
                             parse_mode='Markdown')
        if send_birthday:
            bot.send_message(message.chat.id,
                             text_birthday,
                             parse_mode='Markdown')

    cur.execute(""" SELECT MAX(dateid), chatid, messegeid
                    FROM requests
                    WHERE userid=? and chatid=?
                ;""", (message.from_user.id, message.chat.id))
    question_id = cur.fetchone()
    bot.delete_message(question_id[1], question_id[2])

    message_id = message.message_id
    bot.delete_message(message.chat.id, int(message_id))


def sort_date(x: int) -> int:
    """Ключ фильтра для сортировки."""
    d = x.split(" - ")[0]
    sort_val = f'{d.split(".")[2]}{d.split(".")[1]}{d.split(".")[1]}'
    return int(sort_val)


def show_all_notes(message):
    """Вывод всех записей из БД."""
    note = []
    cur.execute(
        """ SELECT date, task
            FROM tasks
            WHERE type='todo' AND task NOT LIKE ('%' || 'с апогеем' || '%')
            ;""")
    tasks = cur.fetchall()

    for item in tasks:
        note.append(f'{item[0]} - {item[1]}')

    note.sort(key=sort_date)
    note_sort = (f'*{message.from_user.first_name}, '
                 'согласно запроса, в базе найдено:*\n')

    for n in note:
        note_sort = note_sort + f'{n}\n'

    bot.send_message(message.chat.id, note_sort, parse_mode='Markdown')


def show_all_birthdays(message):
    """Показать все дни рождения."""
    note = []
    cur.execute(""" SELECT date, task
                    FROM tasks
                    WHERE type='birthday'
                ;""")
    tasks = cur.fetchall()

    for item in tasks:
        note.append(f'{item[0]} - {item[1]}')

    note.sort(key=lambda x: int(f'{x[:5].split(".")[1]}{x[:5].split(".")[0]}'))
    note_sort = (f'*{message.from_user.first_name}, '
                 'согласно Вашего запроса, найдены ежегодные напоминания:*\n')

    for n in note:
        note_sort = note_sort + f'{n}\n'

    bot.send_message(message.chat.id, note_sort, parse_mode='Markdown')


def joke_parsing(id_user: int, all: bool = False) -> str | list[str]:
    """Парсинг сайта с анекдотами."""
    try:
        if id_user in ID_CHILDREN:
            resp = requests.get('https://anekdotbar.ru/dlya-detey/')
        else:
            resp = requests.get('https://anekdotbar.ru/')
        bs_data = BeautifulSoup(resp.text, "html.parser")
        an_text = bs_data.select('.tecst')
        response_list = []
        for x in an_text:
            joke = x.getText().strip().split('\n')[0]
            response_list.append(joke)
            response_all = ''
        if not all:
            return choice(response_list)
        else:
            for x in response_list:
                response_all += f'~ {x} \n\n'
            return response_all

    except Exception as exc:
        return f'ошибочка вышла - {exc}'


def show_joke(message):
    """Показать анекдот."""
    id_user = message.chat.id
    bot.send_message(message.chat.id, joke_parsing(id_user))


def show_joke_many(message):
    """Показать все распарсенные анекдоты."""
    id_user = message.chat.id
    bot.send_message(message.chat.id, joke_parsing(id_user, all=True))


def random_response_to_word(word: str) -> str:
    """Чтение из БД и возврат случайного задания по слову random."""
    cur.execute(""" SELECT answer
                    FROM reactions
                    WHERE word=?
                    ;""", (word, ))
    respons = cur.fetchall()
    return choice(respons)[0]


def add_random_task(message):
    """Добавление случайного задания на следующий день.
       Используется в случает провинности )."""
    choice_task = random_response_to_word('random')
    task = (
        f'задание "{choice_task}" '
        f'возложено на {message.from_user.first_name}'
    )
    date = datetime.strftime(dt.today() + timedelta(days=1), '%d.%m.%Y')
    data = getter_data_for_parsing_messege(f'{date} {task}')
    judgement = ParsingMessege(*data)
    judgement.add_todo(message.from_user.id)

    bot.send_message(
        message.chat.id,
        (f'Задача <{choice_task}> для '
         f'{message.from_user.first_name} добавлена на {date}')
    )


def check_words_list(list_with_word: list[str], answer: str) -> bool:
    """Поиск слова в списке."""
    for word in list_with_word:
        if word in answer:
            return True
    else:
        return False


@bot.message_handler(func=lambda message: True, content_types=['text'])
def text_ansvers(message):
    """Ищит некоторые слова в сообщениях пользователей."""
    if check_words_list(
            ['прив', 'здрав', 'добро'], message.text.lower()):

        bot.reply_to(message, random_response_to_word('привет'))

    elif check_words_list(
            ['делать'], message.text.lower()):

        bot.reply_to(message, random_response_to_word('делать'))

    elif check_words_list(
            ['делаешь', 'занимаешься'], message.text.lower()):

        bot.reply_to(message, random_response_to_word('делаешь'))

    elif check_words_list(
            ['дела', 'как ты', 'настроен'], message.text.lower()):

        bot.reply_to(message, random_response_to_word('дела'))

    return False


def check_note_and_send_message():
    """Основной модуль оповещающий о собыниях в чатах."""
    # проверка на пропуск минут в случаях отказов оборудования
    cur_time_tup = time.mktime(datetime.now().replace(
        second=0, microsecond=0).timetuple())

    cur.execute(""" SELECT chtime
                    FROM checktime
                ;""")
    last_time_to_check = cur.fetchone()

    if last_time_to_check is None:
        last_time_to_check = 0
    else:
        last_time_to_check = last_time_to_check[0]

    if cur_time_tup - 60 > last_time_to_check:
        hour_start = datetime.fromtimestamp(
            last_time_to_check).strftime('%H:%M')

        hour_end = datetime.fromtimestamp(cur_time_tup).strftime('%H:%M')

        bot.send_message(ID_ADMIN,
                         f"пропуск врмени с {hour_start} до {hour_end}")

    check_time = (cur_time_tup, 'ок')
    cur.execute("""REPLACE INTO checktime VALUES(?, ?);""", check_time)
    conn.commit()

    # поиск в базе событий для вывода в текущую минуту
    date = datetime.strftime(dt.today(), '%d.%m.%Y')
    date_birthday = datetime.strftime(dt.today(), '%d.%m')
    date_delta_birth = datetime.strftime(
        dt.today() + timedelta(days=7), '%d.%m')

    cur.execute(""" SELECT date, time, type, task, id
                    FROM tasks
                    WHERE date=? OR date=? OR date=?
                ;""", (date, date_birthday, date_delta_birth))
    tasks = cur.fetchall()

    del_id = []
    time_zone = pytz.timezone('Europe/Moscow')
    time_ahead = datetime.strftime(datetime.now(
        time_zone) + timedelta(hours=4), '%H:%M')
    send_flag = False
    text_note = '*Напоминаю, что через 4 часа запланировано:*\n'
    if not time_ahead == '07:15':
        for item in tasks:
            if date and time_ahead in item:
                text_note += f'- {item[3]}\n'
                send_flag = True
                del_id.append(item[4])
        if send_flag:
            bot.send_message(CHAT_ID, text_note, parse_mode='Markdown')

    cur_time_msk = datetime.strftime(datetime.now(time_zone), '%H:%M')

    if cur_time_msk == '07:15':
        send_flag_note = False
        send_flag_birth = False
        send_flag_birth_ahead = False
        text_note = '*На сегодня в планах:*\n'
        text_birthday = f'*Не забудьте что, ежегодно {date_birthday}-ого:*\n'
        text_birthday_ahead = '*Не забудьте что, через 7 дней*\n'

        for item in tasks:
            if date in item and cur_time_msk in item:
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
            bot.send_message(CHAT_ID, text_note, parse_mode='Markdown')
        if send_flag_birth:
            bot.send_message(CHAT_ID, text_birthday, parse_mode='Markdown')
        if send_flag_birth_ahead:
            bot.send_message(CHAT_ID, text_birthday_ahead,
                             parse_mode='Markdown')

        ru_holidays = holidays.RU()
        if dt.today() in ru_holidays:
            hd = ru_holidays.get(dt.today())
            bot.send_message(
                CHAT_ID, f'Господа, поздравляю вас с праздником - {hd}')

    if len(del_id) > 0:
        tuple_del_id = tuple(del_id) if len(del_id) > 1 else f'({del_id[0]})'
        cur.execute("""DELETE FROM tasks WHERE id IN %(list)s ;""" %
                    {"list": tuple_del_id})
        conn.commit()


check_note_and_send_message()


schedule.every(1).minutes.do(check_note_and_send_message)


if __name__ == '__main__':
    ScheduleMessage.start_process()
    try:
        bot.polling(none_stop=True)
    finally:
        pass
