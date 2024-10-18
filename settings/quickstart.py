from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def main():
    creds = service_account.Credentials.from_service_account_file(
        'settings/credentials.json', scopes=SCOPES)

    service = build('sheets', 'v4', credentials=creds)

    return service
