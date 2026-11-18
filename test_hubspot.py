
import os
import requests
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()

token = os.getenv("HUBSPOT_ACCESS_TOKEN")

if not token:
    print("ERROR: HubSpot Service Key not found!")
    exit()

# HubSpot API endpoint
url = "https://api.hubapi.com/crm/v3/objects/contacts"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

params = {
    "limit": 5,
    "properties": "firstname,lastname,email,phone"
}

try:
    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    print("HTTP Status:", response.status_code)

    if response.status_code == 200:
        data = response.json()

        print("Connection successful!")
        print("Number of contacts:", len(data.get("results", [])))

        for contact in data.get("results", []):
            properties = contact.get("properties", {})
            print({
                "ID": contact.get("id"),
                "First Name": properties.get("firstname"),
                "Last Name": properties.get("lastname"),
                "Email": properties.get("email")
            })

    else:
        print("Connection failed!")
        print("Error:", response.text[:1000])

except requests.RequestException as error:
    print("Request error:", error)
