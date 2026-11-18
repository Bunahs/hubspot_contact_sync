
import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("HUBSPOT_ACCESS_TOKEN")

url = "https://api.hubapi.com/crm/v3/objects/contacts"

headers = {
    "Authorization": f"Bearer {token}"
}

params = {
    "limit": 100,
    "properties": "firstname,lastname,email"
}

all_contacts = []
page = 1

while True:
    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    contacts = data.get("results", [])
    all_contacts.extend(contacts)

    print(f"Page {page}: {len(contacts)} contacts")

    # Get the next page cursor
    next_page = data.get("paging", {}).get("next")

    if not next_page:
        break

    params["after"] = next_page["after"]
    page += 1

print("----------------------------")
print("Total contacts:", len(all_contacts))
print("Total pages:", page)
print("Pagination completed!")
