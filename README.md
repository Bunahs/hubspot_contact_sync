# HubSpot Contact → Google Sheets Sync

## 1. Project Overview

A Python application that synchronizes HubSpot Contacts with Google Sheets.

The application supports full synchronization and incremental synchronization.

## 2. Features

- Retrieves HubSpot Contacts through the HubSpot CRM API.
- Handles API pagination using HubSpot's `paging.next.after` cursor.
- Uses HubSpot Contact ID as the unique identifier.
- Updates existing Google Sheets rows when a Contact ID already exists.
- Appends new Contacts when their IDs do not exist.
- Supports incremental synchronization based on `lastmodifieddate`.
- Saves the last successful sync timestamp in `data/sync_state.json`.
- Records the last sync timestamp in Google Sheets.
- Keeps Contacts with missing email or phone information and logs a warning.
- Logs synchronization statistics, including records read, created, updated, and errors.
- Handles synchronization failures and records error details in the log.

## 3. Requirements

- Python 3.10+
- HubSpot Service Key with permission to read CRM Contacts (`crm.objects.contacts.read`).
- Google Cloud service account.
- Google Sheets API enabled.
- A Google spreadsheet shared with the service account email as Editor.

## 4. Project Setup

### 4.1. Create a virtual environment

```bash
python -m venv venv
```

Activate the environment:

**Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 4.2. Install dependencies

```bash
pip install -r requirements.txt
```

### 4.3. Configure environment variables

Copy `.env.example` to `.env` and configure:

```env
HUBSPOT_ACCESS_TOKEN=your_hubspot_service_key
GOOGLE_SHEET_ID=your_google_spreadsheet_id
GOOGLE_SERVICE_ACCOUNT_FILE=service-account.json
GOOGLE_WORKSHEET_NAME=Contacts
```

Place the downloaded Google service account JSON key in the project root.

**Security:** Never commit `.env`, `service-account.json`, or other credentials to Git.

## 5. Google Sheets Preparation

1. Create a Google Cloud project.
2. Enable Google Sheets API.
3. Create a service account.
4. Download the service account JSON key.
5. Share the Google spreadsheet with the service account's `client_email` as Editor.
6. Copy the spreadsheet ID from its URL into `.env`.
7. Create a worksheet named `Contacts`, or use the worksheet name configured in `.env`.

The application automatically creates or updates the spreadsheet header row.

## 6. How to Run

Run the synchronization script:

```bash
python src/sync_contacts.py
```

The application prints logs in the terminal and saves them to:

```text
logs/sync.log
```

## 7. Synchronization Workflow

### 7.1. Full Sync

On the first run, when no previous synchronization timestamp exists, the application retrieves all Contacts from HubSpot.

### 7.2. Incremental Sync

On subsequent runs, the application retrieves Contacts whose `lastmodifieddate` is later than the previous successful sync timestamp.

A two-minute overlap is used to reduce the risk of missing updates.

### 7.3. Upsert Logic

For each retrieved Contact:

- If the Contact ID already exists in Google Sheets, update the existing row.
- If the Contact ID does not exist, append a new row.

### 7.4. Sync State

The application stores the last successful synchronization timestamp in:

```text
data/sync_state.json
```

The timestamp is updated only after the Google Sheets write operations complete and no Contact transformation errors are reported.

## 8. Logging and Error Handling

The application uses Python's `logging` module.

Log levels include:

- `INFO`: Synchronization progress and results.
- `WARNING`: Contacts with missing email or phone information.
- `ERROR`: Synchronization failures.

Log file:

```text
logs/sync.log
```

If synchronization fails, the application records the exception details and exits with a non-zero exit code.

## 9. Test Results

The following scenarios were manually tested:

| Test scenario | Result |
|---|---|
| Initial full synchronization | Passed |
| Duplicate Contact ID prevention | Passed |
| Updating existing Contacts | Passed |
| Incremental sync with no changes | Passed |
| Incremental sync with one modified Contact | Passed |
| Google Sheets API connection | Passed |
| Logging synchronization results | Passed |
| Error handling at application level | Basic implementation verified |

Example synchronization results:

**Initial synchronization:**
```text
read=2 | created=2 | updated=0 | errors=0
```

**Duplicate prevention:**
```text
read=2 | created=0 | updated=2 | errors=0
```

**Incremental sync with no changes:**
```text
read=0 | created=0 | updated=0 | errors=0
```

**Incremental sync with one modified Contact:**
```text
read=1 | created=0 | updated=1 | errors=0
```

Note: Multi-page pagination and actual API failure scenarios should be tested with dedicated test data before production deployment.

## 10. Project Structure

```text
hubspot_contact_sync/
│
├── src/
│   └── sync_contacts.py
│
├── data/
│   └── sync_state.json
│
├── logs/
│   └── sync.log
│
├── tests/
│   ├── test_hubspot.py
│   └── test_pagination.py
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── service-account.json
└── README.md
```

## 11. Future Improvements

- Add automatic retry and exponential backoff for rate limits and temporary network failures.
- Add automated unit and integration tests.
- Improve monitoring and error reporting.
- Prevent multiple synchronization jobs from running concurrently.
- Add support for larger datasets and additional HubSpot Contact properties.