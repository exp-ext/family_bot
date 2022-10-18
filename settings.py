import os

from telebot import TeleBot


TOKEN = os.getenv('TOKEN')

CHAT_ID = os.getenv('CHAT_ID')

OW_API_ID = os.getenv('OW_API_ID')

YANDEX_GEO_API = os.getenv('YANDEX_GEO_API')

ID_CHILDREN = list(os.getenv('ID_CHILDREN').split())

ID_ADMIN = os.getenv('ID_ADMIN')

bot = TeleBot(TOKEN)
