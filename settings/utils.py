from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
import aiohttp

from settings import load_table

from typing import Optional, Dict, List, Union

from bs4 import BeautifulSoup

from datetime import datetime, time

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def is_day_active() -> Dict[str, set]:
    weekdays = {0, 1, 2, 3, 4}
    all_days_except_sunday = {0, 1, 2, 3, 4, 5}
    full_week = {0, 1, 2, 3, 4, 5, 6}

    day_info_map = {
        'Будни': weekdays,
        'Кроме ВС': all_days_except_sunday,
        'Все': full_week,
    }

    return day_info_map


MAX_MESSAGE_LENGTH: int = 4096


def split_message(text: str) -> List[str]:
    return [text[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]


async def show_options(obj: Union[types.CallbackQuery, types.Message], data_dict: Dict[str, dict], exclude_key: str,
                       action: Optional[str] = None) -> None:
    builder = InlineKeyboardBuilder()
    for key in data_dict.keys():
        if action is not None:
            builder.row(types.InlineKeyboardButton(text=key, callback_data=f'{action}_{key}'))
        else:
            builder.row(types.InlineKeyboardButton(text=key, callback_data=key))

    if isinstance(obj, types.CallbackQuery):
        await obj.message.answer(text=f'Выберите {exclude_key}', reply_markup=builder.as_markup())
        await obj.answer()
    elif isinstance(obj, types.Message):
        await obj.answer(text=f'Выберите {exclude_key}', reply_markup=builder.as_markup())


async def fetch_advertisement_data(advertisement: Dict[str, str], all_dict: Dict[str, str],
                                   vladivostok_time: time, current_day: int) -> str:
    id_advertisement: str = advertisement['_id']

    active_day_map: Dict[str, set] = is_day_active()
    active_day: Optional[set] = active_day_map.get(advertisement['weekday_active'], None)

    if active_day is None:
        logging.warning(
            f"Активный день для объявления '{id_advertisement}' не найден. Пожалуйста, добавьте его в active_day_map.")
        return f'Для объявления "{id_advertisement}" активный день не определён. Требуется обновление.\n\n'

    is_active_day: bool = current_day in active_day

    url: str = f'https://www.farpost.ru/{id_advertisement}/'

    async with aiohttp.request('get', url, allow_redirects=True) as response:
        if response.status == 200:
            start_time: time = datetime.strptime(advertisement['start_time'], '%H.%M').time()
            end_time: time = datetime.strptime(advertisement['finish_time'], '%H.%M').time()

            if str(response.url) in all_dict and (start_time <= vladivostok_time <= end_time) and is_active_day:
                content: str = await response.text()
                soup: BeautifulSoup = BeautifulSoup(content, 'html.parser')
                title = soup.find('span', class_='inplace auto-shy')
                return f'{title.text} - {all_dict[str(response.url)]}\n\n'
            elif str(response.url) in all_dict and (
                    not (start_time <= vladivostok_time <= end_time) or not is_active_day):
                return f'Для объявления "{url}" время вышло, но оно присутствует. Необходимо проверить данную информацию\n\n'
            elif not (str(response.url) in all_dict) and (start_time <= vladivostok_time <= end_time) and is_active_day:
                return f'Для объявления "{url}" время не вышло, но его нет. Необходимо проверить данную информацию\n\n'
            else:
                return f'Для объявления "{url}" вышло время\n\n'
        else:
            return f'Для компании с id "{id_advertisement}" произошла ошибка запроса\n\n'


async def get_balance(obj: Union[types.CallbackQuery, types.Message]) -> None:
    boobs = {data['Client']: {'Boobs': data['Boobs'], 'Company': field} for field, data in load_table.companies.items()
             if 'Boobs' in data}

    if isinstance(obj, types.CallbackQuery):
        await obj.message.answer('Идет загрузка баланса...')
    else:
        await obj.answer('Идет загрузка баланса...')

    async with aiohttp.ClientSession() as session:
        messages = []
        for client_name, boob_value in boobs.items():
            headers = {'Cookie': f"boobs={boob_value['Boobs']}"}
            async with session.get(f'https://www.farpost.ru/personal/checkBalance/', headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    balance = data.get('canSpend')
                    messages.append(f'<b>Клиент</b>: {client_name} ({boob_value["Company"]}), <b>Баланс</b>: {balance}')
                else:
                    messages.append(f'Ошибка получения баланса для {client_name}')
            session._cookie_jar._cookies.clear()

        if isinstance(obj, types.CallbackQuery):
            await obj.message.answer('\n'.join(messages), parse_mode='HTML')
            await obj.answer()
        else:
            await obj.answer('\n'.join(messages), parse_mode='HTML')


async def get_server(obj: Union[types.CallbackQuery, types.Message]) -> None:
    buttons_command_server = [
        [types.InlineKeyboardButton(text='Start', callback_data='start')],
        [types.InlineKeyboardButton(text='Stop', callback_data='stop')],
        [types.InlineKeyboardButton(text='Restart', callback_data='restart')],
        [types.InlineKeyboardButton(text='Status', callback_data='status')]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons_command_server)
    if isinstance(obj, types.CallbackQuery):
        await obj.message.answer(text='Выберите команду', reply_markup=keyboard)
        await obj.answer()
    else:
        await obj.answer(text='Выберите команду', reply_markup=keyboard)
