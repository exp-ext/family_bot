# Телеграм бот для семейного чата 👨‍👩‍👧‍👦
***
<p align="center">
<img src="https://github.com/exp-ext/family_bot/blob/main/bot-face.png" width="200">
</p>

## Он умеет:
- хранить и показывать разовые напоминания
- оповещать о днях рождения
- раcсказывать анекдоты
- давать прогноз погоды и текущую погоду на улице
- показывать список мероприятий в СПб на сегодняшний день

### Разовые напоминания ToDo

Разовые напоминания обязательно должны содержать дату в формате ##.##.##. Если не прописать время в тексте напоминания, то оно по умолчанию будет 7:15,и оповещение придет в это-же время. Если в тексте будет написано конкретное время, то бот оповестит вас за 4 часа до него.

Пример: 20.12.2022 в 17:50 встреча в кафе с Васей.

### Ежегодные напоминания

О ежегодных напоминаниях бот оповещает в 7:15 на дату оповещения. Если в тексте был Емоджи 🎁, то дополнительно будет оповещение за 7 дней до даты. Это на случай если нужно купить подарок. В формате даты в ежегодного оповещения не должно быть года, только день и месяц ##.##.

Пример: 20.12 ДР у Васи Васиной 🎁

***
### Анекдоты, список мероприятий и списки с напоминаниями можно отобразить нажав на соответствующие кнопки.

### Прогноз погоды и геолокацию можно получить только в личном чате с ботом.
***

## Подробнее о регистрациях:

⚠️все токены и ID записывайте куда-то отдельно в файл.

Для начала необходимо создать нового бота и получить его токен. Делается это через[@BotFather](https://t.me/BotFather). Далее входим в настройки инлайн режима '/setinline' и включаем его.

После, для создания быстрых команд, нужно ввести '/setcommands' и передать
список самих команд:

    help - вывести список доступных команд
    help_locatoin - показать кнопку с запросом погоды

Для получения Вашего ID и ID группы можно воспользоваться ботом [@getmyid_bot](https://t.me/getmyid_bot). Для этого просто добавьте его в группу. Отрицательный номер это ID группы, второй ваш. Не забываем удалить этого бота из группы ) и добавить своего.

Для получения погоды необходимо зарегистрироваться и получить токен на сайте [Openweathermap](https://home.openweathermap.org/api_keys).

Для геолокации будет нужна регистрация и ключ от Яндекс API геолокиция. [Тут можно получить ключ и почитать их документацию при желании.](https://yandex.ru/dev/maps/geocoder/)

## Подробнее о установке:

Бота необходимо разместить на сервере. Я не стал далеко ходить, развернул систему Entware у себя на руотере Keenetic Extra и установил Python3 в ней. Об установке Entware можно посмотреть [тут>>>](https://help.keenetic.com/hc/ru/articles/360021214160)

Установка бота в системе Entware (если другая Unix, то вместо opkg буде sudo apt-get):

> Через командную строку устанавливаем python:

    $ opkg install python3

> после ставим менеджер пакетов pip командой:

    $ opkg install python3-pip

> устанавливаем curl:

    $ opkg install curl

> Создаём необходимую папку:

    $ mkdir /opt/usr/bot

> переходим в нашу директорию:

    $ cd /opt/usr/bot

> заливаем в неё файлы с githab, сразу делая их исполняемыми:

    # копируйте и вводите в терминал все 5 строк поочерёдно
    
    $ curl -k -L https://raw.githubusercontent.com/exp-ext/family_bot/master/notebot.py -o notebot.py && chmod 755 notebot.py
    
    $ curl -k -L https://raw.githubusercontent.com/exp-ext/family_bot/master/config.py -o config.py && chmod 755 config.py
    
    $ curl -k -L https://raw.githubusercontent.com/exp-ext/family_bot/master/data_for_notebot.db -o data_for_notebot.db
    
    $ curl -k -L https://raw.githubusercontent.com/exp-ext/family_bot/master/requirements.txt -o requirements.txt

    $ curl -k -L https://raw.githubusercontent.com/exp-ext/family_bot/master/botstart.sh -o botstart.sh && chmod 755 botstart.sh

> в той же папке открываем при помощи vim конфиг:

    $ vi config.py

Нажимаем Insert для активации режима изменения и вписываем в него все ID полученные при регистрации ранее. Чтоб сохранить и выйти нужно нажать Esc и ввести команду :wq (она появится внизу)

> Устанавливаем необходимые библиотеки:

    $ python3 -m pip install -r requirements.txt

> Заливаем скрипт запуска бота при перезагрузке системы в папку инициализации:
    
    $ curl -k -L https://raw.githubusercontent.com/exp-ext/family_bot/master/botstart.sh -o /opt/etc/init.d/S77botstart.sh && chmod 755 /opt/etc/init.d/S77botstart.sh

> Настраиваем crontab:

    $ vi /opt/etc/crontab

> и в конец всех записей вставляем:

    */360 * * * * root /opt/usr/bot/botstart.sh

> и наконец запуск бота 🚀:

    $ /opt/usr/bot/botstart.sh

## License
[MIT © Andrey Borokin](https://github.com/exp-ext/family_bot/blob/main/LICENSE.txt)

[![Join Telegram](https://img.shields.io/badge/My%20Telegram-Join-blue)](https://t.me/Borokin)
