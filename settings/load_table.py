import asyncio
from settings.quickstart import main
from typing import List, Dict, Optional, Any
from settings.logging_settings import logger

service = main()

SPREADSHEET_ID: str = '1NROUgrCfvtKfccK8iJm__V3qo7uKTC3KsJhn578S7qY'
RANGE_NAME: str = 'Клиенты!A1:L'
RANGE_NAME_2: str = 'JSON!A1:AB'

companies: Dict[str, Dict[str, str]] = {}
advertisements: Dict[str, List[Dict[str, str]]] = {}
advertisements_options: Dict[str, List[Dict[str, str]]] = {}


async def load_data_from_sheet(service: Any, range_name: str) -> Optional[List[List[str]]]:
    sheet = service.spreadsheets()
    result = await asyncio.to_thread(sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute)
    values = result.get('values', [])
    return values if values else None


async def process_data(values: List[List[str]], exclude_key: str) -> Dict[str, List[Dict[str, str]]]:
    headers: List[str] = values[0]
    company_data: List[List[str]] = values[1:]

    header_indices: Dict[str, int] = {header: idx for idx, header in enumerate(headers)}

    exclude_idx: int = header_indices[exclude_key]

    data_dict: Dict[str, List[Dict[str, str]]] = {}

    for row in company_data:
        key: str = row[exclude_idx]
        data: Dict[str, str] = {header: value for header, value in zip(headers, row) if value and header != exclude_key}

        if key not in data_dict:
            data_dict[key] = [data]
        else:
            data_dict[key].append(data)

    return data_dict


async def load_companies_from_sheet(service: Any) -> None:
    logger.info('Началась загрузка данных')

    global companies, advertisements, advertisements_options

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

    logger.info('Загрузка данных завершилась')

