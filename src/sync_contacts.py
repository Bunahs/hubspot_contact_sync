import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import requests
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

PROPERTIES = [
    "firstname", "lastname", "email", "phone", "mobilephone",
    "company", "jobtitle", "website", "country",
    "lifecyclestage", "createdate", "lastmodifieddate",
]
HEADERS = [
    "HubSpot Contact ID", "First Name", "Last Name", "Email", "Phone",
    "Mobile Phone", "Company", "Job Title", "Website", "Country",
    "Lifecycle Stage", "Create Date", "Last Modified Date", "Last Sync",
]
HUBSPOT_URL = "https://api.hubapi.com/crm/v3/objects/contacts"
HUBSPOT_SEARCH_URL = "https://api.hubapi.com/crm/v3/objects/contacts/search"
STATE_FILE = ROOT / "data" / "sync_state.json"

def setup_logging() -> None:
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "sync.log", encoding="utf-8"),
        ],
    )


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def retry_request(method, url, **kwargs):
    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = requests.request(
                method,
                url,
                **kwargs
            )

            response.raise_for_status()
            return response

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
        ) as error:

            if isinstance(error, requests.exceptions.HTTPError):
                status_code = error.response.status_code

                # Do not retry most client errors (4xx).
                if status_code != 429 and status_code < 500:
                    raise

                retry_after = error.response.headers.get("Retry-After")

            else:
                retry_after = None

            if attempt == max_retries - 1:
                logging.error(
                    "API request failed after %s attempts: %s",
                    max_retries,
                    error,
                )
                raise

            if retry_after:
                try:
                    wait_seconds = float(retry_after)
                except ValueError:
                    wait_seconds = 2 ** attempt
            else:
                wait_seconds = 2 ** attempt

            logging.warning(
                "API request failed. Retrying in %s seconds. Attempt %s/%s. Error: %s",
                wait_seconds,
                attempt + 1,
                max_retries,
                error,
            )

            time.sleep(wait_seconds)
def get_hubspot_contacts(
    token: str,
    modified_since_ms=None
) -> Iterable[dict]:
    """Fetch all Contacts or only Contacts modified since a timestamp."""

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # First sync: retrieve all Contacts using the regular API.
    if modified_since_ms is None:
        params = {
            "limit": 100,
            "properties": ",".join(PROPERTIES),
            "archived": "false",
        }

        while True:
            response = retry_request(
    "GET",
    HUBSPOT_URL,
    headers=headers,
    params=params,
    timeout=30,
)
            response.raise_for_status()
            payload = response.json()

            for contact in payload.get("results", []):
                yield contact

            after = payload.get("paging", {}).get("next", {}).get("after")

            if not after:
                break

            params["after"] = after

    # Later syncs: retrieve only modified Contacts.
    else:
        body = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "lastmodifieddate",
                            "operator": "GT",
                            "value": str(modified_since_ms),
                        }
                    ]
                }
            ],
            "properties": PROPERTIES,
            "limit": 200,
        }

        while True:
            response = retry_request(
    "POST",
    HUBSPOT_SEARCH_URL,
    headers=headers,
    json=body,
    timeout=30,
)
            response.raise_for_status()
            payload = response.json()

            for contact in payload.get("results", []):
                yield contact

            after = payload.get("paging", {}).get("next", {}).get("after")

            if not after:
                break

            body["after"] = after



def build_sheets_service(service_account_file: str):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_file(
        service_account_file, scopes=scopes
    )
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def ensure_header(service, spreadsheet_id: str, worksheet: str) -> None:
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"'{worksheet}'!A1:N1"
    ).execute()
    values = result.get("values", [])
    if not values or values[0] != HEADERS:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{worksheet}'!A1:N1",
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()
        logging.info("Created/updated the Google Sheet header.")


def read_existing_contacts(service, spreadsheet_id: str, worksheet: str) -> Dict[str, int]:
    """Return {HubSpot Contact ID: 1-based sheet row number}."""
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"'{worksheet}'!A2:N"
    ).execute()
    rows = result.get("values", [])
    existing = {}
    for row_number, row in enumerate(rows, start=2):
        if row and row[0]:
            existing[str(row[0])] = row_number
    return existing


def contact_to_row(contact: dict, synced_at: str) -> List[str]:
    props = contact.get("properties", {}) or {}
    contact_id=contact.get("id")
    if not contact_id:
        raise ValueError("Contact ID is missing.")
    # Missing email/phone are retained as blank cells and reported in the log.
    if not props.get("email") and not props.get("phone") and not props.get("mobilephone"):
        logging.warning("Contact %s has no email, phone or mobile phone.", contact.get("id"))

    return [
        str(contact_id),
        props.get("firstname") or "",
        props.get("lastname") or "",
        props.get("email") or "",
        props.get("phone") or "",
        props.get("mobilephone") or "",
        props.get("company") or "",
        props.get("jobtitle") or "",
        props.get("website") or "",
        props.get("country") or "",
        props.get("lifecyclestage") or "",
        props.get("createdate") or "",
        props.get("lastmodifieddate") or "",
        synced_at,
    ]

def load_last_sync():
    """Load the last successful sync timestamp."""
    if not STATE_FILE.exists():
        return None

    with open(STATE_FILE, "r", encoding="utf-8") as file:
        state = json.load(file)

    return int(state["last_sync_timestamp_ms"])


def save_last_sync(timestamp_ms: int) -> None:
    """Save the last successful sync timestamp."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    temp_file = STATE_FILE.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(
            {"last_sync_timestamp_ms": timestamp_ms},
            file,
            indent=4,
        )

    temp_file.replace(STATE_FILE)
def sync() -> Tuple[int, int, int, int]:
    token = required_env("HUBSPOT_ACCESS_TOKEN")
    spreadsheet_id = required_env("GOOGLE_SHEET_ID")
    worksheet = os.getenv("GOOGLE_WORKSHEET_NAME", "Contacts")
    service_account_file = required_env("GOOGLE_SERVICE_ACCOUNT_FILE")
    service_account_path = ROOT / service_account_file
    if not service_account_path.exists():
        raise FileNotFoundError(f"Google service account file not found: {service_account_path}")

    sheets = build_sheets_service(str(service_account_path))
    ensure_header(sheets, spreadsheet_id, worksheet)
    existing = read_existing_contacts(sheets, spreadsheet_id, worksheet)

    read_count = created_count = updated_count = error_count = 0

    # Capture the start time of this sync.
    sync_started_ms = int(
        datetime.now(timezone.utc).timestamp() * 1000
    )

    synced_at = datetime.now(timezone.utc).isoformat()
    updates = []

    last_sync_ms = load_last_sync()

    if last_sync_ms is None:
        modified_since_ms = None
        logging.info("No previous sync found. Running full sync.")
    else:
        # Recheck the previous 2 minutes to avoid missing updates.
        modified_since_ms = max(0, last_sync_ms - 120000)
        logging.info("Running incremental sync.")

    logging.info("Starting HubSpot Contact synchronization.")

    for contact in get_hubspot_contacts(token, modified_since_ms):
        read_count += 1
        contact_id = str(contact.get("id", ""))
        try:
            row = contact_to_row(contact, synced_at)
            if contact_id in existing:
                row_number = existing[contact_id]
                updates.append({
                    "range": f"'{worksheet}'!A{row_number}:N{row_number}",
                    "values": [row],
                })
               
            else:
                # New records are appended in one batch after pagination completes.
                updates.append({"range": None, "values": [row]})
                
        except Exception:
            error_count += 1
            logging.exception("Could not transform Contact ID %s.", contact_id)

    # Send existing-row updates together; append new rows together.
    update_data = [item for item in updates if item["range"] is not None]
    append_rows = [item["values"][0] for item in updates if item["range"] is None]

    if update_data:sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"valueInputOption": "RAW", "data": update_data},
    ).execute(num_retries=3)

    updated_count = len(update_data)

    if append_rows: sheets.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{worksheet}'!A:N",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": append_rows},
    ).execute(num_retries=3)

    created_count = len(append_rows)
    if error_count == 0:
        save_last_sync(sync_started_ms)
        logging.info("Last successful sync timestamp saved.")
    else:
        logging.warning(
            "Sync had errors. Last sync timestamp was not updated."
        )
    logging.info(
        "Sync completed | read=%s | created=%s | updated=%s | errors=%s",
        read_count, created_count, updated_count, error_count
    )
    return read_count, created_count, updated_count, error_count


if __name__ == "__main__":
    setup_logging()

    try:
        sync()

    except Exception:
        logging.exception(
            "Synchronization failed. Please check the error and try again."
        )
        sys.exit(1)