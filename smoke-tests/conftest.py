"""
conftest.py — Shared pytest fixtures for the Azure AI Search test suite.

Provides:
  - Environment config loaded from .env
  - Authenticated RestClient instances (admin, query, Entra, mgmt)
  - Unique per-session resource names (``smoke-{uuid}``)
  - AOAI configuration
  - FailureReporter integration (captures every failure with HTTP context)
"""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid

import pytest
from dotenv import load_dotenv

# Ensure the project root is on sys.path so ``helpers`` is importable.
sys.path.insert(0, os.path.dirname(__file__))

from helpers.reporter import FailureEntry, FailureReporter
from helpers.rest_client import RestClient

# ── Environment ──────────────────────────────────────────────────────────────

load_dotenv(override=True)

logger = logging.getLogger("smoke-tests")


def _env(key: str, required: bool = True, default: str = "") -> str:
    val = os.environ.get(key, default)
    if required and not val:
        pytest.exit(f"Required environment variable {key} is not set. See .env.template.", returncode=1)
    return val


# ── Unique session prefix ────────────────────────────────────────────────────

SESSION_ID = uuid.uuid4().hex[:8]


# ── Fixtures — config ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def search_endpoint() -> str:
    return _env("SEARCH_ENDPOINT")


@pytest.fixture(scope="session")
def search_api_version() -> str:
    return _env("SEARCH_API_VERSION", default="2025-11-01-preview")


@pytest.fixture(scope="session")
def mgmt_api_version() -> str:
    return _env("SEARCH_MGMT_API_VERSION", default="2026-03-01-Preview")


@pytest.fixture(scope="session")
def admin_key() -> str:
    return _env("SEARCH_ADMIN_KEY")


@pytest.fixture(scope="session")
def query_key(rest) -> str:
    """Fetch query key from env or at runtime via management plane."""
    key = _env("SEARCH_QUERY_KEY", required=False)
    if key:
        return key
    # Fetch the first query key via management plane
    try:
        resp = rest.mgmt_get("/listQueryKeys")
        if resp.status_code == 200:
            keys = resp.json().get("value", [])
            if keys:
                return keys[0].get("key", "")
    except Exception:
        pass
    return ""


@pytest.fixture(scope="session")
def subscription_id() -> str:
    return _env("AZURE_SUBSCRIPTION_ID")


@pytest.fixture(scope="session")
def resource_group() -> str:
    return _env("AZURE_RESOURCE_GROUP")


@pytest.fixture(scope="session")
def service_name() -> str:
    return _env("SEARCH_SERVICE_NAME")


@pytest.fixture(scope="session")
def search_location() -> str:
    return _env("SEARCH_LOCATION", default="centraluseuap")


@pytest.fixture(scope="session")
def search_sku() -> str:
    return _env("SEARCH_SKU")


# ── Fixtures — auth headers ──────────────────────────────────────────────────

@pytest.fixture(scope="session")
def admin_headers(admin_key) -> dict:
    return {"api-key": admin_key, "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def query_headers(query_key) -> dict:
    if not query_key:
        pytest.skip("SEARCH_QUERY_KEY not set")
    return {"api-key": query_key, "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def entra_headers():
    """Bearer token via azure-identity DefaultAzureCredential."""
    try:
        from azure.identity import DefaultAzureCredential
        tenant_id = os.getenv("AZURE_TENANT_ID")
        credential = DefaultAzureCredential(additionally_allowed_tenants=["*"], **(dict(authority=f"https://login.microsoftonline.com/{tenant_id}") if tenant_id else {}))
        token = credential.get_token("https://search.azure.com/.default", tenant_id=tenant_id) if tenant_id else credential.get_token("https://search.azure.com/.default")
        return {"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"}
    except Exception as exc:
        pytest.skip(f"Entra auth not available: {exc}")


@pytest.fixture(scope="session")
def mgmt_bearer_headers():
    """Bearer token for management.azure.com."""
    try:
        from azure.identity import DefaultAzureCredential
        tenant_id = os.getenv("AZURE_TENANT_ID")
        credential = DefaultAzureCredential(additionally_allowed_tenants=["*"], **(dict(authority=f"https://login.microsoftonline.com/{tenant_id}") if tenant_id else {}))
        token = credential.get_token("https://management.azure.com/.default", tenant_id=tenant_id) if tenant_id else credential.get_token("https://management.azure.com/.default")
        return {"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"}
    except Exception as exc:
        pytest.skip(f"Management auth not available: {exc}")


# ── Fixtures — RestClient instances ──────────────────────────────────────────

@pytest.fixture(scope="session")
def rest(search_endpoint, admin_headers, search_api_version, mgmt_api_version,
         subscription_id, resource_group, service_name, mgmt_bearer_headers) -> RestClient:
    """Primary RestClient with admin API-key auth + management plane Bearer auth."""
    return RestClient(
        base_url=search_endpoint,
        headers=admin_headers,
        api_version=search_api_version,
        mgmt_api_version=mgmt_api_version,
        subscription_id=subscription_id,
        resource_group=resource_group,
        service_name=service_name,
        mgmt_headers=mgmt_bearer_headers,
    )


@pytest.fixture(scope="session")
def rest_query(search_endpoint, query_headers, search_api_version) -> RestClient:
    """RestClient with query API-key auth (read-only)."""
    return RestClient(
        base_url=search_endpoint,
        headers=query_headers,
        api_version=search_api_version,
    )


@pytest.fixture(scope="session")
def rest_entra(search_endpoint, entra_headers, search_api_version) -> RestClient:
    """RestClient with Entra bearer token auth."""
    return RestClient(
        base_url=search_endpoint,
        headers=entra_headers,
        api_version=search_api_version,
    )


@pytest.fixture(scope="session")
def rest_noauth(search_endpoint, search_api_version) -> RestClient:
    """RestClient with NO auth — for negative tests."""
    return RestClient(
        base_url=search_endpoint,
        headers={"Content-Type": "application/json"},
        api_version=search_api_version,
    )


# ── Fixtures — resource names ────────────────────────────────────────────────

@pytest.fixture(scope="session")
def primary_index_name() -> str:
    return f"smoke-hotels-{SESSION_ID}"


@pytest.fixture(scope="session")
def simple_index_name() -> str:
    return f"smoke-simple-{SESSION_ID}"


@pytest.fixture(scope="session")
def vector_index_name() -> str:
    return f"smoke-vector-{SESSION_ID}"


@pytest.fixture(scope="session")
def synonym_map_name() -> str:
    return f"smoke-synonyms-{SESSION_ID}"


@pytest.fixture(scope="session")
def datasource_blob_name() -> str:
    return f"smoke-ds-blob-{SESSION_ID}"


@pytest.fixture(scope="session")
def datasource_cosmos_name() -> str:
    return f"smoke-ds-cosmos-{SESSION_ID}"


@pytest.fixture(scope="session")
def datasource_sql_name() -> str:
    return f"smoke-ds-sql-{SESSION_ID}"


@pytest.fixture(scope="session")
def indexer_blob_name() -> str:
    return f"smoke-ixr-blob-{SESSION_ID}"


@pytest.fixture(scope="session")
def indexer_cosmos_name() -> str:
    return f"smoke-ixr-cosmos-{SESSION_ID}"


@pytest.fixture(scope="session")
def indexer_sql_name() -> str:
    return f"smoke-ixr-sql-{SESSION_ID}"


@pytest.fixture(scope="session")
def skillset_name() -> str:
    return f"smoke-skillset-{SESSION_ID}"


@pytest.fixture(scope="session")
def knowledge_source_name() -> str:
    return f"smoke-ks-{SESSION_ID}"


@pytest.fixture(scope="session")
def knowledge_base_name() -> str:
    return f"smoke-kb-{SESSION_ID}"


@pytest.fixture(scope="session")
def alias_name() -> str:
    return f"smoke-alias-{SESSION_ID}"


@pytest.fixture(scope="session")
def disposable_service_name() -> str:
    """Name for a throwaway service created/deleted in control-plane tests."""
    return f"smoke-svc-{SESSION_ID}"


# ── Fixtures — AOAI config ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def aoai_config() -> dict:
    return {
        "endpoint": _env("AZURE_OPENAI_ENDPOINT"),
        "api_key": _env("AZURE_OPENAI_API_KEY"),
        "chat_deployment": _env("AZURE_OPENAI_CHAT_DEPLOYMENT", default="gpt-4.1-mini"),
        "chat_model": _env("AZURE_OPENAI_CHAT_MODEL", default="gpt-4.1-mini"),
        "embedding_deployment": _env("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", default="text-embedding-3-small"),
        "embedding_model": _env("AZURE_OPENAI_EMBEDDING_MODEL", default="text-embedding-3-small"),
        "embedding_dimensions": int(_env("AZURE_OPENAI_EMBEDDING_DIMENSIONS", default="1536")),
        "api_version": _env("AZURE_OPENAI_API_VERSION", default="2024-06-01"),
    }


@pytest.fixture(scope="session")
def cmk_config() -> dict | None:
    vault_uri = _env("CMK_KEY_VAULT_URI", required=False)
    key_name = _env("CMK_KEY_NAME", required=False)
    if not vault_uri or not key_name:
        return None
    return {"key_vault_uri": vault_uri, "key_name": key_name}


# ── Fixtures — sample data ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def sample_data_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "sample_data")


# ── Reporter + pytest hooks ──────────────────────────────────────────────────

@pytest.fixture(scope="session")
def reporter(search_sku) -> FailureReporter:
    return FailureReporter(results_dir=os.path.join(os.path.dirname(__file__), "results", search_sku))


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "service_mgmt: control-plane service management tests")
    config.addinivalue_line("markers", "negative: negative / feature-gate tests")
    config.addinivalue_line("markers", "auth: authentication and authorization tests")
    config.addinivalue_line("markers", "indexes: index management tests")
    config.addinivalue_line("markers", "documents: document CRUD tests")
    config.addinivalue_line("markers", "synonyms: synonym map tests")
    config.addinivalue_line("markers", "queries: query modality tests")
    config.addinivalue_line("markers", "misc: miscellaneous service feature tests")
    config.addinivalue_line("markers", "indexers: indexer and data source tests")
    config.addinivalue_line("markers", "skillsets: AI enrichment skillset tests")
    config.addinivalue_line("markers", "vectorization: integrated vectorization tests")
    config.addinivalue_line("markers", "agentic: agentic retrieval tests")
    config.addinivalue_line("markers", "service_behavior: service-specific behavioral tests")
    config.addinivalue_line("markers", "service_limits: SKU limits validation tests")
    config.addinivalue_line("markers", "networking: networking tests (requires VNET)")
    config.addinivalue_line("markers", "gate: gate test — failure aborts the run")


# Store reporter at module level so hooks can access it
_reporter: FailureReporter | None = None


@pytest.fixture(scope="session", autouse=True)
def _session_reporter(reporter):
    global _reporter
    _reporter = reporter
    # Load known bugs from SKU-specific results directory
    bugs_path = reporter.results_dir / "known_bugs.json"
    if bugs_path.exists():
        import json
        try:
            bugs = json.loads(bugs_path.read_text(encoding="utf-8"))
            for test_id, url in bugs.items():
                reporter.register_bug(test_id, url)
        except Exception:
            pass
    yield
    reporter.write_reports()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Capture test outcomes and feed failures to the reporter."""
    outcome = yield
    report = outcome.get_result()

    if report.when != "call":
        return

    if _reporter is None:
        return

    _reporter.total_tests += 1

    # Extract test ID from markers or node ID
    test_id = ""
    for marker in item.iter_markers():
        if marker.name == "test_id":
            test_id = marker.args[0] if marker.args else ""
            break
    if not test_id:
        test_id = item.nodeid.split("::")[-1]

    description = (item.function.__doc__ or "").strip().split("\n")[0]

    if report.passed:
        _reporter.record_pass()
        _reporter.record_result(test_id, description, "PASS", node_id=item.nodeid)
    elif report.skipped:
        _reporter.record_skip()
        _reporter.record_result(test_id, description, "SKIP", node_id=item.nodeid)
    elif report.failed:
        # Try to find the RestClient from the test's fixtures to get last HTTP record
        rest_client: RestClient | None = None
        for fixture_name in ("rest", "rest_query", "rest_entra", "rest_noauth"):
            if fixture_name in item.funcargs:
                rest_client = item.funcargs[fixture_name]
                break

        http_request = None
        http_response = None
        x_ms_request_id = None
        elapsed_ms = None

        if rest_client and rest_client.last_record:
            rec = rest_client.last_record
            http_request = {
                "method": rec.method,
                "url": rec.url,
                "headers": rec.request_headers,
                "body": rec.request_body,
            }
            http_response = {
                "status_code": rec.status_code,
                "headers": rec.response_headers,
                "body": rec.response_body,
            }
            x_ms_request_id = rec.x_ms_request_id
            elapsed_ms = rec.elapsed_ms

        _reporter.record_result(test_id, description, "FAIL", node_id=item.nodeid)
        _reporter.failures.append(FailureEntry(
            test_id=test_id,
            test_name=item.nodeid,
            description=item.function.__doc__ or "",
            expected="(see assertion)",
            actual=f"status={http_response['status_code']}" if http_response else "exception",
            error_message=str(report.longrepr)[:5000],
            http_request=http_request,
            http_response=http_response,
            x_ms_request_id=x_ms_request_id,
            elapsed_ms=elapsed_ms,
        ))


# ── Pre-create helpers ───────────────────────────────────────────────────────

def ensure_fresh(rest: RestClient, resource_path: str, *, wait: float = 10.0) -> None:
    """Ensure a resource does NOT exist before a test creates it.

    If the resource already exists (from a previous run), delete it and wait
    *wait* seconds for the service to settle before the test proceeds.

    Args:
        rest: Authenticated RestClient.
        resource_path: API path **including the name**, e.g. ``/indexes/smoke-hotels``.
        wait: Seconds to sleep after deletion (default 10).
    """
    resp = rest.get(resource_path)
    if resp.status_code == 200:
        logger.info(f"ensure_fresh: {resource_path} exists — deleting...")
        del_resp = rest.delete(resource_path)
        if del_resp.status_code not in (204, 404):
            logger.warning(
                f"ensure_fresh: DELETE {resource_path} returned {del_resp.status_code}"
            )
        if wait > 0:
            time.sleep(wait)
        logger.info(f"ensure_fresh: {resource_path} cleared, waited {wait}s")


def ensure_fresh_many(rest: RestClient, *resource_paths: str, wait: float = 10.0) -> None:
    """Delete multiple pre-existing resources then wait once.

    Useful when a test needs several resources cleaned up before it starts
    (e.g. an indexer, its skillset, and its data source).
    """
    deleted_any = False
    for path in resource_paths:
        resp = rest.get(path)
        if resp.status_code == 200:
            logger.info(f"ensure_fresh_many: {path} exists — deleting...")
            rest.delete(path)
            deleted_any = True
    if deleted_any and wait > 0:
        time.sleep(wait)
