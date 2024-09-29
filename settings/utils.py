from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, time
from typing import Optional, Dict, List


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


async def show_options(callback: types.CallbackQuery, data_dict: Dict[str, dict], exclude_key: str,
                       action: Optional[str] = None) -> None:
    builder = InlineKeyboardBuilder()
    for key in data_dict.keys():
        if action is not None:
            builder.row(types.InlineKeyboardButton(text=key, callback_data=f'{action}_{key}'))
        else:
            builder.row(types.InlineKeyboardButton(text=key, callback_data=key))
    await callback.message.answer(text=f'Выберите {exclude_key}', reply_markup=builder.as_markup())
    await callback.answer()


async def fetch_advertisement_data(advertisement: Dict[str, str], all_dict: Dict[str, str],
                                   vladivostok_time: time, current_day: int) -> str:
    id_advertisement: str = advertisement['_id']

    active_day_map: Dict[str, set] = is_day_active()
    active_day: set = active_day_map[advertisement['weekday_active']]
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
