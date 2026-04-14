#!/usr/bin/env python
"""
setup_resources.py — Automated provisioning of all external resources for the
serverless bug-bash smoke test suite.

Usage:
    python setup_resources.py setup      # Create + populate all resources
    python setup_resources.py teardown   # Destroy test-created resources
    python setup_resources.py status     # Show which resources exist

Idempotent — safe to run repeatedly.  Creates only what is missing.

What gets created:
    1. Resource groups (search + supporting)
    2. Azure AI Search service (serverless SKU, system-assigned MSI)
    3. Storage account + blob container + 10 hotel JSON files
    4. Cosmos DB account (serverless NoSQL) + database + container + 10 hotels
    5. Azure SQL server (+ serverless DB + Hotels table w/ change tracking + 10 hotels)
    6. Azure Function app + custom skill deployment
    7. Key Vault RBAC grant for CMK

Writes all connection strings / keys to .env automatically.

Prerequisites:
    - Azure CLI (az) logged in to the correct subscription
    - pip install -r requirements-setup.txt   (azure-cosmos, pyodbc)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import string
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# ═══════════════════════════════════════════════════════════════════════════════
# Load existing .env values as fallback defaults
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from dotenv import dotenv_values
    _existing = dotenv_values(SCRIPT_DIR / ".env") if (SCRIPT_DIR / ".env").exists() else {}
except ImportError:
    _existing = {}


def _d(key: str, fallback: str = "") -> str:
    """Default value: environment variable > existing .env > fallback."""
    return os.environ.get(key) or _existing.get(key) or fallback


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION — Override via env vars or edit defaults below
# ═══════════════════════════════════════════════════════════════════════════════

SUBSCRIPTION     = _d("AZURE_SUBSCRIPTION_ID", "c4a547de-4411-4447-964d-1edbc72cf116")
SEARCH_RG        = _d("AZURE_RESOURCE_GROUP", "Serverless-bugbash")
SUPPORT_RG       = _d("SUPPORT_RESOURCE_GROUP", "SSS3PT_mcarter_azs")
SEARCH_LOCATION  = _d("SEARCH_LOCATION", "centraluseuap")
SUPPORT_LOCATION = _d("SUPPORT_LOCATION", "eastus2")

SEARCH_NAME      = _d("SEARCH_SERVICE_NAME", "mcarter-serverless")
SEARCH_API_VER   = "2025-11-01-preview"
MGMT_API_VER     = "2026-03-01-Preview"
PPE_SUFFIX       = "search-ppe.windows-int.net"

STORAGE_ACCOUNT  = _d("STORAGE_ACCOUNT", "mcarterstr")
BLOB_CONTAINER   = _d("BLOB_CONTAINER_NAME", "hotels")

COSMOS_ACCOUNT   = _d("COSMOS_ACCOUNT_NAME", "mcarter-smoke-cosmos")
COSMOS_DATABASE  = _d("COSMOS_DATABASE", "hotels-db")
COSMOS_CONTAINER = _d("COSMOS_CONTAINER", "hotels")

SQL_SERVER       = _d("SQL_SERVER_NAME", "mcarter-smoke-sql")
SQL_DATABASE     = _d("SQL_DATABASE_NAME", "hotelsdb")
SQL_ADMIN        = _d("SQL_ADMIN_USER", "smokeadmin")
SQL_TABLE        = _d("AZURE_SQL_TABLE", "Hotels")

FUNCTION_APP     = _d("CUSTOM_SKILL_FUNCTION_APP", "mcarter-serverless-func")
SKILL_DIR        = SCRIPT_DIR / "custom_skill"

CMK_VAULT_URI    = _d("CMK_KEY_VAULT_URI", "https://cmkprereqs-kv.vault.azure.net/")
CMK_KEY_NAME     = _d("CMK_KEY_NAME", "cmkprereqs-cmk")
_m = re.search(r"https://([^.]+)\.", CMK_VAULT_URI)
CMK_VAULT_NAME   = _m.group(1) if _m else ""

AOAI_ENDPOINT    = _d("AZURE_OPENAI_ENDPOINT", "https://mcarter-4925-resource.cognitiveservices.azure.com")
AOAI_API_KEY     = _d("AZURE_OPENAI_API_KEY")


# ═══════════════════════════════════════════════════════════════════════════════
# HOTEL DATA — shared across all data sources
# ═══════════════════════════════════════════════════════════════════════════════

HOTELS = [
    {"id": "1", "HotelId": "1", "HotelName": "Stay-Kay City Hotel",
     "Description": "The hotel is ideally located on the main commercial artery of the city in the heart of New York.",
     "Category": "Boutique", "Tags": ["pool", "air conditioning", "concierge"],
     "ParkingIncluded": False, "Rating": 3.6, "LastRenovationDate": "2015-06-27T00:00:00Z",
     "Address": {"StreetAddress": "677 5th Ave", "City": "New York", "StateProvince": "NY"}},
    {"id": "2", "HotelId": "2", "HotelName": "Old Century Hotel",
     "Description": "The hotel is situated in a nineteenth century plaza, which has been expanded and renovated to the highest architectural standards.",
     "Category": "Boutique", "Tags": ["pool", "free wifi", "concierge"],
     "ParkingIncluded": False, "Rating": 3.6, "LastRenovationDate": "2019-02-18T00:00:00Z",
     "Address": {"StreetAddress": "140 University Town Center Dr", "City": "Sarasota", "StateProvince": "FL"}},
    {"id": "3", "HotelId": "3", "HotelName": "Gastronomic Landscape Hotel",
     "Description": "The hotel stands out for its gastronomic excellence under the management of William Dede.",
     "Category": "Resort and Spa", "Tags": ["air conditioning", "bar", "continental breakfast"],
     "ParkingIncluded": True, "Rating": 4.8, "LastRenovationDate": "2018-09-01T00:00:00Z",
     "Address": {"StreetAddress": "3393 Peachtree Rd", "City": "Atlanta", "StateProvince": "GA"}},
    {"id": "4", "HotelId": "4", "HotelName": "Sublime Palace Hotel",
     "Description": "Sublime Palace Hotel is a perfect blend of luxury accommodation and convenient location.",
     "Category": "Boutique", "Tags": ["concierge", "view", "24-hour front desk service"],
     "ParkingIncluded": True, "Rating": 4.6, "LastRenovationDate": "2020-11-12T00:00:00Z",
     "Address": {"StreetAddress": "7400 San Pedro Ave", "City": "San Antonio", "StateProvince": "TX"}},
    {"id": "5", "HotelId": "5", "HotelName": "Perfect Resort and Spa",
     "Description": "Best resort and spa just south of Seattle overlooking the magnificent mountains.",
     "Category": "Resort and Spa", "Tags": ["laundry service", "free wifi", "free parking"],
     "ParkingIncluded": True, "Rating": 4.9, "LastRenovationDate": "2021-05-20T00:00:00Z",
     "Address": {"StreetAddress": "22 Survey Rd", "City": "Bellevue", "StateProvince": "WA"}},
    {"id": "6", "HotelId": "6", "HotelName": "Fancy Stay",
     "Description": "This lovely hotel in the countryside is perfect for an extended stay.",
     "Category": "Budget", "Tags": ["free wifi", "coffee in lobby"],
     "ParkingIncluded": True, "Rating": 3.2, "LastRenovationDate": "2017-03-15T00:00:00Z",
     "Address": {"StreetAddress": "100 Country Ln", "City": "Woodstock", "StateProvince": "VT"}},
    {"id": "7", "HotelId": "7", "HotelName": "Modern Stay Hotel",
     "Description": "A mid-century modern hotel with all the amenities you need for a comfortable stay.",
     "Category": "Suite", "Tags": ["pool", "bar", "view"],
     "ParkingIncluded": False, "Rating": 4.1, "LastRenovationDate": "2022-01-10T00:00:00Z",
     "Address": {"StreetAddress": "250 Broadway", "City": "Portland", "StateProvince": "OR"}},
    {"id": "8", "HotelId": "8", "HotelName": "Riverside Inn",
     "Description": "Charming riverside inn with scenic views and quiet rooms for a peaceful retreat.",
     "Category": "Budget", "Tags": ["free parking", "continental breakfast"],
     "ParkingIncluded": True, "Rating": 3.8, "LastRenovationDate": "2016-08-22T00:00:00Z",
     "Address": {"StreetAddress": "44 River Rd", "City": "Asheville", "StateProvince": "NC"}},
    {"id": "9", "HotelId": "9", "HotelName": "Hilltop Heritage Hotel",
     "Description": "Historic hilltop hotel renovated with modern comforts while preserving its heritage charm.",
     "Category": "Boutique", "Tags": ["concierge", "spa", "view"],
     "ParkingIncluded": False, "Rating": 4.4, "LastRenovationDate": "2023-04-05T00:00:00Z",
     "Address": {"StreetAddress": "1 Heritage Dr", "City": "Savannah", "StateProvince": "GA"}},
    {"id": "10", "HotelId": "10", "HotelName": "Alpine Lodge",
     "Description": "Mountain lodge offering ski-in/ski-out access and breathtaking alpine panoramas.",
     "Category": "Resort and Spa", "Tags": ["free parking", "pool", "spa"],
     "ParkingIncluded": True, "Rating": 4.7, "LastRenovationDate": "2024-01-30T00:00:00Z",
     "Address": {"StreetAddress": "888 Summit Rd", "City": "Vail", "StateProvince": "CO"}},
]


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def _az(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    """Run an Azure CLI command."""
    r = _run(["az"] + list(args))
    if check and r.returncode != 0:
        print(f"    ERROR: {r.stderr.strip()[:300]}")
        sys.exit(1)
    return r


def _az_json(*args: str) -> dict | list | None:
    """Run az CLI and parse JSON output."""
    r = _az(*args, "-o", "json")
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def _az_text(*args: str) -> str:
    """Run az CLI and return trimmed text output."""
    r = _az(*args, "-o", "tsv")
    return r.stdout.strip()


def _az_rest(method: str, url: str, body: dict | None = None) -> dict | None:
    """Call az rest, using temp file for body (safe on Windows)."""
    args = ["rest", "--method", method, "--url", url]
    tmp = None
    try:
        if body is not None:
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump(body, tmp)
            tmp.close()
            args += ["--body", f"@{tmp.name}"]
        r = _az(*args)
        if r.returncode != 0:
            # Surface the error but don't crash — caller decides
            return None
        return json.loads(r.stdout) if r.stdout.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return None
    finally:
        if tmp and os.path.exists(tmp.name):
            os.unlink(tmp.name)


def _mask(s: str) -> str:
    if not s or len(s) <= 8:
        return "****"
    return s[:4] + "****" + s[-4:]


def _generate_sql_password() -> str:
    """Generate a SQL-compliant password (uppercase + lowercase + digit + special)."""
    pw = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%&*"),
    ]
    pool = string.ascii_letters + string.digits + "!@#$%&*"
    pw.extend(secrets.choice(pool) for _ in range(12))
    secrets.SystemRandom().shuffle(pw)
    return "".join(pw)


def _get_my_ip() -> str:
    """Current public IP for SQL firewall rules."""
    try:
        import requests
        return requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception:
        return "0.0.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 0 — Prerequisites
# ═══════════════════════════════════════════════════════════════════════════════

def check_prerequisites() -> None:
    print("\n[0/8] Checking prerequisites...")
    # az CLI
    r = _run(["az", "version"])
    if r.returncode != 0:
        sys.exit("  ERROR: Azure CLI (az) not found.  https://aka.ms/installazurecli")
    ver = json.loads(r.stdout).get("azure-cli", "?")
    print(f"  Azure CLI: {ver}")

    # Logged in?
    r = _az("account", "show", "-o", "json")
    if r.returncode != 0:
        sys.exit("  ERROR: Not logged in. Run: az login")
    acct = json.loads(r.stdout)
    print(f"  Subscription: {acct['name']} ({acct['id']})")
    if acct["id"] != SUBSCRIPTION:
        print(f"  WARNING: expected subscription {SUBSCRIPTION}")
        print(f"           Run: az account set --subscription {SUBSCRIPTION}")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Resource Groups
# ═══════════════════════════════════════════════════════════════════════════════

def setup_resource_groups() -> None:
    print("\n[1/8] Resource groups...")
    for rg, loc in [(SEARCH_RG, SEARCH_LOCATION), (SUPPORT_RG, SUPPORT_LOCATION)]:
        r = _az("group", "show", "-n", rg)
        if r.returncode == 0:
            print(f"  {rg}: exists")
        else:
            print(f"  Creating {rg} in {loc}...")
            _az("group", "create", "-n", rg, "-l", loc, check=True)
            print(f"  {rg}: created")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — Search Service
# ═══════════════════════════════════════════════════════════════════════════════

def _search_mgmt_url(path: str = "") -> str:
    return (
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION}"
        f"/resourceGroups/{SEARCH_RG}"
        f"/providers/Microsoft.Search/searchServices/{SEARCH_NAME}"
        f"{path}?api-version={MGMT_API_VER}"
    )


def setup_search_service() -> dict:
    """Returns dict with admin_key, query_key, endpoint, principal_id."""
    print(f"\n[2/8] Search service ({SEARCH_NAME})...")

    # Check if exists
    svc = _az_rest("GET", _search_mgmt_url())
    if svc and svc.get("properties", {}).get("status") == "running":
        print(f"  Service exists, status: running")
    else:
        # Create
        print(f"  Creating serverless service in {SEARCH_LOCATION}... (2-5 min)")
        body = {
            "location": SEARCH_LOCATION,
            "sku": {"name": "serverless"},
            "identity": {"type": "SystemAssigned"},
            "properties": {
                "authOptions": {"aadOrApiKey": {"aadAuthFailureMode": "http403"}},
                "semanticSearch": "free",
            },
        }
        svc = _az_rest("PUT", _search_mgmt_url(), body)
        if svc is None:
            sys.exit("  ERROR: Failed to create search service.")

        # Poll until running
        for _ in range(60):
            time.sleep(10)
            svc = _az_rest("GET", _search_mgmt_url())
            status = (svc or {}).get("properties", {}).get("status", "unknown")
            print(f"    status: {status}")
            if status == "running":
                break
        else:
            sys.exit("  ERROR: Search service did not reach 'running' state.")

    # Ensure MSI is on
    identity = (svc or {}).get("identity", {})
    if identity.get("type", "None") == "None":
        print("  Enabling system-assigned managed identity...")
        _az_rest("PATCH", _search_mgmt_url(), {"identity": {"type": "SystemAssigned"}})
        svc = _az_rest("GET", _search_mgmt_url())
        identity = (svc or {}).get("identity", {})

    principal_id = identity.get("principalId", "")
    print(f"  MSI principal: {principal_id[:12]}..." if principal_id else "  MSI: not available")

    # Get admin key
    keys = _az_rest("POST", _search_mgmt_url("/listAdminKeys"))
    admin_key = (keys or {}).get("primaryKey", "")
    print(f"  Admin key: {_mask(admin_key)}")

    # Ensure at least one query key exists
    qk_resp = _az_rest("POST", _search_mgmt_url("/listQueryKeys"))
    query_keys = (qk_resp or {}).get("value", [])
    if query_keys:
        query_key = query_keys[0].get("key", "")
    else:
        print("  Creating query key...")
        qk = _az_rest("POST", _search_mgmt_url("/createQueryKey/smoke-test-qk"))
        query_key = (qk or {}).get("key", "")
    print(f"  Query key: {_mask(query_key)}")

    endpoint = f"https://{SEARCH_NAME}.{PPE_SUFFIX}"

    return {
        "admin_key": admin_key,
        "query_key": query_key,
        "endpoint": endpoint,
        "principal_id": principal_id,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Storage Account + Blob Container + Data
# ═══════════════════════════════════════════════════════════════════════════════

def setup_storage() -> str:
    """Returns blob connection string."""
    print(f"\n[3/8] Storage account ({STORAGE_ACCOUNT})...")

    # Create account (idempotent)
    r = _az("storage", "account", "show", "-g", SUPPORT_RG, "-n", STORAGE_ACCOUNT)
    if r.returncode == 0:
        print(f"  Account exists")
    else:
        print(f"  Creating storage account in {SUPPORT_LOCATION}...")
        _az("storage", "account", "create",
            "-g", SUPPORT_RG, "-n", STORAGE_ACCOUNT, "-l", SUPPORT_LOCATION,
            "--sku", "Standard_LRS", check=True)

    # Get connection string
    conn_str = _az_text("storage", "account", "show-connection-string",
                        "-g", SUPPORT_RG, "-n", STORAGE_ACCOUNT,
                        "--query", "connectionString")
    print(f"  Connection string: {_mask(conn_str)}")

    # Create container
    _az("storage", "container", "create",
        "--connection-string", conn_str, "--name", BLOB_CONTAINER)
    print(f"  Container '{BLOB_CONTAINER}': ready")

    # Upload hotel data as individual JSON blobs
    print(f"  Uploading {len(HOTELS)} hotel blobs...")
    for hotel in HOTELS:
        blob_name = f"hotel-{hotel['HotelId']}.json"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(hotel, f, indent=2)
            f.flush()
            _az("storage", "blob", "upload",
                "--connection-string", conn_str,
                "--container-name", BLOB_CONTAINER,
                "--name", blob_name,
                "--file", f.name,
                "--overwrite", "true")
        os.unlink(f.name)
    print(f"  Blobs uploaded")

    return conn_str


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — Cosmos DB
# ═══════════════════════════════════════════════════════════════════════════════

def setup_cosmos() -> str:
    """Returns Cosmos connection string."""
    print(f"\n[4/8] Cosmos DB ({COSMOS_ACCOUNT})...")

    # Create account (serverless NoSQL) — this is the slowest step (~5 min)
    r = _az("cosmosdb", "show", "-g", SUPPORT_RG, "-n", COSMOS_ACCOUNT)
    if r.returncode == 0:
        print(f"  Account exists")
    else:
        print(f"  Creating serverless NoSQL account in {SUPPORT_LOCATION}... (5-10 min)")
        _az("cosmosdb", "create",
            "-g", SUPPORT_RG, "-n", COSMOS_ACCOUNT, "-l", SUPPORT_LOCATION,
            "--capabilities", "EnableServerless",
            "--kind", "GlobalDocumentDB", check=True)
        print(f"  Account created")

    # Get connection string
    conn_str = _az_text("cosmosdb", "keys", "list",
                        "-g", SUPPORT_RG, "-n", COSMOS_ACCOUNT,
                        "--type", "connection-strings",
                        "--query", "connectionStrings[0].connectionString")
    print(f"  Connection string: {_mask(conn_str)}")

    # Create database + container + seed data via SDK
    try:
        from azure.cosmos import CosmosClient, PartitionKey
    except ImportError:
        print("  SKIP data seeding: azure-cosmos not installed")
        print("  Run: pip install -r requirements-setup.txt")
        return conn_str

    client = CosmosClient.from_connection_string(conn_str)
    db = client.create_database_if_not_exists(id=COSMOS_DATABASE)
    print(f"  Database '{COSMOS_DATABASE}': ready")
    container = db.create_container_if_not_exists(
        id=COSMOS_CONTAINER,
        partition_key=PartitionKey(path="/HotelId"),
    )
    print(f"  Container '{COSMOS_CONTAINER}': ready")

    for hotel in HOTELS:
        container.upsert_item(hotel)
    print(f"  Seeded {len(HOTELS)} hotels")

    return conn_str


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — Azure SQL
# ═══════════════════════════════════════════════════════════════════════════════

def setup_sql() -> tuple[str, str]:
    """Returns (ADO.NET connection string, password)."""
    print(f"\n[5/8] Azure SQL ({SQL_SERVER})...")

    # Password: reuse from .env or generate fresh
    password = _d("AZURE_SQL_ADMIN_PASSWORD", "")
    if not password:
        password = _generate_sql_password()

    # Create server
    r = _az("sql", "server", "show", "-g", SUPPORT_RG, "-n", SQL_SERVER)
    if r.returncode == 0:
        print(f"  Server exists — updating admin password")
        _az("sql", "server", "update",
            "-g", SUPPORT_RG, "-n", SQL_SERVER,
            "--admin-password", password)
    else:
        print(f"  Creating SQL server in {SUPPORT_LOCATION}...")
        _az("sql", "server", "create",
            "-g", SUPPORT_RG, "-n", SQL_SERVER, "-l", SUPPORT_LOCATION,
            "--admin-user", SQL_ADMIN,
            "--admin-password", password, check=True)
        print(f"  Server created")

    # Create database (serverless Gen5, 1 vCore)
    r = _az("sql", "db", "show", "-g", SUPPORT_RG, "-s", SQL_SERVER, "-n", SQL_DATABASE)
    if r.returncode == 0:
        print(f"  Database '{SQL_DATABASE}' exists")
    else:
        print(f"  Creating database '{SQL_DATABASE}' (serverless Gen5)...")
        _az("sql", "db", "create",
            "-g", SUPPORT_RG, "-s", SQL_SERVER, "-n", SQL_DATABASE,
            "--compute-model", "Serverless",
            "--edition", "GeneralPurpose",
            "--family", "Gen5", "--capacity", "1",
            "--auto-pause-delay", "60", check=True)
        print(f"  Database created")

    # Firewall: current IP + Azure services
    my_ip = _get_my_ip()
    print(f"  Firewall: allowing {my_ip}")
    _az("sql", "server", "firewall-rule", "create",
        "-g", SUPPORT_RG, "-s", SQL_SERVER,
        "-n", "AllowSetup", "--start-ip-address", my_ip, "--end-ip-address", my_ip)
    _az("sql", "server", "firewall-rule", "create",
        "-g", SUPPORT_RG, "-s", SQL_SERVER,
        "-n", "AllowAzureServices",
        "--start-ip-address", "0.0.0.0", "--end-ip-address", "0.0.0.0")

    # Build ADO.NET connection string (what Azure AI Search needs)
    conn_str = (
        f"Server=tcp:{SQL_SERVER}.database.windows.net,1433;"
        f"Initial Catalog={SQL_DATABASE};"
        f"User ID={SQL_ADMIN};"
        f"Password={password};"
        f"Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
    )
    print(f"  Connection string: Server=tcp:{SQL_SERVER}.database.windows.net...")

    # Seed data
    _seed_sql(conn_str)

    return conn_str, password


def _seed_sql(conn_str_ado: str) -> None:
    """Create table with change tracking and seed hotel data."""
    try:
        import pyodbc
    except ImportError:
        print("  SKIP data seeding: pyodbc not installed")
        print("  Run: pip install -r requirements-setup.txt")
        return

    # Find ODBC driver
    drivers = pyodbc.drivers()
    driver = None
    for d in ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"]:
        if d in drivers:
            driver = d
            break
    if not driver:
        print(f"  SKIP: No SQL Server ODBC driver.  Available: {drivers}")
        return

    # Parse ADO.NET → ODBC
    parts = {}
    for segment in conn_str_ado.split(";"):
        if "=" in segment:
            k, v = segment.split("=", 1)
            parts[k.strip()] = v.strip()
    server = parts.get("Server", "").replace("tcp:", "").rstrip(",1433")
    database = parts.get("Initial Catalog", "")
    uid = parts.get("User ID", "")
    pwd = parts.get("Password", "")
    odbc = (
        f"DRIVER={{{driver}}};SERVER={server};"
        f"DATABASE={database};UID={uid};PWD={pwd};"
        f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )

    try:
        conn = pyodbc.connect(odbc, timeout=60)
    except Exception as e:
        print(f"  ERROR connecting to SQL: {e}")
        return

    cursor = conn.cursor()

    # Enable change tracking on database
    cursor.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.change_tracking_databases
                       WHERE database_id = DB_ID())
        ALTER DATABASE CURRENT SET CHANGE_TRACKING = ON
            (CHANGE_RETENTION = 2 DAYS, AUTO_CLEANUP = ON)
    """)
    conn.commit()

    # Create table
    cursor.execute(f"""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = '{SQL_TABLE}')
        CREATE TABLE {SQL_TABLE} (
            HotelId          NVARCHAR(50)  NOT NULL PRIMARY KEY,
            HotelName        NVARCHAR(200),
            Description      NVARCHAR(MAX),
            Category         NVARCHAR(100),
            ParkingIncluded  BIT,
            Rating           FLOAT,
            LastRenovationDate DATETIME2,
            City             NVARCHAR(100),
            StateProvince    NVARCHAR(50)
        )
    """)
    conn.commit()

    # Enable change tracking on table
    cursor.execute(f"""
        IF NOT EXISTS (SELECT 1 FROM sys.change_tracking_tables
                       WHERE object_id = OBJECT_ID('{SQL_TABLE}'))
        ALTER TABLE {SQL_TABLE} ENABLE CHANGE_TRACKING
    """)
    conn.commit()
    print(f"  Table '{SQL_TABLE}' with change tracking: ready")

    # Truncate + insert (idempotent refresh)
    cursor.execute(f"DELETE FROM {SQL_TABLE}")
    for h in HOTELS:
        addr = h.get("Address", {})
        cursor.execute(
            f"INSERT INTO {SQL_TABLE} "
            f"(HotelId, HotelName, Description, Category, ParkingIncluded, "
            f"Rating, LastRenovationDate, City, StateProvince) "
            f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            h["HotelId"], h["HotelName"], h["Description"], h["Category"],
            1 if h.get("ParkingIncluded") else 0, h["Rating"],
            h.get("LastRenovationDate"), addr.get("City", ""), addr.get("StateProvince", ""),
        )
    conn.commit()
    cursor.close()
    conn.close()
    print(f"  Seeded {len(HOTELS)} hotels")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — Custom Skill Function
# ═══════════════════════════════════════════════════════════════════════════════

def setup_function() -> str:
    """Deploy custom skill function, return URL with code param."""
    print(f"\n[6/8] Custom skill function ({FUNCTION_APP})...")

    # Create function app (idempotent)
    r = _az("functionapp", "show", "-g", SUPPORT_RG, "-n", FUNCTION_APP)
    if r.returncode == 0:
        print(f"  Function app exists")
    else:
        print(f"  Creating function app (Consumption, Linux, Python 3.11)...")
        _az("functionapp", "create",
            "-g", SUPPORT_RG, "-n", FUNCTION_APP,
            "--storage-account", STORAGE_ACCOUNT,
            "--consumption-plan-location", SUPPORT_LOCATION,
            "--runtime", "python", "--runtime-version", "3.11",
            "--functions-version", "4", "--os-type", "Linux", check=True)
        print(f"  Function app created")

    # Enable remote build
    _az("functionapp", "config", "appsettings", "set",
        "-g", SUPPORT_RG, "-n", FUNCTION_APP,
        "--settings", "SCM_DO_BUILD_DURING_DEPLOYMENT=true", "ENABLE_ORYX_BUILD=true")

    # Create deployment zip (v2 model — only need function_app.py, host.json, requirements.txt)
    if not SKILL_DIR.exists():
        print(f"  SKIP: custom_skill/ directory not found at {SKILL_DIR}")
        return ""

    zip_path = SCRIPT_DIR / "custom_skill_deploy.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for fname in ["function_app.py", "host.json", "requirements.txt"]:
            fpath = SKILL_DIR / fname
            if fpath.exists():
                z.write(fpath, fname)
    print(f"  Deploying code via zip deploy...")
    r = _az("functionapp", "deployment", "source", "config-zip",
            "-g", SUPPORT_RG, "-n", FUNCTION_APP, "--src", str(zip_path))
    if zip_path.exists():
        os.unlink(zip_path)

    if r.returncode != 0:
        print(f"  WARNING: Zip deploy returned non-zero. Trying func CLI fallback...")
        _run(["func", "azure", "functionapp", "publish", FUNCTION_APP, "--python"],
             cwd=str(SKILL_DIR))

    # Wait for function to register
    print(f"  Waiting for function registration...")
    func_url = ""
    for attempt in range(12):
        time.sleep(10)
        base = _az_text("functionapp", "function", "show",
                        "-g", SUPPORT_RG, "-n", FUNCTION_APP,
                        "--function-name", "analyze",
                        "--query", "invokeUrlTemplate")
        if base:
            func_url = base
            break
        if attempt < 11:
            print(f"    attempt {attempt + 1}/12...")

    # Get function key
    func_key = _az_text("functionapp", "function", "keys", "list",
                        "-g", SUPPORT_RG, "-n", FUNCTION_APP,
                        "--function-name", "analyze",
                        "--query", "default")

    if func_url and func_key:
        full_url = f"{func_url}?code={func_key}"
    elif func_url:
        full_url = func_url
    else:
        full_url = f"https://{FUNCTION_APP}.azurewebsites.net/api/analyze"
        print(f"  WARNING: Could not discover URL dynamically, using constructed URL")

    print(f"  URL: {full_url[:60]}...")
    return full_url


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7 — CMK Key Vault RBAC
# ═══════════════════════════════════════════════════════════════════════════════

def setup_cmk(principal_id: str) -> None:
    print(f"\n[7/8] CMK permissions...")
    if not CMK_VAULT_NAME or not principal_id:
        print(f"  SKIP: vault={CMK_VAULT_NAME}, principal={principal_id[:8] if principal_id else 'none'}")
        return

    # Find vault resource group
    vault_rg = _az_text("resource", "list",
                        "--name", CMK_VAULT_NAME,
                        "--resource-type", "Microsoft.KeyVault/vaults",
                        "--query", "[0].resourceGroup")
    if not vault_rg:
        print(f"  WARNING: Key Vault '{CMK_VAULT_NAME}' not found in subscription")
        return

    scope = (
        f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{vault_rg}"
        f"/providers/Microsoft.KeyVault/vaults/{CMK_VAULT_NAME}"
    )

    # Grant Key Vault Crypto Officer
    print(f"  Granting 'Key Vault Crypto Officer' to MSI on {CMK_VAULT_NAME}...")
    r = _az("role", "assignment", "create",
            "--role", "Key Vault Crypto Officer",
            "--assignee-object-id", principal_id,
            "--assignee-principal-type", "ServicePrincipal",
            "--scope", scope)
    if r.returncode == 0 or "conflict" in r.stderr.lower() or "already exists" in r.stderr.lower():
        print(f"  RBAC assignment: ready")
    else:
        print(f"  WARNING: RBAC assignment may have failed: {r.stderr[:200]}")


# ═══════════════════════════════════════════════════════════════════════════════
# .env WRITER
# ═══════════════════════════════════════════════════════════════════════════════

def write_env(search_info: dict, blob_conn: str, cosmos_conn: str,
              sql_conn: str, sql_password: str, func_url: str) -> None:
    print(f"\n[8/8] Writing .env...")
    env_path = SCRIPT_DIR / ".env"

    content = f"""# =============================================================================
# Azure AI Search — Serverless Bug Bash Test Suite
# AUTO-GENERATED by setup_resources.py — {time.strftime('%Y-%m-%d %H:%M:%S')}
# =============================================================================

# ── Search Service ──────────────────────────────────────────────────────────
SEARCH_ENDPOINT={search_info['endpoint']}
SEARCH_ADMIN_KEY={search_info['admin_key']}
SEARCH_QUERY_KEY={search_info['query_key']}

# API versions
SEARCH_API_VERSION={SEARCH_API_VER}
SEARCH_MGMT_API_VERSION={MGMT_API_VER}

# ── Management Plane ────────────────────────────────────────────────────────
AZURE_SUBSCRIPTION_ID={SUBSCRIPTION}
AZURE_RESOURCE_GROUP={SEARCH_RG}
SEARCH_SERVICE_NAME={SEARCH_NAME}
SEARCH_LOCATION={SEARCH_LOCATION}

# ── Azure OpenAI ────────────────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT={AOAI_ENDPOINT}
AZURE_OPENAI_API_KEY={AOAI_API_KEY}
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_CHAT_MODEL=gpt-4.1-mini
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
AZURE_OPENAI_EMBEDDING_DIMENSIONS=1536
AZURE_OPENAI_API_VERSION=2024-06-01

# ── Blob Storage (indexer tests) ────────────────────────────────────────────
BLOB_CONNECTION_STRING={blob_conn}
BLOB_CONTAINER_NAME={BLOB_CONTAINER}

# ── Cosmos DB (indexer tests) ───────────────────────────────────────────────
COSMOS_CONNECTION_STRING={cosmos_conn}
COSMOS_DATABASE={COSMOS_DATABASE}
COSMOS_CONTAINER={COSMOS_CONTAINER}

# ── Azure SQL (indexer tests) ───────────────────────────────────────────────
AZURE_SQL_CONNECTION_STRING={sql_conn}
AZURE_SQL_TABLE={SQL_TABLE}
AZURE_SQL_ADMIN_PASSWORD={sql_password}

# ── CMK Encryption Tests ───────────────────────────────────────────────────
CMK_KEY_VAULT_URI={CMK_VAULT_URI}
CMK_KEY_NAME={CMK_KEY_NAME}

# ── Networking ──────────────────────────────────────────────────────────────
VNET_ENABLED=false

# ── Custom Skill (Azure Function) ──────────────────────────────────────────
CUSTOM_SKILL_FUNCTION_APP={FUNCTION_APP}
CUSTOM_SKILL_RESOURCE_GROUP={SUPPORT_RG}
CUSTOM_SKILL_URL={func_url}
"""

    env_path.write_text(content.strip() + "\n")
    print(f"  Written to {env_path}")
    print(f"  Values: {sum(1 for line in content.splitlines() if '=' in line and not line.startswith('#'))} env vars")


# ═══════════════════════════════════════════════════════════════════════════════
# SETUP (orchestrator)
# ═══════════════════════════════════════════════════════════════════════════════

def setup() -> None:
    start = time.time()
    print("=" * 60)
    print(" Serverless Bug-Bash — Resource Setup")
    print("=" * 60)

    check_prerequisites()
    setup_resource_groups()

    search_info = setup_search_service()
    blob_conn = setup_storage()
    cosmos_conn = setup_cosmos()
    sql_conn, sql_password = setup_sql()
    func_url = setup_function()
    setup_cmk(search_info["principal_id"])

    write_env(search_info, blob_conn, cosmos_conn, sql_conn, sql_password, func_url)

    elapsed = int(time.time() - start)
    print(f"\n{'=' * 60}")
    print(f" Setup complete ({elapsed // 60}m {elapsed % 60}s)")
    print(f" Run tests:  python -m pytest tests/")
    print(f"{'=' * 60}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# TEARDOWN
# ═══════════════════════════════════════════════════════════════════════════════

def teardown(delete_search: bool = False) -> None:
    print("=" * 60)
    print(" Serverless Bug-Bash — Resource Teardown")
    print("=" * 60)

    check_prerequisites()

    # Cosmos DB account
    print(f"\n  Deleting Cosmos DB account '{COSMOS_ACCOUNT}'...")
    r = _az("cosmosdb", "delete", "-g", SUPPORT_RG, "-n", COSMOS_ACCOUNT, "--yes")
    print(f"    {'Deleted' if r.returncode == 0 else 'Not found / already deleted'}")

    # Azure SQL server (cascades to DB + firewall)
    print(f"\n  Deleting SQL server '{SQL_SERVER}'...")
    r = _az("sql", "server", "delete", "-g", SUPPORT_RG, "-n", SQL_SERVER, "--yes")
    print(f"    {'Deleted' if r.returncode == 0 else 'Not found / already deleted'}")

    # Blob data (delete blobs, keep container and account)
    print(f"\n  Clearing blob container '{BLOB_CONTAINER}'...")
    conn_str = _az_text("storage", "account", "show-connection-string",
                        "-g", SUPPORT_RG, "-n", STORAGE_ACCOUNT,
                        "--query", "connectionString")
    if conn_str:
        _az("storage", "blob", "delete-batch",
            "--connection-string", conn_str,
            "--source", BLOB_CONTAINER)
        print(f"    Cleared")
    else:
        print(f"    Storage account not found")

    # Search service — only deleted when explicitly requested
    if delete_search:
        print(f"\n  Deleting search service '{SEARCH_NAME}'...")
        _az_rest("DELETE", _search_mgmt_url())
        print(f"    Delete initiated (async)")
    else:
        print(f"\n  Keeping search service '{SEARCH_NAME}' (default — use --delete-search to remove)")

    print(f"\n{'=' * 60}")
    print(f" Teardown complete")
    print(f"{'=' * 60}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def status() -> None:
    print("=" * 60)
    print(" Serverless Bug-Bash — Resource Status")
    print("=" * 60)

    check_prerequisites()

    checks = [
        ("Search service", lambda: _az("rest", "--method", "GET", "--url",
            _search_mgmt_url()).returncode == 0),
        ("Storage account", lambda: _az("storage", "account", "show",
            "-g", SUPPORT_RG, "-n", STORAGE_ACCOUNT).returncode == 0),
        ("Cosmos DB account", lambda: _az("cosmosdb", "show",
            "-g", SUPPORT_RG, "-n", COSMOS_ACCOUNT).returncode == 0),
        ("Azure SQL server", lambda: _az("sql", "server", "show",
            "-g", SUPPORT_RG, "-n", SQL_SERVER).returncode == 0),
        ("Function app", lambda: _az("functionapp", "show",
            "-g", SUPPORT_RG, "-n", FUNCTION_APP).returncode == 0),
        (".env file", lambda: (SCRIPT_DIR / ".env").exists()),
    ]

    for name, check in checks:
        try:
            ok = check()
        except Exception:
            ok = False
        marker = "EXISTS" if ok else "MISSING"
        print(f"  {name:25s} {marker}")

    print()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Provision / tear down all resources for the serverless smoke tests.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="Create + populate all resources, write .env")
    td = sub.add_parser("teardown", help="Destroy supporting resources (keeps search service by default)")
    td.add_argument("--delete-search", action="store_true",
                    help="Also delete the search service (default: keep it for bug repro)")
    sub.add_parser("status", help="Show which resources exist")

    args = parser.parse_args()

    if args.command == "setup":
        setup()
    elif args.command == "teardown":
        teardown(delete_search=args.delete_search)
    elif args.command == "status":
        status()


if __name__ == "__main__":
    main()
