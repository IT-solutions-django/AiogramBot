import asyncio
from googleapiclient.errors import HttpError
from settings.quickstart import main
from typing import List, Dict, Optional, Any
from settings.logging_settings import logger
import aiohttp
from settings import static

service = main()

SPREADSHEET_ID: str = '1NROUgrCfvtKfccK8iJm__V3qo7uKTC3KsJhn578S7qY'
RANGE_NAME: str = "Clients!A1:M"
RANGE_NAME_2: str = "JSON!A1:AD"

companies: Dict[str, Dict[str, str]] = {}
advertisements: Dict[str, List[Dict[str, str]]] = {}
advertisements_options: Dict[str, List[Dict[str, str]]] = {}
position_advertisements = {}
slow_position_advertisements = {}
info_for_id_ad = {}
balance_position = {}


async def load_data_from_sheet(service: Any, range_name: str, retries: int = 3) -> Optional[List[List[str]]]:
    sheet = service.spreadsheets()

    for attempt in range(retries):
        try:
            result = await asyncio.to_thread(sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute)
            values = result.get('values', [])
            return values if values else None
        except HttpError as e:
            logger.warning(f"Ошибка при загрузке данных: {e}. Попытка {attempt + 1} из {retries}")
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                logger.error("Превышено количество попыток загрузки данных.")
                return None


async def process_data(values: List[List[str]], exclude_key: str) -> Dict[str, List[Dict[str, str]]]:
    headers: List[str] = values[0]
    company_data: List[List[str]] = values[1:]

    header_indices: Dict[str, int] = {header: idx for idx, header in enumerate(headers)}

    exclude_idx: int = header_indices[exclude_key]

    data_dict: Dict[str, List[Dict[str, str]]] = {}

    for row in company_data:
        key: str = row[exclude_idx]
        data: Dict[str, str] = {header.strip(): value for header, value in zip(headers, row) if
                                value and header != exclude_key}

        if key not in data_dict:
            data_dict[key] = [data]
        else:
            data_dict[key].append(data)

    return data_dict


async def load_companies_from_sheet(service: Any) -> None:
    logger.info('Началась загрузка данных')

    global companies, advertisements, advertisements_options, position_advertisements, info_for_id_ad, slow_position_advertisements

    values_1: Optional[List[List[str]]] = await load_data_from_sheet(service, RANGE_NAME)
    if values_1:
        headers: List[str] = values_1[0]
        company_data: List[List[str]] = values_1[1:]
        companies = {
            row[0]: {headers[i]: row[i] for i in range(1, len(headers)) if row[i]}
            for row in company_data
        }

    values_2: Optional[List[List[str]]] = await load_data_from_sheet(service, RANGE_NAME_2)
    if values_2:
        advertisements = await process_data(values_2, 'client')
        advertisements_options = await process_data(values_2, 'options')

    value_3 = await load_data_from_sheet(service, RANGE_NAME_2)
    if value_3:
        for row in value_3[1:]:
            if row[27] == 'TRUE':
                if row[7] == 'Снято':
                    continue
                if row[23] == '' and row[24] == "TRUE":
                    continue
                id_ad = row[8]
                dir_ad = row[6]
                geo_ad = row[3]
                lemma_ad = row[5]
                params = (geo_ad, lemma_ad, dir_ad)
                if params in slow_position_advertisements:
                    slow_position_advertisements[params]['idx'].append(id_ad)
                else:
                    slow_position_advertisements[params] = {'idx': [id_ad]}
            else:
                if row[7] == 'Снято':
                    continue
                if row[23] == '' and row[24] == "TRUE":
                    continue
                id_ad = row[8]
                dir_ad = row[6]
                geo_ad = row[3]
                lemma_ad = row[5]
                params = (geo_ad, lemma_ad, dir_ad)
                if params in position_advertisements:
                    position_advertisements[params]['idx'].append(id_ad)
                else:
                    position_advertisements[params] = {'idx': [id_ad]}

    values_4 = await load_data_from_sheet(service, RANGE_NAME_2)
    if values_4:
        info_for_id_ad = await process_data(values_2, '_id')

    logger.info('Загрузка данных завершилась')


async def get_balance_position():
    logger.info('Началась загрузка баланса')
    global balance_position

    boobs = {data['Client']: {'Boobs': data['Boobs'], 'Company': field} for field, data in companies.items()
             if 'Boobs' in data}

    balance_url = static.Urls.BALANCE_URL.value

    for client_name, boob_value in boobs.items():
        headers = {'Cookie': f"boobs={boob_value['Boobs']}"}

        async with aiohttp.request('get', balance_url, headers=headers, allow_redirects=False) as balance_response:
            if balance_response.status == 200:
                balance_data = await balance_response.json()
                balance = balance_data.get('canSpend')
                balance_position[boob_value['Company']] = balance
            else:
                balance_position[boob_value['Company']] = "Ошибка получения баланса"
                logger.warning(f"Ошибка получения баланса для {boob_value['Company']}")

    logger.info('Завершилась загрузка баланса')
