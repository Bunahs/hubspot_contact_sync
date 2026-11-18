
import os
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Load configuration
load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
WORKSHEET_NAME = os.getenv("GOOGLE_WORKSHEET_NAME", "Contacts")

if not SERVICE_ACCOUNT_FILE or not SPREADSHEET_ID:
    raise ValueError("Missing Google Sheets configuration in .env")

# Authenticate with Google
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

credentials = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)

# Connect to Google Sheets API
service = build(
    "sheets",
    "v4",
    credentials=credentials
)

# Test writing data to Google Sheet
result = service.spreadsheets().values().update(
    spreadsheetId=SPREADSHEET_ID,
    range=f"'{WORKSHEET_NAME}'!A1",
    valueInputOption="RAW",
    body={
        "values": [["Google Sheets API connection successful!"]]
    }
).execute()

print("Google Sheets connection successful!")
print("Updated cells:", result.get("updatedCells"))
