# family_bot

    Телеграм бот для напоминания о разовых заданиях и ежегодных записях.
    К примеру:
        "встретится с друзьями в 18:00 20.02.2020" - разовое напоминание, которое будет удалено после показа.
        "ДР друга Васи 20.02" - запись которая 20.02 ежегодно будет давать о себе знать.
    Бот в личном чате может сообщать погоду в текущем месте и моменте или прогноз на 4 дня вперёд.
    Можно отправлять адрес местонахождения в группу Телеграмм.
    Умеет выводить анекдоты, когда становится грусно или просто посмешить согрупников.
    Можно отработать провинность, добавив случайное задание на следующий день.
    Или узнать список мероприятий в СПб на ближайшую дату.


    Для корректной работы необходимо все файлы расположить в одной папке.
    В config.py заполнить все параметры, зарегестрировшись предварительно на сервисах.


    У меня он работает на руотере keenetic Extra в системе Entware, тут описание -
    <https://help.keenetic.com/hc/ru/articles/360021214160-Установка-системы-пакетов-репозитория-Entware-на-USB-накопитель>

    Скрипты и систему расположил в отдельной одноимённом архиве.
    S77botstart нужно положить в /opt/etc/init.d/
    всё остальное в /opt/usr/bot/    

