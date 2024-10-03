from enum import Enum


class DayActiveMap(Enum):
    WEEKDAYS: set = {0, 1, 2, 3, 4}
    ALL_DAYS_EXCEPT_SUNDAY: set = {0, 1, 2, 3, 4, 5}
    FULL_WEEK: set = {0, 1, 2, 3, 4, 5, 6}


class MessageLength(Enum):
    MAX_MESSAGE_LENGTH: int = 4096


class Urls(Enum):
    BALANCE_URL: str = 'https://www.farpost.ru/personal/checkBalance/'
    DETAILS_URL: str = 'https://www.farpost.ru/personal/balance/details?date={date}&page=1'
    URL_ADVERTISEMENT: str = 'https://www.farpost.ru/{id_advertisement}/'
    URL_ACTUAL_BULLETINS: str = 'https://www.farpost.ru/personal/actual/bulletins'

    def get_url(self, **kwargs):
        return self.value.format(**kwargs)


class SshData(Enum):
    IP: str = '217.18.62.157'
    USERNAME: str = 'root'


class Message(Enum):
    LOAD_COMMAND: str = 'Идет выполнение команды...'
    CHOICE_COMMAND: str = 'Выберите команду'
    ERROR_COMMAND: str = 'Для данной компании действие недоступно'
