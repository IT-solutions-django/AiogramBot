from settings.quickstart import main

service = main()

SPREADSHEET_ID = '1N4nlS9ph1N3PGBPIVcYxbtXRqcEE4GnAijZIC1pzBgI'
RANGE_NAME = 'Клиенты!A1:I'
RANGE_NAME_2 = 'JSON!A1:AB'

companies = {}
advertisements = {}
advertisements_options = {}


def load_data_from_sheet(service, range_name: str):
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    values = result.get('values', [])
    return values if values else None


def process_data(values, exclude_key: str):
    headers = values[0]
    company_data = values[1:]

    header_indices = {header: idx for idx, header in enumerate(headers)}

    exclude_idx = header_indices[exclude_key]

    data_dict = {}

    for row in company_data:
        key = row[exclude_idx]
        data = {header: value for header, value in zip(headers, row) if value and header != exclude_key}

        if key not in data_dict:
            data_dict[key] = [data]
        else:
            data_dict[key].append(data)

    return data_dict


def load_companies_from_sheet(service):
    global companies, advertisements, advertisements_options

    values_1 = load_data_from_sheet(service, RANGE_NAME)
    if values_1:
        headers = values_1[0]
        company_data = values_1[1:]
        companies = {
            row[0]: {headers[i]: row[i] for i in range(1, len(headers)) if row[i]}
            for row in company_data
        }

    values_2 = load_data_from_sheet(service, RANGE_NAME_2)
    if values_2:
        advertisements = process_data(values_2, 'client')
        advertisements_options = process_data(values_2, 'options')
