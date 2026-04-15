"""
setup_cosmos.py — Provision Cosmos DB for NoSQL (serverless) and seed hotel data.

Usage:
    python setup_cosmos.py

Reads AZURE_SUBSCRIPTION_ID and AZURE_RESOURCE_GROUP from .env.
Creates a Cosmos DB account with serverless capacity mode, a database, and a container,
then inserts 10 hotel documents matching the search index schema.
"""

import json
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

# Lazy import — user must have azure-identity + requests installed
import requests
from azure.identity import DefaultAzureCredential


# ── Configuration ────────────────────────────────────────────────────────────

SUBSCRIPTION_ID = os.environ["AZURE_SUBSCRIPTION_ID"]
RESOURCE_GROUP = os.environ.get("COSMOS_RESOURCE_GROUP", os.environ["AZURE_RESOURCE_GROUP"])
ACCOUNT_NAME = os.environ.get("COSMOS_ACCOUNT_NAME", "smoketest-cosmos")
DATABASE_NAME = os.environ.get("COSMOS_DATABASE", "hotels-db")
CONTAINER_NAME = os.environ.get("COSMOS_CONTAINER", "hotels")
LOCATION = os.environ.get("COSMOS_LOCATION", "eastus2")

MGMT_API = "https://management.azure.com"
COSMOS_API_VERSION = "2024-05-15"


def _bearer() -> str:
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default")
    return token.token


def _mgmt_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _account_url() -> str:
    return (
        f"{MGMT_API}/subscriptions/{SUBSCRIPTION_ID}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.DocumentDB/databaseAccounts/{ACCOUNT_NAME}"
    )


def _poll_provisioning(token: str, timeout: int = 600) -> None:
    """Poll until Cosmos DB account is provisioned."""
    headers = _mgmt_headers(token)
    url = f"{_account_url()}?api-version={COSMOS_API_VERSION}"
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            state = resp.json().get("properties", {}).get("provisioningState", "")
            if state == "Succeeded":
                print(f"  Account provisioned ({state})")
                return
            print(f"  Provisioning state: {state}...")
        time.sleep(10)
    raise TimeoutError(f"Cosmos DB account did not provision within {timeout}s")


# ── Step 1: Create Cosmos DB account (serverless NoSQL) ─────────────────────

def create_account(token: str) -> dict:
    """Create or update the Cosmos DB account with serverless capacity."""
    print(f"Creating Cosmos DB account '{ACCOUNT_NAME}' in {LOCATION}...")
    url = f"{_account_url()}?api-version={COSMOS_API_VERSION}"
    body = {
        "location": LOCATION,
        "kind": "GlobalDocumentDB",
        "properties": {
            "databaseAccountOfferType": "Standard",
            "locations": [{"locationName": LOCATION, "failoverPriority": 0}],
            "capabilities": [{"name": "EnableServerless"}],
        },
    }
    resp = requests.put(url, headers=_mgmt_headers(token), json=body)
    if resp.status_code not in (200, 201):
        print(f"ERROR: {resp.status_code} — {resp.text[:500]}")
        sys.exit(1)
    print(f"  PUT returned {resp.status_code}")
    _poll_provisioning(token)
    return resp.json()


# ── Step 2: Get connection string ────────────────────────────────────────────

def get_connection_string(token: str) -> str:
    """Fetch the primary connection string for the Cosmos DB account."""
    url = f"{_account_url()}/listConnectionStrings?api-version={COSMOS_API_VERSION}"
    resp = requests.post(url, headers=_mgmt_headers(token))
    if resp.status_code != 200:
        print(f"ERROR listing connection strings: {resp.status_code}")
        sys.exit(1)
    strings = resp.json().get("connectionStrings", [])
    if not strings:
        print("ERROR: No connection strings returned")
        sys.exit(1)
    return strings[0]["connectionString"]


# ── Step 3: Create database + container via data plane ───────────────────────

def _data_plane_endpoint(token: str) -> str:
    """Get the Cosmos DB document endpoint."""
    url = f"{_account_url()}?api-version={COSMOS_API_VERSION}"
    resp = requests.get(url, headers=_mgmt_headers(token))
    return resp.json()["properties"]["documentEndpoint"]


def create_database_and_container(connection_string: str) -> None:
    """Create database and container using the Cosmos DB REST API via connection string.
    
    We use the Azure SDK for simplicity.
    """
    try:
        from azure.cosmos import CosmosClient, PartitionKey
    except ImportError:
        print("ERROR: azure-cosmos package not installed. Run: pip install azure-cosmos")
        sys.exit(1)

    client = CosmosClient.from_connection_string(connection_string)

    print(f"Creating database '{DATABASE_NAME}'...")
    db = client.create_database_if_not_exists(id=DATABASE_NAME)

    print(f"Creating container '{CONTAINER_NAME}' with partition key /HotelId...")
    container = db.create_container_if_not_exists(
        id=CONTAINER_NAME,
        partition_key=PartitionKey(path="/HotelId"),
    )
    return container


# ── Step 4: Seed hotel documents ─────────────────────────────────────────────

HOTELS = [
    {
        "id": "1", "HotelId": "1", "HotelName": "Stay-Kay City Hotel",
        "Description": "The hotel is ideally located on the main commercial artery of the city in the heart of New York.",
        "Category": "Boutique", "Tags": ["pool", "air conditioning", "concierge"],
        "ParkingIncluded": False, "Rating": 3.6,
        "Address": {"StreetAddress": "677 5th Ave", "City": "New York", "StateProvince": "NY", "PostalCode": "10022", "Country": "USA"},
    },
    {
        "id": "2", "HotelId": "2", "HotelName": "Old Century Hotel",
        "Description": "The hotel is situated in a nineteenth century plaza, which has been expanded and renovated to the highest architectural standards.",
        "Category": "Boutique", "Tags": ["pool", "free wifi", "concierge"],
        "ParkingIncluded": False, "Rating": 3.6,
        "Address": {"StreetAddress": "140 University Town Center Dr", "City": "Sarasota", "StateProvince": "FL", "PostalCode": "34243", "Country": "USA"},
    },
    {
        "id": "3", "HotelId": "3", "HotelName": "Gastronomic Landscape Hotel",
        "Description": "The hotel stands out for its gastronomic excellence under the management of William Dede.",
        "Category": "Resort and Spa", "Tags": ["air conditioning", "bar", "continental breakfast"],
        "ParkingIncluded": True, "Rating": 4.8,
        "Address": {"StreetAddress": "3393 Peachtree Rd", "City": "Atlanta", "StateProvince": "GA", "PostalCode": "30326", "Country": "USA"},
    },
    {
        "id": "4", "HotelId": "4", "HotelName": "Sublime Palace Hotel",
        "Description": "Sublime Palace Hotel is a perfect blend of luxury accommodation and convenient location.",
        "Category": "Boutique", "Tags": ["concierge", "view", "24-hour front desk service"],
        "ParkingIncluded": True, "Rating": 4.6,
        "Address": {"StreetAddress": "7400 San Pedro Ave", "City": "San Antonio", "StateProvince": "TX", "PostalCode": "78216", "Country": "USA"},
    },
    {
        "id": "5", "HotelId": "5", "HotelName": "Perfect Resort and Spa",
        "Description": "Best resort and spa just south of Seattle overlooking the magnificent mountains.",
        "Category": "Resort and Spa", "Tags": ["laundry service", "free wifi", "free parking"],
        "ParkingIncluded": True, "Rating": 4.9,
        "Address": {"StreetAddress": "22 Survey Rd", "City": "Bellevue", "StateProvince": "WA", "PostalCode": "98007", "Country": "USA"},
    },
    {
        "id": "6", "HotelId": "6", "HotelName": "Fancy Stay",
        "Description": "This lovely hotel in the countryside is perfect for an extended stay.",
        "Category": "Budget", "Tags": ["free wifi", "coffee in lobby"],
        "ParkingIncluded": True, "Rating": 3.2,
        "Address": {"StreetAddress": "100 Country Ln", "City": "Woodstock", "StateProvince": "VT", "PostalCode": "05091", "Country": "USA"},
    },
    {
        "id": "7", "HotelId": "7", "HotelName": "Modern Stay Hotel",
        "Description": "A mid-century modern hotel with all the amenities you need for a comfortable stay.",
        "Category": "Suite", "Tags": ["pool", "bar", "view"],
        "ParkingIncluded": False, "Rating": 4.1,
        "Address": {"StreetAddress": "250 Broadway", "City": "Portland", "StateProvince": "OR", "PostalCode": "97204", "Country": "USA"},
    },
    {
        "id": "8", "HotelId": "8", "HotelName": "Riverside Inn",
        "Description": "Charming riverside inn with scenic views and quiet rooms for a peaceful retreat.",
        "Category": "Budget", "Tags": ["free parking", "continental breakfast"],
        "ParkingIncluded": True, "Rating": 3.8,
        "Address": {"StreetAddress": "44 River Rd", "City": "Asheville", "StateProvince": "NC", "PostalCode": "28801", "Country": "USA"},
    },
    {
        "id": "9", "HotelId": "9", "HotelName": "Hilltop Heritage Hotel",
        "Description": "Historic hilltop hotel renovated with modern comforts while preserving its heritage charm.",
        "Category": "Boutique", "Tags": ["concierge", "spa", "view"],
        "ParkingIncluded": False, "Rating": 4.4,
        "Address": {"StreetAddress": "1 Heritage Dr", "City": "Savannah", "StateProvince": "GA", "PostalCode": "31401", "Country": "USA"},
    },
    {
        "id": "10", "HotelId": "10", "HotelName": "Alpine Lodge",
        "Description": "Mountain lodge offering ski-in/ski-out access and breathtaking alpine panoramas.",
        "Category": "Resort and Spa", "Tags": ["free parking", "pool", "spa"],
        "ParkingIncluded": True, "Rating": 4.7,
        "Address": {"StreetAddress": "888 Summit Rd", "City": "Vail", "StateProvince": "CO", "PostalCode": "81657", "Country": "USA"},
    },
]


def seed_data(container) -> None:
    """Upsert hotel documents into the Cosmos container."""
    print(f"Seeding {len(HOTELS)} hotel documents...")
    for hotel in HOTELS:
        container.upsert_item(hotel)
        print(f"  Upserted hotel {hotel['HotelId']}: {hotel['HotelName']}")
    print("Done.")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    token = _bearer()

    # 1. Create or update the Cosmos DB account
    create_account(token)

    # 2. Get connection string
    conn_str = get_connection_string(token)
    print(f"\nConnection string (first 60 chars): {conn_str[:60]}...")

    # 3. Create database and container
    container = create_database_and_container(conn_str)

    # 4. Seed data
    seed_data(container)

    # 5. Output for .env
    print(f"\n── Add to .env ──")
    print(f"COSMOS_CONNECTION_STRING={conn_str}")
    print(f"COSMOS_DATABASE={DATABASE_NAME}")
    print(f"COSMOS_CONTAINER={CONTAINER_NAME}")


if __name__ == "__main__":
    main()
