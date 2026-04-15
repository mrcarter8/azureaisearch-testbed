#!/usr/bin/env python
"""
teardown_resources.py — Delete ALL Azure resources created by setup_resources.py.

Usage:
    python teardown_resources.py              # Interactive — prompts for confirmation
    python teardown_resources.py --confirm    # Skip confirmation prompt

This script deletes the following resources:
    1. Azure AI Search service
    2. Azure Function App (custom skill)
    3. Azure OpenAI account + deployments
    4. Azure Cosmos DB account
    5. Azure SQL server + database
    6. Azure Blob Storage account
    7. Resource groups (if empty after deletion)

It reads resource names from .env (or environment variables / defaults)
to identify what to delete. It will NOT delete:
    - Key Vault or CMK keys (shared infrastructure)
    - Resources not matching the configured names

This is a MANUAL script — never called by tests or run_smoke.ps1.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

try:
    from dotenv import dotenv_values
    _existing = dotenv_values(SCRIPT_DIR / ".env") if (SCRIPT_DIR / ".env").exists() else {}
except ImportError:
    _existing = {}


def _d(key: str, fallback: str = "") -> str:
    return os.environ.get(key) or _existing.get(key) or fallback


# ── Configuration (mirrors setup_resources.py) ──────────────────────────────

SUBSCRIPTION     = _d("AZURE_SUBSCRIPTION_ID", "c4a547de-4411-4447-964d-1edbc72cf116")
SEARCH_RG        = _d("AZURE_RESOURCE_GROUP", "search-testbed")
SUPPORT_RG       = _d("SUPPORT_RESOURCE_GROUP", "SSS3PT_mcarter_azs")
SEARCH_NAME      = _d("SEARCH_SERVICE_NAME", "smoke-search")
STORAGE_ACCOUNT  = _d("STORAGE_ACCOUNT", "mcarterstr")
COSMOS_ACCOUNT   = _d("COSMOS_ACCOUNT_NAME", "mcarter-smoke-cosmos")
SQL_SERVER       = _d("SQL_SERVER_NAME", "mcarter-smoke-sql")
SQL_DATABASE     = _d("SQL_DATABASE_NAME", "hotelsdb")
FUNCTION_APP     = _d("CUSTOM_SKILL_FUNCTION_APP", "smoke-func")
AOAI_ACCOUNT     = _d("AZURE_OPENAI_ACCOUNT_NAME", "smoke-aoai")
AOAI_RG          = SUPPORT_RG


def _az(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["az"] + list(args), capture_output=True, text=True)


def _exists(result: subprocess.CompletedProcess) -> bool:
    return result.returncode == 0


def _delete_resource(label: str, check_cmd: list[str], delete_cmd: list[str]) -> None:
    """Check if resource exists, delete if found."""
    r = _az(*check_cmd)
    if not _exists(r):
        print(f"  {label}: not found (skip)")
        return
    print(f"  {label}: deleting...")
    r = _az(*delete_cmd)
    if r.returncode == 0:
        print(f"  {label}: deleted")
    else:
        print(f"  {label}: FAILED — {r.stderr.strip()[:200]}")


def teardown() -> None:
    print("=" * 60)
    print(" Azure AI Search Testbed — Full Resource Teardown")
    print("=" * 60)

    # Verify az login
    r = _az("account", "show", "-o", "json")
    if r.returncode != 0:
        sys.exit("ERROR: Not logged in. Run: az login")
    acct = json.loads(r.stdout)
    print(f"  Subscription: {acct['name']} ({acct['id']})")

    print(f"\nResources targeted for deletion:")
    print(f"  Search service:     {SEARCH_NAME} (RG: {SEARCH_RG})")
    print(f"  Function app:       {FUNCTION_APP} (RG: {SUPPORT_RG})")
    print(f"  OpenAI account:     {AOAI_ACCOUNT} (RG: {AOAI_RG})")
    print(f"  Cosmos DB account:  {COSMOS_ACCOUNT} (RG: {SUPPORT_RG})")
    print(f"  SQL server:         {SQL_SERVER} (RG: {SUPPORT_RG})")
    print(f"  Storage account:    {STORAGE_ACCOUNT} (RG: {SUPPORT_RG})")
    print()

    # ── 1. Search service ───────────────────────────────────────────────────
    print("[1/6] Azure AI Search service...")
    _delete_resource(
        SEARCH_NAME,
        ["search", "service", "show", "-g", SEARCH_RG, "-n", SEARCH_NAME],
        ["search", "service", "delete", "-g", SEARCH_RG, "-n", SEARCH_NAME, "--yes"],
    )

    # ── 2. Function app ─────────────────────────────────────────────────────
    print("\n[2/6] Azure Function App...")
    _delete_resource(
        FUNCTION_APP,
        ["functionapp", "show", "-g", SUPPORT_RG, "-n", FUNCTION_APP],
        ["functionapp", "delete", "-g", SUPPORT_RG, "-n", FUNCTION_APP],
    )

    # ── 3. Azure OpenAI ─────────────────────────────────────────────────────
    print("\n[3/6] Azure OpenAI account...")
    _delete_resource(
        AOAI_ACCOUNT,
        ["cognitiveservices", "account", "show", "-g", AOAI_RG, "-n", AOAI_ACCOUNT],
        ["cognitiveservices", "account", "delete", "-g", AOAI_RG, "-n", AOAI_ACCOUNT],
    )

    # ── 4. Cosmos DB ─────────────────────────────────────────────────────────
    print("\n[4/6] Cosmos DB account...")
    _delete_resource(
        COSMOS_ACCOUNT,
        ["cosmosdb", "show", "-g", SUPPORT_RG, "-n", COSMOS_ACCOUNT],
        ["cosmosdb", "delete", "-g", SUPPORT_RG, "-n", COSMOS_ACCOUNT, "--yes"],
    )

    # ── 5. Azure SQL ─────────────────────────────────────────────────────────
    print("\n[5/6] Azure SQL server...")
    _delete_resource(
        SQL_SERVER,
        ["sql", "server", "show", "-g", SUPPORT_RG, "-n", SQL_SERVER],
        ["sql", "server", "delete", "-g", SUPPORT_RG, "-n", SQL_SERVER, "--yes"],
    )

    # ── 6. Storage account ───────────────────────────────────────────────────
    print("\n[6/6] Storage account...")
    _delete_resource(
        STORAGE_ACCOUNT,
        ["storage", "account", "show", "-g", SUPPORT_RG, "-n", STORAGE_ACCOUNT],
        ["storage", "account", "delete", "-g", SUPPORT_RG, "-n", STORAGE_ACCOUNT, "--yes"],
    )

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(" Teardown complete.")
    print(" Resource groups were left in place.")
    print(" To delete them manually:")
    print(f"   az group delete -n {SEARCH_RG} --yes --no-wait")
    print(f"   az group delete -n {SUPPORT_RG} --yes --no-wait")
    print(f"{'=' * 60}\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Delete ALL Azure resources created by setup_resources.py.",
    )
    parser.add_argument("--confirm", action="store_true",
                        help="Skip the interactive confirmation prompt")
    args = parser.parse_args()

    if not args.confirm:
        print("This will DELETE all Azure resources provisioned by setup_resources.py.")
        print("This action cannot be undone.\n")
        answer = input("Type 'yes' to proceed: ").strip().lower()
        if answer != "yes":
            print("Aborted.")
            sys.exit(0)

    teardown()


if __name__ == "__main__":
    main()
