from enum import Enum


class DayActiveMap(Enum):
    WEEKDAYS: set = {0, 1, 2, 3, 4}
    ALL_DAYS_EXCEPT_SUNDAY: set = {0, 1, 2, 3, 4, 5}
    FULL_WEEK: set = {0, 1, 2, 3, 4, 5, 6}


class MessageLength(Enum):
    MAX_MESSAGE_LENGTH: int = 4096


class Urls(Enum):
    BALANCE_URL: str = 'https://www.farpost.ru/personal/checkBalance/'
    DETAILS_URL: str = 'https://www.farpost.ru/personal/balance/details?date={date}'
    URL_ADVERTISEMENT: str = 'https://www.farpost.ru/{id_advertisement}/'
    URL_ACTUAL_BULLETINS: str = 'https://www.farpost.ru/personal/actual/bulletins'
    URL_STATISTIC: str = 'https://www.farpost.ru/bulletin/{ad_id}/stat/charts-data?from={current_date}&to={current_date}'
    URL_TABLE: str = 'https://docs.google.com/spreadsheets/d/1NROUgrCfvtKfccK8iJm__V3qo7uKTC3KsJhn578S7qY/edit?gid=351863719#gid=351863719'

    def get_url(self, **kwargs):
        return self.value.format(**kwargs)


class SshData(Enum):
    IP: str = '217.18.62.157'
    USERNAME: str = 'root'


class Message(Enum):
    LOAD_COMMAND: str = 'Идет выполнение команды...'
    CHOICE_COMMAND: str = 'Выберите команду'
    ERROR_COMMAND: str = 'Для данной компании действие недоступно'
    STATISTICS_SUCCESS: str = 'Данные по статистике отправлены'
    STATISTICS_ERROR: str = 'Данные по статистике не отправлены. Произошла ошибка'
