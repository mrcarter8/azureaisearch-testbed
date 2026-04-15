"""Quick check: what SKU is the configured service actually running?"""
import os
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

sub = os.environ["AZURE_SUBSCRIPTION_ID"]
rg = os.environ["AZURE_RESOURCE_GROUP"]
svc = os.environ["SEARCH_SERVICE_NAME"]
api = os.environ.get("SEARCH_MGMT_API_VERSION", "2026-03-01-Preview")

token = subprocess.check_output(
    ["az", "account", "get-access-token", "--query", "accessToken", "-o", "tsv"]
).decode().strip()

url = (
    f"https://management.azure.com/subscriptions/{sub}/resourceGroups/{rg}"
    f"/providers/Microsoft.Search/searchServices/{svc}?api-version={api}"
)
r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
data = r.json()

sku = data.get("sku", {})
props = data.get("properties", {})
print(f"Service:        {svc}")
print(f"SKU name:       {sku.get('name', 'UNKNOWN')}")
print(f"Hosting mode:   {props.get('hostingMode', 'UNKNOWN')}")
print(f"Status:         {props.get('status', 'UNKNOWN')}")
print(f"Semantic search:{props.get('semanticSearch', 'UNKNOWN')}")
print(f"Location:       {data.get('location', 'UNKNOWN')}")
print(f"Full SKU:       {sku}")
