# -*- coding: utf-8 -*-
import re
import sys
import sqlite3
import os
import time
from datetime import date as dt
from datetime import datetime, timedelta
from multiprocessing.context import Process
from random import choice
import difflib

import pytz
import requests
import schedule
from telebot import types, TeleBot
from bs4 import BeautifulSoup
import holidays

from config import *  # your bot config


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

    __slots__ = ('massege', 'date', 'time', 'type_note')

    def __init__(self, message):
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
        elif re.search(r'[Сс]егодня', message):
            date_found = re.search(r'[Сс]егодня', message).group()
            date_str = datetime.strftime(dt.today(), '%d.%m.%Y')
        elif re.search(r'[Зз]автра', message):
            date_found = re.search(r'[Зз]автра', message).group()
            date_str = datetime.strftime(
                dt.today() + timedelta(days=1), '%d.%m.%Y')
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

        self.massege = re.sub(r'\s+', ' ', message_without_date).strip()
        self.date = date_str
        self.time = time_str
        self.type_note = type_note


class ScheduleMessage():

    def try_send_schedule():
        while True:
            schedule.run_pending()
            time.sleep(1)

    def start_process():
        p1 = Process(target=ScheduleMessage.try_send_schedule, args=())
        p1.start()


class MyClass():

    def __init__(self, param):
        self.param = param


def get_messege_id(user_id, messege_id, chat_id):
    iddate = round(time.time() * 100000)
    new_request = (iddate, user_id, chat_id, messege_id)
    cur.execute("REPLACE INTO requests VALUES(?, ?, ?, ?);", new_request)
    conn.commit()


@bot.message_handler(commands=['help'])
def help(message):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    add_note = types.InlineKeyboardButton(
        text="💬 добавить запись", callback_data='add')
    del_note = types.InlineKeyboardButton(
        text="❌ удалить запись", callback_data='del')
    get_note_random = types.InlineKeyboardButton(
        text="🙏 отработать провинность", callback_data='random')
    get_all_birthdays = types.InlineKeyboardButton(
        "🚼 календарь рождений", callback_data='birthdays')
    get_note_on_date = types.InlineKeyboardButton(
        "📅 планы на дату", callback_data='show')
    get_all_note = types.InlineKeyboardButton(
        "📝 все планы", callback_data='show_all')
    get_joke = types.InlineKeyboardButton("🎭 анекдот", callback_data='joke')
    get_many_joke = types.InlineKeyboardButton(
        "🎪 много анекдотов", callback_data='joke_many')
    where_to_go = types.InlineKeyboardButton(
        "🏄 список мероприятий в СПб", callback_data='where_to_go')

    keyboard.add(add_note, del_note, get_note_random, get_all_birthdays,
                 get_note_on_date, get_all_note, get_joke, get_many_joke)
    keyboard.add(where_to_go)

    menu_id = bot.send_message(message.chat.id, f"* 💡 🔽  ГЛАВНОЕ МЕНЮ  🔽 💡 *\nдля пользователя {message.from_user.first_name}",
                               reply_markup=keyboard, parse_mode='Markdown').message_id

    get_messege_id(message.from_user.id, menu_id, message.chat.id)

    message_id = message.message_id
    bot.delete_message(message.chat.id, message_id)

    add_new_user = (message.from_user.id,
                    message.from_user.first_name,  message.from_user.last_name)
    cur.execute("""REPLACE INTO users VALUES(?, ?, ?);""", add_new_user)
    conn.commit()


@bot.message_handler(content_types=['location'])
def location(message):

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    weather_per_day = types.InlineKeyboardButton(
        text="🌈 погода сейчас", callback_data='weather_per_day')
    get_weather_for_4_day = types.InlineKeyboardButton(
        text="☔️ прогноз погоды на 4 дня", callback_data='weather')
    get_my_position = types.InlineKeyboardButton(
        text="🛰 моя позиция для группы", callback_data='my_position')
    keyboard.add(weather_per_day, get_weather_for_4_day, get_my_position)

    menu_id = bot.send_message(message.chat.id, f"* 💡 🔽  МЕНЮ ПОГОДЫ  🔽 💡 *",
                               reply_markup=keyboard, parse_mode='Markdown').message_id

    chat_id = message.chat.id
    lat = message.location.latitude
    lon = message.location.longitude

    get_messege_id(message.from_user.id, menu_id, chat_id)

    iddate = round(time.time() * 100000)
    geo = (iddate, message.from_user.id, lon, lat)
    cur.execute("""INSERT INTO geolocation VALUES(?, ?, ?, ?);""", geo)
    conn.commit()

    message_id = message.message_id
    bot.delete_message(message.chat.id, message_id)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
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
        msg = bot.send_message(message.chat.id,
                               f'*{call.from_user.first_name}*, введите текст заметки с датой и временем',
                               parse_mode='Markdown')

        get_messege_id(call.from_user.id, msg.message_id, message.chat.id)

        bot.register_next_step_handler(msg, add_notes)
    elif call.data == 'del':
        msg = bot.send_message(message.chat.id,
                               f'*{call.from_user.first_name}*, введите дату и фрагмент текста заметки для её удаления',
                               parse_mode='Markdown')

        get_messege_id(call.from_user.id, msg.message_id, message.chat.id)

        bot.register_next_step_handler(msg, del_note)
    elif call.data == 'show':
        msg = bot.send_message(message.chat.id,
                               f'*{call.from_user.first_name}*, введите нужную дату для отображения заметок',
                               parse_mode='Markdown')

        get_messege_id(call.from_user.id, msg.message_id, message.chat.id)

        bot.register_next_step_handler(msg, show_note_on_date)
    elif call.data == 'where_to_go':
        where_to_go(message)
    elif call.data == 'weather':
        message.from_user.id = call.from_user.id
        weather_forecast(message)
    elif call.data == 'weather_per_day':
        message.from_user.id = call.from_user.id
        current_weather_and_location(message)
    elif call.data == 'my_position':
        message.from_user.first_name = call.from_user.first_name
        message.from_user.id = call.from_user.id
        my_current_geoposition(message)


# api kudago.com для списка событий в СПб
def where_to_go(message):
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
        text = f'[BCЕ МЕРОПРИЯТИЯ НА СЕГОДНЯ](https://kudago.com/spb/festival/?date={date_today}&hide_online=y&only_free=y)\n\n'

        excluded_list = ['197880', '198003', '187745', '187466', '187745']

        for item in next_data['results']:
            if item['id'] not in excluded_list:
                text += f"- {item['title'].capitalize()} [>>>](https://kudago.com/spb/event/{item['slug']}/)\n"
                text += '-------------\n'

        bot.send_message(message.chat.id, text, parse_mode='Markdown')

    except Exception as E:
        bot.send_message(message.chat.id, f'ошибочка вышла - {E}')


@bot.message_handler(commands=['help_locatoin'])
def help_locatoin(message):
    try:
        keyboard = types.ReplyKeyboardMarkup(
            row_width=1, resize_keyboard=True, input_field_placeholder="\( ' _|_ ' )/")
        button_geo = types.KeyboardButton(
            text="☀️ получить погоду и 👣 моё местоположение", request_location=True)
        keyboard.add(button_geo)
        bot.send_message(
            message.chat.id, 'появилась кнопочка погоды по Вашим координатам', reply_markup=keyboard)
        message_id = message.message_id
        bot.delete_message(message.chat.id, int(message_id))
    except:
        message_id = message.message_id
        bot.delete_message(message.chat.id, int(message_id))


# api geocode-maps.yandex для текущего местонахождения
def get_address_from_coords(coords):
    PARAMS = {
        "apikey": YANDEX_GEO_API,
        "format": "json",
        "lang": "ru_RU",
        "kind": "house",
        "geocode": coords
    }
    try:
        r = requests.get(
            url="https://geocode-maps.yandex.ru/1.x/", params=PARAMS)
        json_data = r.json()
        address_str = json_data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"][
            "metaDataProperty"]["GeocoderMetaData"]["AddressDetails"]["Country"]["AddressLine"]
        return address_str
    except Exception:
        return "error"


def status_weather(description_weather):
    if description_weather == "ясно":
        return " ☀️ ясно"
    elif description_weather == "переменная облачность" or description_weather == "небольшая облачность":
        return " 🌤 переменная облачность"
    elif description_weather == "облачно с прояснениями":
        return " ⛅️ облачно с прояснениями"
    elif description_weather == "пасмурно":
        return " ☁️ пасмурно"
    elif description_weather == "небольшой дождь":
        return " 🌦 небольшой дождь"
    elif description_weather == "сильный дождь":
        return " 🌧 сильный дождь"
    else:
        return description_weather


def get_geo_coordinates(user_id):
    cur.execute(""" SELECT MAX(iddate), longitude, latitude
                    FROM geolocation
                    WHERE userid=?
                    ;""", (user_id,))
    geo = cur.fetchone()
    return geo


def my_current_geoposition(message):
    coordinates = get_geo_coordinates(message.from_user.id)
    geo = f"{coordinates[1]},{coordinates[2]}"

    bot.send_message(CHAT_ID, f"Согласно полученных геокоординат, {message.from_user.first_name} находится:\n\
[{get_address_from_coords(geo)}](https://yandex.ru/maps/?whatshere[point]={geo}&whatshere[zoom]=17)\n", parse_mode='Markdown')


def current_weather_and_location(message):
    coordinates = get_geo_coordinates(message.from_user.id)
    try:
        res = requests.get("http://api.openweathermap.org/data/2.5/weather",
                           params={'lat': coordinates[2], 'lon': coordinates[1], 'units': 'metric', 'lang': 'ru', 'APPID': OW_API_ID})
        data = res.json()

        wind_directions = ("Сев", "Сев-Вост", "Вост", "Юго-Вост",
                           "Южный", "Юго-Зап", "Зап", "Сев-Зап")
        direction = int(int((data['wind']['speed']) + 22.5) // 45 % 8)

        bot.send_message(message.chat.id, f"По данным ближайшего метеоцентра сейчас на улице:\n\
~ *{status_weather(data['weather'][0]['description'])}* ~\n\
     - 💧 влажность: *{data['main']['humidity']}*% \n \
    - ⚗️ давление:   *{round(int(data['main']['pressure']*0.750063755419211))}*мм рт.ст\n\
     - 💨 ветер: *{int(data['wind']['speed'])}м/сек ⤗ {wind_directions[direction]}*\n\
~ 🌡 текущая: *{'{0:+3.0f}'.format(data['main']['temp'])}*°C\n\
     - 🥶 мин:  *{'{0:+3.0f}'.format(data['main']['temp_min'])}*°C\n\
     - 🥵 макс: *{'{0:+3.0f}'.format(data['main']['temp_max'])}*°C\n\
        \n", parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "что-то пошло не так")
        pass


# прогноз погоды на 4 дня
def weather_forecast(message):
    coordinates = get_geo_coordinates(message.from_user.id)
    try:
        res = requests.get("http://api.openweathermap.org/data/2.5/forecast?",
                           params={'lat': coordinates[2], 'lon': coordinates[1], 'units': 'metric', 'lang': 'ru', 'APPID': OW_API_ID})
        data = res.json()

        sunrise_time = datetime.utcfromtimestamp(
            int(data['city']['sunrise']) + int(data['city']['timezone']))
        sunset_time = datetime.utcfromtimestamp(
            int(data['city']['sunset']) + int(data['city']['timezone']))

        text_weather = f"Прогноз в месте с названием\n*{data['city']['name']}*:\n"
        for record in range(0, 40, 8):
            temp_max_min_day = []
            temp_max_min_night = []
            text_weather += f"*{data['list'][record]['dt_txt'][:10]}*\n".rjust(
                25, '~')
            text_weather += f"*{status_weather(data['list'][record]['weather'][0]['description'])}*\n"
            for i in range(40):
                if data['list'][i]['dt_txt'][:10] == data['list'][record]['dt_txt'][:10]:
                    if sunset_time.hour > int(data['list'][i]['dt_txt'][11:13]) > sunrise_time.hour:
                        temp_max_min_day.append(
                            data['list'][i]['main']['temp_min'])
                        temp_max_min_day.append(
                            data['list'][i]['main']['temp_max'])
                    else:
                        temp_max_min_night.append(
                            data['list'][i]['main']['temp_min'])
                        temp_max_min_night.append(
                            data['list'][i]['main']['temp_max'])
            if len(temp_max_min_day) > 0:
                text_weather += f"🌡🌞 *{'{0:+3.0f}'.format(max(temp_max_min_day))}* ... *{'{0:+3.0f}'.format(min(temp_max_min_day))}*°C\n"
            if len(temp_max_min_night) > 0:
                text_weather += f"      🌙 *{'{0:+3.0f}'.format(max(temp_max_min_night))}* ... *{'{0:+3.0f}'.format(min(temp_max_min_night))}*°C\n"
            text_weather += f"давление *{int(data['list'][record]['main']['pressure']*0.750063755419211)}*мм рт.ст\n"
        text_weather += "-\n".rjust(30, '-')
        text_weather += f"      ВОСХОД в *{sunrise_time.strftime('%H:%M')}*\n"
        text_weather += f"      ЗАКАТ     в *{sunset_time.strftime('%H:%M')}*"
        bot.send_message(message.chat.id, text_weather, parse_mode='Markdown')
    except Exception as E:
        bot.send_message(message.chat.id, f'ошибочка вышла - {E}')
        pass


def similarity(s1, s2):
    normalized1 = s1.lower()
    normalized2 = s2.lower()
    matcher = difflib.SequenceMatcher(None, normalized1, normalized2)
    return matcher.ratio()


def add_todo(date, type_note, task, user_id, t_time='07:15'):

    cur.execute(""" SELECT id, date, time, task
                    FROM tasks
                    WHERE date=?
                ;""", (date,))
    tasks = cur.fetchall()

    if len(tasks) > 0:
        for item in tasks:
            simil = similarity(item[3], task)
            if simil > 0.618:
                return True

    id = round(time.time() * 100000)
    new_tasks = (id, date, t_time, type_note, task, user_id)

    cur.execute("""INSERT INTO tasks VALUES(?, ?, ?, ?, ?, ?);""", new_tasks)
    conn.commit()


def add_notes(message):
    try:
        command_text = re.sub(r'/add ', '', message.text)
        pars_mess = ParsingMessege(command_text)
        date = pars_mess.date
        t_time = pars_mess.time
        type_note = pars_mess.type_note
        task = pars_mess.massege
        user_id = message.from_user.id

        if date == None:
            bot.send_message(message.chat.id,
                             f'Дата в запросе *<{command_text}>* не найдена, напоминание не записано',
                             parse_mode='Markdown')

        elif add_todo(date, type_note, task, user_id, t_time):
            bot.send_message(message.chat.id,
                             f'Есть более чем на 61% схожая запись на дату *{date}*,\nсообщение *<{task}>* не добавлено',
                             parse_mode='Markdown')
        else:
            if type_note == 'todo':
                bot.send_message(message.chat.id,
                                 f'{message.from_user.first_name}, напоминание, *<{task}>* добавлена на дату <{date}> на время <{t_time}>',
                                 parse_mode='Markdown')

            elif type_note == 'birthday':
                bot.send_message(message.chat.id,
                                 f'{message.from_user.first_name}, ежегодное напоминание о *<{task}>* добавлена на дату <{date}>',
                                 parse_mode='Markdown')

        cur.execute(""" SELECT MAX(dateid), chatid, messegeid
                        FROM requests
                        WHERE userid=? and chatid=?
                    ;""", (user_id, message.chat.id))
        question_id = cur.fetchall()
        bot.delete_message(question_id[0][1], question_id[0][2])

        message_id = message.message_id
        bot.delete_message(message.chat.id, message_id)

    except Exception as E:
        bot.send_message(message.chat.id, f'ошибочка вышла - {E}')


def del_note(message):
    try:
        command_text = re.sub(r'/del ', '', message.text)
        pars_mess = ParsingMessege(command_text)
        date = pars_mess.date
        task = pars_mess.massege

        if date == None:
            bot.send_message(message.chat.id,
                             f'*{message.from_user.first_name}*, дата в запросе не найдена! Начните операцию заново.',
                             parse_mode='Markdown')
        else:
            cur.execute(""" SELECT id, task
                            FROM tasks
                            WHERE date=? AND task LIKE ('%' || ? || '%')
                        ;""", (date, task))
            tasks = cur.fetchone()

            if tasks == None:
                bot.send_message(
                    message.chat.id, f'{message.from_user.first_name}, нет заметок с текстом *<{task}>* на эту дату!')
            else:
                cur.execute("""DELETE FROM tasks WHERE id=?""", (tasks[0],))
                conn.commit()
                bot.send_message(message.chat.id,
                                 f"{message.from_user.first_name}, запись *<{tasks[1]}>* на дату {date} удалена", parse_mode='Markdown')

        cur.execute(""" SELECT MAX(dateid), chatid ,messegeid
                        FROM requests
                        WHERE userid=? and chatid=?
                    ;""", (message.from_user.id, message.chat.id))
        question_id = cur.fetchone()
        bot.delete_message(question_id[1], question_id[2])

        message_id = message.message_id
        bot.delete_message(message.chat.id, int(message_id))

    except Exception as E:
        bot.send_message(message.chat.id, f'ошибочка вышла - {E}')
        pass


def show_note_on_date(message):
    command_text = re.sub(r'/show ', '', message.text)
    pars_mess = ParsingMessege(command_text)
    date = pars_mess.date
    date_every_year = '.'.join([date.split('.')[0], date.split('.')[1]])

    if date == None:
        bot.send_message(message.chat.id,
                         f'*{message.from_user.first_name}*, дата в запросе не найдена! Начните операцию сначала.',
                         parse_mode='Markdown')
    else:
        cur.execute(""" SELECT date, type, task
                        FROM tasks
                        WHERE date=? or date=?
                    ;""", (date_every_year, date))
        tasks = cur.fetchall()

        text_notes = f'*{message.from_user.first_name}, на {date} запланировано:*\n'
        send_note = False
        text_birthday = f'*{message.from_user.first_name}, на выбранную дату {date} найдено ежегодное напоминание:*\n'
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


def sort_date(x):
    d = x.split(" - ")[0]
    sort_val = f'{d.split(".")[2]}{d.split(".")[1]}{d.split(".")[1]}'
    return int(sort_val)


def show_all_notes(message):
    note = []
    cur.execute(""" SELECT date, task
                    FROM tasks
                    WHERE type='todo' AND task NOT LIKE ('%' || 'с апогеем' || '%')
                ;""")
    tasks = cur.fetchall()

    for item in tasks:
        note.append(f'{item[0]} - {item[1]}')

    note.sort(key=sort_date)
    noteSort = f'*{message.from_user.first_name}, согласно запроса, в базе найдено:*\n'

    for n in note:
        noteSort = noteSort + f'{n}\n'

    bot.send_message(message.chat.id, noteSort, parse_mode='Markdown')


def show_all_birthdays(message):
    note = []
    cur.execute(""" SELECT date, task
                    FROM tasks
                    WHERE type='birthday'
                ;""")
    tasks = cur.fetchall()

    for item in tasks:
        note.append(f'{item[0]} - {item[1]}')

    note.sort(key=lambda x: int(f'{x[:5].split(".")[1]}{x[:5].split(".")[0]}'))
    noteSort = f'*{message.from_user.first_name}, согласно Вашего запроса, найдены ежегодные напоминания:*\n'

    for n in note:
        noteSort = noteSort + f'{n}\n'

    bot.send_message(message.chat.id, noteSort, parse_mode='Markdown')


def joke_parsing(id_user, all=False):
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
    if all == False:
        return choice(response_list)
    else:
        for x in response_list:
            response_all += f'~ {x} \n\n'
        return response_all


def show_joke(message):
    try:
        id_user = message.chat.id
        bot.send_message(message.chat.id, joke_parsing(id_user))
    except:
        bot.send_message(
            message.chat.id, 'похоже сломался сайтик с анекдотами')


def show_joke_many(message):
    try:
        id_user = message.chat.id
        bot.send_message(message.chat.id, joke_parsing(id_user, all=True))
    except:
        bot.send_message(
            message.chat.id, 'похоже сломался сайтик с анекдотами')


def random_response_to_word(word):
    cur.execute(""" SELECT answer
                    FROM reactions
                    WHERE word=?
                    ;""", (word, ))
    respons = cur.fetchall()
    return choice(respons)[0]


def add_random_task(message, *args):
    choice_task = random_response_to_word('random')
    task = f'задание "{choice_task}" возложено на {message.from_user.first_name}'
    date = datetime.strftime(dt.today() + timedelta(days=1), '%d.%m.%Y')
    add_todo(date, 'todo', task, message.from_user.id)
    bot.send_message(
        message.chat.id, f'Задача <{choice_task}> для {message.from_user.first_name} добавлена на {date}')


def check_note_and_send_message():
    # проверка на пропуск минут в случаях отказов оборудования
    cur_time_tup = time.mktime(datetime.now().replace(
        second=0, microsecond=0).timetuple())

    cur.execute(""" SELECT chtime
                    FROM checktime
                ;""")
    last_time_to_check = cur.fetchone()

    if last_time_to_check == None:
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
            bot.send_message(
                CHAT_ID, f'Господа, поздравляю вас с праздником - {ru_holidays.get(dt.today())}')

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
