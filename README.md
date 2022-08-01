# Телеграмм бот для семейного чата.
***

![Alt Text](img/bot-face.png)

***

## Он умеет:
- хранить и показывать разовые напоминания
- оповещать о днях рождения
- расказывать анекдоты
- давать прогноз погоды и текущую погоду на улице
- показывать список мероприятий в СПб на сегодняшний день

## Разотые напоминания ToDo.
Разовые напоминания обязательно должны содержать дату вформате ##.##.##.
Если не прописать время в тексте напоминания, то оно по умолчанию будет
7:15,и оповещение придет в это-же время. Если в тексте будет написано
конкретное время, то бот оповестит вас за 4 часа до него.
Пример: 20.12.2022 в 17:50 встреча в кафе с Васей.

## Ежегодные напоминания.
О ежегодных напоминаниях бот оповещает в 7:15 на дату оповещения. Если в
тексте был Емоджи 🎁, то дополнительно будет оповещение за 7 дней до даты.
Это на случай если нужно купить подарок. В формате даты в ежегодного
оповещения не должно быть года, только день и месяц ##.##.
Пример: 20.12 ДР у Васи Васиной 🎁

Анекдоты, список мероприятий и списки с напоминаниями можно отобразить
нажав на соответствующие кнопки.


Для корректной работы необходимо все файлы расположить в одной папке.
В config.py заполнить все параметры, зарегестрировшись предварительно на сервисах.


У меня он работает на руотере keenetic Extra в системе Entware, 
описание по установке [тут>>>](https://help.keenetic.com/hc/ru/articles/360021214160)

____
Скрипты и саму систему расположил в одноимённом архиве.
S77botstart нужно положить в /opt/etc/init.d/
второй скрипт и файлы бота в /opt/usr/bot/
Перед запуском, не забудте установить интерпритатор Python и нужные библиотеки.
