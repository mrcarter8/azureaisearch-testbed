"""
test_11_vectorization.py — Integrated Vectorization

Tests: VEC-01 through VEC-19

VEC-01–VEC-09: Vector schema CRUD (algorithms, profiles, quantization)
VEC-10–VEC-19: E2E integrated vectorization (1000-doc upload + kind:text queries)
"""

import random as _random
import time as _time

import pytest
import requests as _http

from conftest import ensure_fresh
from helpers.assertions import assert_field_exists, assert_status

pytestmark = [pytest.mark.vectorization]


def _base_vector_index(name, algorithms, profiles, vectorizers=None, compressions=None,
                        fields_extra=None):
    """Build a minimal vector-enabled index body."""
    fields = [
        {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
        {"name": "content", "type": "Edm.String", "searchable": True},
        {
            "name": "contentVector",
            "type": "Collection(Edm.Single)",
            "searchable": True,
            "dimensions": 1536,
            "vectorSearchProfile": profiles[0]["name"] if profiles else None,
        },
    ]
    if fields_extra:
        fields.extend(fields_extra)

    vs = {"algorithms": algorithms, "profiles": profiles}
    if vectorizers:
        vs["vectorizers"] = vectorizers
    if compressions:
        vs["compressions"] = compressions

    return {"name": name, "fields": fields, "vectorSearch": vs}


# ---------------------------------------------------------------------------
# Algorithm Configurations
# ---------------------------------------------------------------------------


class TestVectorAlgorithms:

    def test_vec_01_hnsw_algorithm(self, rest):
        """VEC-01: Index with HNSW vectorSearch algorithm round-trips."""
        name = "smoke-vec01-hnsw"
        body = _base_vector_index(
            name,
            algorithms=[{
                "name": "hnsw-alg",
                "kind": "hnsw",
                "hnswParameters": {
                    "m": 4, "efConstruction": 400, "efSearch": 500, "metric": "cosine",
                },
            }],
            profiles=[{"name": "hnsw-profile", "algorithm": "hnsw-alg"}],
        )
        ensure_fresh(rest, f"/indexes/{name}")
        resp = rest.put(f"/indexes/{name}", body)
        assert resp.status_code in (200, 201)
        # Verify round-trip
        get_resp = rest.get(f"/indexes/{name}")
        vs = get_resp.json().get("vectorSearch", {})
        algs = vs.get("algorithms", [])
        assert any(a["kind"] == "hnsw" for a in algs), f"HNSW not found: {algs}"

    def test_vec_02_exhaustive_knn(self, rest):
        """VEC-02: Index with exhaustiveKnn algorithm round-trips."""
        name = "smoke-vec02-eknn"
        body = _base_vector_index(
            name,
            algorithms=[{
                "name": "eknn-alg",
                "kind": "exhaustiveKnn",
                "exhaustiveKnnParameters": {"metric": "cosine"},
            }],
            profiles=[{"name": "eknn-profile", "algorithm": "eknn-alg"}],
        )
        ensure_fresh(rest, f"/indexes/{name}")
        resp = rest.put(f"/indexes/{name}", body)
        assert resp.status_code in (200, 201)
        get_resp = rest.get(f"/indexes/{name}")
        algs = get_resp.json().get("vectorSearch", {}).get("algorithms", [])
        assert any(a["kind"] == "exhaustiveKnn" for a in algs)


# ---------------------------------------------------------------------------
# Vectorizers & Profiles
# ---------------------------------------------------------------------------


class TestVectorizersAndProfiles:

    def test_vec_03_aoai_vectorizer(self, rest, aoai_config):
        """VEC-03: Azure OpenAI vectorizer round-trips."""
        name = "smoke-vec03-vectorizer"
        body = _base_vector_index(
            name,
            algorithms=[{
                "name": "hnsw-alg", "kind": "hnsw",
                "hnswParameters": {"m": 4, "efConstruction": 400, "metric": "cosine"},
            }],
            profiles=[{
                "name": "vec-profile",
                "algorithm": "hnsw-alg",
                "vectorizer": "aoai-vectorizer",
            }],
            vectorizers=[{
                "name": "aoai-vectorizer",
                "kind": "azureOpenAI",
                "azureOpenAIParameters": {
                    "resourceUri": aoai_config["endpoint"],
                    "deploymentId": aoai_config["embedding_deployment"],
                    "modelName": aoai_config["embedding_model"],
                    "apiKey": aoai_config["api_key"],
                },
            }],
        )
        ensure_fresh(rest, f"/indexes/{name}")
        resp = rest.put(f"/indexes/{name}", body)
        assert resp.status_code in (200, 201)
        get_resp = rest.get(f"/indexes/{name}")
        vectorizers = get_resp.json().get("vectorSearch", {}).get("vectorizers", [])
        assert any(v["name"] == "aoai-vectorizer" for v in vectorizers)

    def test_vec_04_vector_profile_linked(self, rest, aoai_config):
        """VEC-04: Profile linking algorithm + vectorizer is applied on field."""
        name = "smoke-vec04-profile"
        body = _base_vector_index(
            name,
            algorithms=[{
                "name": "hnsw-alg", "kind": "hnsw",
                "hnswParameters": {"m": 4, "efConstruction": 400, "metric": "cosine"},
            }],
            profiles=[{
                "name": "linked-profile",
                "algorithm": "hnsw-alg",
                "vectorizer": "aoai-vec",
            }],
            vectorizers=[{
                "name": "aoai-vec",
                "kind": "azureOpenAI",
                "azureOpenAIParameters": {
                    "resourceUri": aoai_config["endpoint"],
                    "deploymentId": aoai_config["embedding_deployment"],
                    "modelName": aoai_config["embedding_model"],
                    "apiKey": aoai_config["api_key"],
                },
            }],
        )
        # Override the vector field to use the linked profile
        for f in body["fields"]:
            if f["name"] == "contentVector":
                f["vectorSearchProfile"] = "linked-profile"
        ensure_fresh(rest, f"/indexes/{name}")
        resp = rest.put(f"/indexes/{name}", body)
        assert resp.status_code in (200, 201)
        get_resp = rest.get(f"/indexes/{name}")
        for f in get_resp.json().get("fields", []):
            if f["name"] == "contentVector":
                assert f.get("vectorSearchProfile") == "linked-profile"
                break


# ---------------------------------------------------------------------------
# E2E Chunking + Embedding (creation-only, no blob run)
# ---------------------------------------------------------------------------


class TestVectorE2E:

    def test_vec_05_chunking_embedding_index(self, rest, aoai_config):
        """VEC-05: Full pipeline index: chunking + embedding config present."""
        # This validates the index creation; actual indexer run is in test_09
        name = "smoke-vec05-e2e"
        body = _base_vector_index(
            name,
            algorithms=[{
                "name": "hnsw-alg", "kind": "hnsw",
                "hnswParameters": {"m": 4, "efConstruction": 400, "metric": "cosine"},
            }],
            profiles=[{
                "name": "e2e-profile",
                "algorithm": "hnsw-alg",
                "vectorizer": "aoai-vec",
            }],
            vectorizers=[{
                "name": "aoai-vec",
                "kind": "azureOpenAI",
                "azureOpenAIParameters": {
                    "resourceUri": aoai_config["endpoint"],
                    "deploymentId": aoai_config["embedding_deployment"],
                    "modelName": aoai_config["embedding_model"],
                    "apiKey": aoai_config["api_key"],
                },
            }],
        )
        ensure_fresh(rest, f"/indexes/{name}")
        resp = rest.put(f"/indexes/{name}", body)
        assert resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Quantization / Compression
# ---------------------------------------------------------------------------


class TestVectorCompression:

    def test_vec_06_scalar_quantization(self, rest):
        """VEC-06: Scalar quantization configuration round-trips."""
        name = "smoke-vec06-scalar"
        body = _base_vector_index(
            name,
            algorithms=[{
                "name": "hnsw-alg", "kind": "hnsw",
                "hnswParameters": {"m": 4, "efConstruction": 400, "metric": "cosine"},
            }],
            profiles=[{
                "name": "sq-profile",
                "algorithm": "hnsw-alg",
                "compression": "scalar-quant",
            }],
            compressions=[{
                "name": "scalar-quant",
                "kind": "scalarQuantization",
                "scalarQuantizationParameters": {"quantizedDataType": "int8"},
            }],
        )
        ensure_fresh(rest, f"/indexes/{name}")
        resp = rest.put(f"/indexes/{name}", body)
        assert resp.status_code in (200, 201)
        get_resp = rest.get(f"/indexes/{name}")
        compressions = get_resp.json().get("vectorSearch", {}).get("compressions", [])
        assert any(c["kind"] == "scalarQuantization" for c in compressions), (
            f"Scalar quantization not found: {compressions}"
        )

    def test_vec_07_binary_quantization(self, rest):
        """VEC-07: Binary quantization configuration round-trips."""
        name = "smoke-vec07-binary"
        body = _base_vector_index(
            name,
            algorithms=[{
                "name": "hnsw-alg", "kind": "hnsw",
                "hnswParameters": {"m": 4, "efConstruction": 400, "metric": "cosine"},
            }],
            profiles=[{
                "name": "bq-profile",
                "algorithm": "hnsw-alg",
                "compression": "binary-quant",
            }],
            compressions=[{
                "name": "binary-quant",
                "kind": "binaryQuantization",
            }],
        )
        ensure_fresh(rest, f"/indexes/{name}")
        resp = rest.put(f"/indexes/{name}", body)
        assert resp.status_code in (200, 201)
        get_resp = rest.get(f"/indexes/{name}")
        compressions = get_resp.json().get("vectorSearch", {}).get("compressions", [])
        assert any(c["kind"] == "binaryQuantization" for c in compressions)


# ---------------------------------------------------------------------------
# Vector Field Options
# ---------------------------------------------------------------------------


class TestVectorFieldOptions:

    def test_vec_08_stored_false(self, rest):
        """VEC-08: Vector field with stored:false — not in $select but usable for search."""
        name = "smoke-vec08-stored"
        body = _base_vector_index(
            name,
            algorithms=[{
                "name": "hnsw-alg", "kind": "hnsw",
                "hnswParameters": {"m": 4, "efConstruction": 400, "metric": "cosine"},
            }],
            profiles=[{"name": "p", "algorithm": "hnsw-alg"}],
        )
        # Set stored = false on the vector field
        for f in body["fields"]:
            if f["name"] == "contentVector":
                f["stored"] = False
        ensure_fresh(rest, f"/indexes/{name}")
        resp = rest.put(f"/indexes/{name}", body)
        assert resp.status_code in (200, 201)
        # Verify stored:false round-tripped
        get_resp = rest.get(f"/indexes/{name}")
        for f in get_resp.json().get("fields", []):
            if f["name"] == "contentVector":
                assert f.get("stored") is False, f"Expected stored=false, got {f.get('stored')}"
                break

    def test_vec_09_multiple_vector_profiles(self, rest):
        """VEC-09: Index with 2 profiles on different vector fields."""
        name = "smoke-vec09-multi"
        body = _base_vector_index(
            name,
            algorithms=[
                {"name": "hnsw-a", "kind": "hnsw",
                 "hnswParameters": {"m": 4, "efConstruction": 400, "metric": "cosine"}},
                {"name": "hnsw-b", "kind": "hnsw",
                 "hnswParameters": {"m": 8, "efConstruction": 200, "metric": "dotProduct"}},
            ],
            profiles=[
                {"name": "profile-a", "algorithm": "hnsw-a"},
                {"name": "profile-b", "algorithm": "hnsw-b"},
            ],
            fields_extra=[{
                "name": "titleVector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "dimensions": 1536,
                "vectorSearchProfile": "profile-b",
            }],
        )
        ensure_fresh(rest, f"/indexes/{name}")
        resp = rest.put(f"/indexes/{name}", body)
        assert resp.status_code in (200, 201)
        get_resp = rest.get(f"/indexes/{name}")
        profiles = get_resp.json().get("vectorSearch", {}).get("profiles", [])
        profile_names = [p["name"] for p in profiles]
        assert "profile-a" in profile_names and "profile-b" in profile_names, (
            f"Expected both profiles, got: {profile_names}"
        )


# ==========================================================================
# E2E Integrated Vectorization (VEC-10 through VEC-19)
#
# Creates a 1000-document "tech articles" index with an Azure OpenAI
# vectorizer, computes embeddings via the AOAI API, uploads the documents,
# then exercises query-time integrated vectorization using kind:"text"
# vector queries (text → vector conversion happens server-side).
# ==========================================================================

_E2E_INDEX = "smoke-vec-e2e"

# ── Synthetic data: 10 categories × 10 topic sentences ──────────────────────

_TECH_TOPICS = {
    "AI": [
        "Deep learning neural networks revolutionize computer vision with convolutional architectures for image recognition",
        "Natural language processing using transformer models enables accurate text understanding and generation",
        "Reinforcement learning algorithms train agents for complex decision-making in dynamic environments",
        "Generative adversarial networks produce realistic synthetic images for data augmentation and creative applications",
        "Machine learning pipelines automate feature engineering model training and hyperparameter optimization",
        "Transfer learning leverages pre-trained foundation models to accelerate domain-specific AI development",
        "Federated learning enables collaborative model training across distributed devices while preserving data privacy",
        "Responsible AI frameworks ensure fairness transparency and accountability in automated decision systems",
        "Anomaly detection models identify unusual patterns in time series data for fraud prevention and monitoring",
        "Knowledge graphs combine structured data with AI reasoning for intelligent search and recommendation systems",
    ],
    "Cloud": [
        "Kubernetes orchestration manages containerized microservices with automated scaling and self-healing capabilities",
        "Serverless computing eliminates infrastructure management allowing developers to focus on business logic",
        "Multi-cloud strategies distribute workloads across providers for resilience and cost optimization",
        "Infrastructure as code tools like Terraform and Bicep enable repeatable cloud environment deployments",
        "Cloud-native design patterns include circuit breakers service mesh and event-driven architectures",
        "Container registries store and distribute Docker images for consistent application deployment across environments",
        "Cloud cost optimization involves right-sizing instances reserved capacity and spot instance workloads",
        "Service mesh technologies provide observability traffic management and security for distributed microservices",
        "Cloud migration strategies include lift-and-shift replatforming and complete application refactoring approaches",
        "Edge computing extends cloud capabilities to distributed locations for ultra low-latency data processing",
    ],
    "Security": [
        "Zero trust architecture requires continuous verification of every user device and network connection",
        "Encryption protocols protect sensitive data in transit and at rest using modern cryptographic algorithms",
        "Identity and access management controls who can access resources through authentication and authorization policies",
        "Penetration testing simulates real-world attacks to uncover vulnerabilities before malicious actors exploit them",
        "Security information and event management aggregates logs for real-time threat detection and incident response",
        "Container security scanning identifies vulnerabilities in Docker images before they reach production environments",
        "API security best practices include rate limiting input validation OAuth tokens and mutual TLS authentication",
        "Cloud security posture management continuously monitors infrastructure for compliance and misconfiguration risks",
        "Data loss prevention tools detect and block unauthorized transmission of sensitive information across networks",
        "Ransomware protection strategies combine endpoint detection backups network segmentation and user training",
    ],
    "DevOps": [
        "Continuous integration and continuous deployment pipelines automate code testing building and release processes",
        "GitOps workflows use Git repositories as the single source of truth for infrastructure and application state",
        "Monitoring and observability platforms collect metrics logs and traces for comprehensive system visibility",
        "Site reliability engineering practices balance feature velocity with service availability and error budgets",
        "Infrastructure automation with Ansible Chef and Puppet ensures consistent server configuration management",
        "Blue-green and canary deployment strategies minimize downtime and risk during application version releases",
        "Chaos engineering deliberately injects failures into systems to verify resilience and disaster recovery capabilities",
        "Developer experience platforms streamline onboarding tooling and inner loop development productivity",
        "Artifact management systems store versioned build outputs containers and packages for reproducible deployments",
        "Platform engineering teams build internal developer portals and self-service infrastructure provisioning tools",
    ],
    "Database": [
        "Relational database optimization techniques include query tuning indexing strategies and execution plan analysis",
        "NoSQL databases provide flexible schema designs for document graph key-value and wide-column data models",
        "Database replication and sharding distribute data across nodes for horizontal scaling and high availability",
        "Time series databases efficiently store and query timestamped data for IoT metrics and financial analytics",
        "Graph databases model complex relationships between entities enabling traversal queries and pattern detection",
        "Database migration tools automate schema changes version tracking and rollback procedures across environments",
        "In-memory caching layers like Redis and Memcached accelerate read-heavy workloads and reduce database load",
        "Vector databases enable similarity search over high-dimensional embeddings for AI-powered applications",
        "Database backup and disaster recovery procedures ensure business continuity with point-in-time restore capabilities",
        "Distributed SQL databases combine ACID transactions with horizontal scalability across multiple geographic regions",
    ],
    "Networking": [
        "Software-defined networking decouples control and data planes for programmable network infrastructure management",
        "Content delivery networks cache static assets at edge locations to minimize latency for global users",
        "Network load balancers distribute incoming traffic across backend servers for high availability and throughput",
        "Virtual private networks create encrypted tunnels for secure remote access to corporate network resources",
        "DNS configuration and management ensures reliable domain name resolution with failover and geographic routing",
        "Network security groups and firewalls filter traffic based on IP address port and protocol rule sets",
        "IPv6 adoption provides expanded address space and improved routing efficiency for modern internet connectivity",
        "Network performance monitoring tools measure bandwidth latency packet loss and jitter across infrastructure",
        "Hybrid connectivity solutions bridge on-premises data centers with cloud virtual networks using VPN or ExpressRoute",
        "API gateway services provide centralized routing authentication rate limiting and protocol translation for APIs",
    ],
    "Frontend": [
        "React component architecture enables reusable declarative user interface development with virtual DOM rendering",
        "Progressive web applications combine native app capabilities with web accessibility and offline support features",
        "CSS grid and flexbox layout systems create responsive designs that adapt to different screen sizes and devices",
        "Web accessibility standards ensure inclusive design for users with visual auditory motor and cognitive disabilities",
        "Frontend performance optimization includes code splitting lazy loading image compression and caching strategies",
        "TypeScript adds static type checking to JavaScript improving code quality and developer tooling support",
        "State management libraries coordinate application data flow across complex single page application components",
        "Design system libraries provide consistent reusable UI components tokens and patterns across products and teams",
        "Server-side rendering and static site generation improve initial load performance and search engine optimization",
        "Web animation frameworks create smooth performant motion design for interactive user experience enhancement",
    ],
    "Backend": [
        "REST API design principles include resource-based URLs proper HTTP methods status codes and pagination patterns",
        "GraphQL APIs provide flexible query execution allowing clients to request exactly the data fields they need",
        "Message queue systems decouple producers and consumers enabling asynchronous event-driven processing architectures",
        "Microservice communication patterns include synchronous REST calls asynchronous messaging and event sourcing",
        "Authentication middleware validates JSON web tokens OAuth scopes and session cookies for secured API endpoints",
        "Rate limiting and throttling protect backend services from abuse and ensure fair resource allocation among clients",
        "Background job processing systems handle long-running tasks email sending report generation and data pipelines",
        "API versioning strategies maintain backward compatibility while introducing new features and deprecating old endpoints",
        "Connection pooling and database session management optimize backend resource utilization under concurrent load",
        "Distributed tracing correlates requests across microservice boundaries for end-to-end latency and error analysis",
    ],
    "Mobile": [
        "Cross-platform mobile frameworks build native iOS and Android applications from a single shared codebase",
        "Mobile app performance profiling identifies memory leaks CPU bottlenecks and battery drain in real devices",
        "Push notification services deliver timely messages to mobile users through platform-specific delivery channels",
        "Offline-first mobile architecture synchronizes local data stores with cloud backends when connectivity resumes",
        "Mobile CI/CD pipelines automate building testing signing and distributing apps to testers and app stores",
        "Mobile analytics platforms track user engagement session metrics crash reports and conversion funnel events",
        "Responsive mobile design adapts layouts typography and touch targets for varying screen sizes and orientations",
        "Mobile security includes certificate pinning biometric authentication secure storage and transport encryption",
        "Augmented reality SDKs overlay digital content on camera feeds for immersive mobile entertainment and commerce",
        "Mobile backend services provide authentication data storage file hosting and serverless functions for mobile apps",
    ],
    "IoT": [
        "IoT device management platforms handle provisioning firmware updates monitoring and lifecycle for connected devices",
        "Edge computing gateways preprocess sensor data locally before transmitting summarized results to cloud analytics",
        "Industrial IoT protocols like MQTT OPC-UA and AMQP enable reliable machine-to-machine communication",
        "IoT security challenges include device authentication firmware integrity secure boot and encrypted communication",
        "Digital twin models create virtual replicas of physical assets for simulation monitoring and predictive maintenance",
        "Smart home automation systems coordinate lighting HVAC security cameras and appliances through centralized hubs",
        "Wearable health devices collect biometric signals including heart rate blood oxygen steps and sleep patterns",
        "Agricultural IoT sensors monitor soil moisture temperature humidity and crop health for precision farming decisions",
        "Fleet management IoT solutions track vehicle location fuel consumption driver behavior and maintenance schedules",
        "IoT data pipelines ingest millions of telemetry events per second for real-time streaming analytics and alerting",
    ],
}

_VARIATION_TEMPLATES = [
    "{topic}",
    "An introduction to {topic}",
    "Advanced concepts in {topic}",
    "Best practices for {topic}",
    "A practical guide covering {topic}",
    "Understanding the fundamentals of {topic}",
    "Modern approaches to {topic}",
    "Enterprise patterns for {topic}",
    "Scaling strategies related to {topic}",
    "Performance considerations in {topic}",
]

_AUTHORS = [
    "Alice Chen", "Bob Kumar", "Carol Martinez", "David Park", "Eve Thompson",
    "Frank Wilson", "Grace Lee", "Henry Brown", "Iris Zhang", "James Davis",
]

_TAG_POOL = {
    "AI": ["machine-learning", "deep-learning", "neural-networks", "nlp", "computer-vision"],
    "Cloud": ["kubernetes", "serverless", "containers", "microservices", "iaas"],
    "Security": ["encryption", "zero-trust", "identity", "compliance", "threat-detection"],
    "DevOps": ["ci-cd", "gitops", "monitoring", "automation", "sre"],
    "Database": ["sql", "nosql", "replication", "indexing", "caching"],
    "Networking": ["load-balancing", "cdn", "dns", "firewall", "vpn"],
    "Frontend": ["react", "typescript", "css", "accessibility", "pwa"],
    "Backend": ["rest-api", "graphql", "messaging", "authentication", "microservices"],
    "Mobile": ["cross-platform", "offline-first", "push-notifications", "analytics", "ci-cd"],
    "IoT": ["edge-computing", "mqtt", "digital-twin", "sensor-data", "device-management"],
}

_RNG = _random.Random(42)


def _generate_articles():
    """Generate 1000 synthetic tech article documents (10 categories × 10 topics × 10 variations)."""
    articles = []
    doc_id = 0
    for cat, topics in _TECH_TOPICS.items():
        for topic in topics:
            for template in _VARIATION_TEMPLATES:
                doc_id += 1
                content = template.format(topic=topic)
                articles.append({
                    "id": f"art-{doc_id:04d}",
                    "title": content[:100],
                    "content": content,
                    "category": cat,
                    "author": _AUTHORS[(doc_id - 1) % len(_AUTHORS)],
                    "publishDate": f"2024-{((doc_id - 1) % 12) + 1:02d}-{((doc_id - 1) % 28) + 1:02d}T00:00:00Z",
                    "rating": round(3.0 + ((doc_id * 7) % 20) * 0.1, 1),
                    "tags": _RNG.sample(_TAG_POOL[cat], 3),
                })
    return articles


def _embed_texts(texts, aoai_config, batch_size=200):
    """Call Azure OpenAI embedding API in batches.  Returns list[list[float]]."""
    endpoint = aoai_config["endpoint"].rstrip("/")
    deployment = aoai_config["embedding_deployment"]
    url = f"{endpoint}/openai/deployments/{deployment}/embeddings?api-version={aoai_config['api_version']}"
    headers = {"api-key": aoai_config["api_key"], "Content-Type": "application/json"}

    all_embeddings: list = [None] * len(texts)
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        last_err = None
        for attempt in range(6):
            try:
                resp = _http.post(url, json={"input": batch}, headers=headers, timeout=120)
            except _http.exceptions.RequestException as exc:
                last_err = exc
                _time.sleep(2 ** attempt)
                continue
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 2 ** attempt))
                _time.sleep(wait)
                continue
            if resp.status_code >= 500:
                _time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            for item in resp.json()["data"]:
                all_embeddings[start + item["index"]] = item["embedding"]
            last_err = None
            break
        else:
            raise RuntimeError(
                f"AOAI embedding failed for batch at index {start} after 6 retries: {last_err}"
            )
    return all_embeddings


def _wait_for_count(rest, index_name, expected, timeout=60):
    """Poll document count until it reaches *expected* (or timeout)."""
    deadline = _time.time() + timeout
    count = 0
    while _time.time() < deadline:
        try:
            resp = rest.get(f"/indexes/{index_name}/docs/$count")
            if resp.status_code == 200:
                count = int(resp.text.strip())
                if count >= expected:
                    return count
        except Exception:
            pass
        _time.sleep(3)
    return count


# ── E2E test class ───────────────────────────────────────────────────────────


class TestIntegratedVectorizationE2E:
    """E2E integrated vectorization: vectorizer-enabled index, 1000 docs, kind:text queries."""

    def test_vec_10_create_vectorizer_index(self, rest, aoai_config):
        """VEC-10: Create index with AOAI vectorizer for integrated vectorization."""
        body = {
            "name": _E2E_INDEX,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
                {"name": "title", "type": "Edm.String", "searchable": True, "retrievable": True},
                {"name": "content", "type": "Edm.String", "searchable": True, "retrievable": True},
                {
                    "name": "category", "type": "Edm.String",
                    "filterable": True, "facetable": True, "searchable": True, "retrievable": True,
                },
                {"name": "author", "type": "Edm.String", "filterable": True, "retrievable": True},
                {
                    "name": "publishDate", "type": "Edm.DateTimeOffset",
                    "filterable": True, "sortable": True, "retrievable": True,
                },
                {
                    "name": "rating", "type": "Edm.Double",
                    "filterable": True, "sortable": True, "facetable": True, "retrievable": True,
                },
                {"name": "tags", "type": "Collection(Edm.String)", "filterable": True, "retrievable": True},
                {
                    "name": "contentVector",
                    "type": "Collection(Edm.Single)",
                    "searchable": True,
                    "retrievable": False,
                    "dimensions": aoai_config["embedding_dimensions"],
                    "vectorSearchProfile": "e2e-vector-profile",
                },
            ],
            "vectorSearch": {
                "algorithms": [{
                    "name": "e2e-hnsw",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "m": 4, "efConstruction": 400, "efSearch": 500, "metric": "cosine",
                    },
                }],
                "vectorizers": [{
                    "name": "e2e-aoai-vectorizer",
                    "kind": "azureOpenAI",
                    "azureOpenAIParameters": {
                        "resourceUri": aoai_config["endpoint"],
                        "deploymentId": aoai_config["embedding_deployment"],
                        "modelName": aoai_config["embedding_model"],
                        "apiKey": aoai_config["api_key"],
                    },
                }],
                "profiles": [{
                    "name": "e2e-vector-profile",
                    "algorithm": "e2e-hnsw",
                    "vectorizer": "e2e-aoai-vectorizer",
                }],
            },
        }
        # Clean up any prior run
        ensure_fresh(rest, f"/indexes/{_E2E_INDEX}")

        resp = rest.put(f"/indexes/{_E2E_INDEX}", body)
        assert resp.status_code in (200, 201), (
            f"Create index failed: {resp.status_code} {resp.text[:500]}"
        )

        # Verify vectorizer round-trips
        get_resp = rest.get(f"/indexes/{_E2E_INDEX}")
        assert get_resp.status_code == 200
        vs = get_resp.json().get("vectorSearch", {})
        vectorizers = vs.get("vectorizers", [])
        assert any(v["name"] == "e2e-aoai-vectorizer" for v in vectorizers), (
            f"Vectorizer not found in index: {vectorizers}"
        )
        profiles = vs.get("profiles", [])
        assert any(p.get("vectorizer") == "e2e-aoai-vectorizer" for p in profiles), (
            f"Profile not linked to vectorizer: {profiles}"
        )

    def test_vec_11_upload_1000_documents(self, rest, aoai_config):
        """VEC-11: Embed and upload 1000 tech articles for vectorizer queries."""
        articles = _generate_articles()
        assert len(articles) == 1000, f"Expected 1000 articles, got {len(articles)}"

        # Compute embeddings via Azure OpenAI
        texts = [a["content"] for a in articles]
        embeddings = _embed_texts(texts, aoai_config, batch_size=200)
        assert all(e is not None for e in embeddings), "Some embeddings were not computed"

        # Attach vectors and upload in batches of 100
        for i, article in enumerate(articles):
            article["contentVector"] = embeddings[i]
            article["@search.action"] = "upload"

        batch_size = 100
        for start in range(0, len(articles), batch_size):
            batch = articles[start : start + batch_size]
            resp = rest.post(f"/indexes/{_E2E_INDEX}/docs/index", {"value": batch})
            assert resp.status_code in (200, 207), (
                f"Upload batch at {start} failed: {resp.status_code} {resp.text[:500]}"
            )

        # Wait for all documents to be indexed
        count = _wait_for_count(rest, _E2E_INDEX, expected=1000, timeout=60)
        assert count >= 1000, f"Expected >= 1000 docs, got {count}"

    def test_vec_12_text_to_vector_query(self, rest):
        """VEC-12: Query with kind:text — server-side vectorization via AOAI vectorizer."""
        body = {
            "count": True,
            "top": 10,
            "select": "id, title, category, rating",
            "vectorQueries": [{
                "kind": "text",
                "text": "machine learning and neural network algorithms for artificial intelligence",
                "fields": "contentVector",
                "k": 10,
            }],
        }
        resp = rest.post(f"/indexes/{_E2E_INDEX}/docs/search", body)
        assert resp.status_code == 200, f"Text vector query failed: {resp.status_code}"
        results = resp.json()
        values = results.get("value", [])
        assert len(values) > 0, "Expected results from text vector query"
        # Every result should have a search score
        assert all(v.get("@search.score") is not None for v in values)
        # AI-related results should appear (semantic relevance check)
        categories = [v["category"] for v in values]
        assert "AI" in categories, f"Expected AI in top results, got: {categories}"

    def test_vec_13_hybrid_text_vector_query(self, rest):
        """VEC-13: Hybrid search combining keyword + kind:text vectorizer query."""
        body = {
            "search": "kubernetes container orchestration",
            "searchFields": "title,content",
            "count": True,
            "top": 10,
            "select": "id, title, category",
            "vectorQueries": [{
                "kind": "text",
                "text": "container orchestration and cloud native deployment patterns",
                "fields": "contentVector",
                "k": 10,
            }],
        }
        resp = rest.post(f"/indexes/{_E2E_INDEX}/docs/search", body)
        assert resp.status_code == 200, f"Hybrid query failed: {resp.status_code}"
        values = resp.json().get("value", [])
        assert len(values) > 0, "Expected results from hybrid query"
        # Cloud category should appear in results
        categories = [v["category"] for v in values]
        assert "Cloud" in categories, f"Expected Cloud in hybrid results, got: {categories}"

    def test_vec_14_filtered_vector_text_query(self, rest):
        """VEC-14: Vector kind:text query with $filter on category."""
        body = {
            "count": True,
            "top": 10,
            "filter": "category eq 'Security'",
            "select": "id, title, category",
            "vectorQueries": [{
                "kind": "text",
                "text": "encryption and network security threat detection protocols",
                "fields": "contentVector",
                "k": 50,
            }],
        }
        resp = rest.post(f"/indexes/{_E2E_INDEX}/docs/search", body)
        assert resp.status_code == 200, f"Filtered vector query failed: {resp.status_code}"
        values = resp.json().get("value", [])
        assert len(values) > 0, "Expected Security results"
        for v in values:
            assert v["category"] == "Security", (
                f"Filter violation: got category '{v['category']}', expected 'Security'"
            )

    def test_vec_15_vector_query_select_fields(self, rest):
        """VEC-15: Vector kind:text query with $select restricts returned fields."""
        body = {
            "top": 5,
            "select": "id, category",
            "vectorQueries": [{
                "kind": "text",
                "text": "database query optimization and indexing strategies",
                "fields": "contentVector",
                "k": 5,
            }],
        }
        resp = rest.post(f"/indexes/{_E2E_INDEX}/docs/search", body)
        assert resp.status_code == 200
        values = resp.json().get("value", [])
        assert len(values) > 0
        for v in values:
            assert "id" in v, "id should be in select"
            assert "category" in v, "category should be in select"
            assert "title" not in v, "title should not be returned when not in $select"
            assert "content" not in v, "content should not be returned when not in $select"

    def test_vec_16_vector_query_pagination(self, rest):
        """VEC-16: Vector kind:text query with top/skip pagination — no overlap."""
        base = {
            "select": "id, title",
            "vectorQueries": [{
                "kind": "text",
                "text": "cloud computing infrastructure and deployment",
                "fields": "contentVector",
                "k": 50,
            }],
        }
        resp1 = rest.post(f"/indexes/{_E2E_INDEX}/docs/search", {**base, "top": 5, "skip": 0})
        assert resp1.status_code == 200
        page1_ids = {v["id"] for v in resp1.json().get("value", [])}

        resp2 = rest.post(f"/indexes/{_E2E_INDEX}/docs/search", {**base, "top": 5, "skip": 5})
        assert resp2.status_code == 200
        page2_ids = {v["id"] for v in resp2.json().get("value", [])}

        assert len(page1_ids) == 5, f"Page 1 should have 5 results, got {len(page1_ids)}"
        assert len(page2_ids) == 5, f"Page 2 should have 5 results, got {len(page2_ids)}"
        assert page1_ids.isdisjoint(page2_ids), (
            f"Pages should not overlap: {page1_ids & page2_ids}"
        )

    def test_vec_17_multi_text_vector_queries(self, rest):
        """VEC-17: Multiple vectorQueries with kind:text targeting same field."""
        body = {
            "count": True,
            "top": 10,
            "select": "id, title, category",
            "vectorQueries": [
                {
                    "kind": "text",
                    "text": "machine learning model training deep learning",
                    "fields": "contentVector",
                    "k": 10,
                },
                {
                    "kind": "text",
                    "text": "IoT sensor telemetry edge computing",
                    "fields": "contentVector",
                    "k": 10,
                },
            ],
        }
        resp = rest.post(f"/indexes/{_E2E_INDEX}/docs/search", body)
        assert resp.status_code == 200, f"Multi-vector query failed: {resp.status_code}"
        values = resp.json().get("value", [])
        assert len(values) > 0, "Expected results from multi-vector query"
        # Two semantically different queries should bring diverse categories
        categories = {v["category"] for v in values}
        assert len(categories) >= 2, (
            f"Expected at least 2 categories from diverse queries, got: {categories}"
        )

    def test_vec_18_quantization_with_vectorizer(self, rest, aoai_config):
        """VEC-18: Scalar quantization + AOAI vectorizer on same profile — query works."""
        name = "smoke-vec18-quant-vec"
        body = {
            "name": name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
                {"name": "content", "type": "Edm.String", "searchable": True, "retrievable": True},
                {
                    "name": "contentVector",
                    "type": "Collection(Edm.Single)",
                    "searchable": True,
                    "retrievable": False,
                    "dimensions": aoai_config["embedding_dimensions"],
                    "vectorSearchProfile": "quant-vec-profile",
                },
            ],
            "vectorSearch": {
                "algorithms": [{
                    "name": "hnsw-alg", "kind": "hnsw",
                    "hnswParameters": {"m": 4, "efConstruction": 400, "metric": "cosine"},
                }],
                "vectorizers": [{
                    "name": "aoai-vec",
                    "kind": "azureOpenAI",
                    "azureOpenAIParameters": {
                        "resourceUri": aoai_config["endpoint"],
                        "deploymentId": aoai_config["embedding_deployment"],
                        "modelName": aoai_config["embedding_model"],
                        "apiKey": aoai_config["api_key"],
                    },
                }],
                "compressions": [{
                    "name": "sq8",
                    "kind": "scalarQuantization",
                    "scalarQuantizationParameters": {"quantizedDataType": "int8"},
                }],
                "profiles": [{
                    "name": "quant-vec-profile",
                    "algorithm": "hnsw-alg",
                    "vectorizer": "aoai-vec",
                    "compression": "sq8",
                }],
            },
        }
        ensure_fresh(rest, f"/indexes/{name}")

        resp = rest.put(f"/indexes/{name}", body)
        assert resp.status_code in (200, 201), (
            f"Create quantized vectorizer index failed: {resp.status_code} {resp.text[:500]}"
        )

        # Upload a small batch with pre-computed vectors
        sample_texts = [
            "Deep learning for image classification using neural networks",
            "Cloud computing with Kubernetes container orchestration at scale",
            "Database optimization and query tuning with execution plan analysis",
            "Network security encryption and zero trust architecture patterns",
            "Mobile application development with cross-platform frameworks",
        ]
        embeddings = _embed_texts(sample_texts, aoai_config, batch_size=10)
        docs = [
            {
                "@search.action": "upload",
                "id": f"qv-{i}",
                "content": sample_texts[i],
                "contentVector": embeddings[i],
            }
            for i in range(len(sample_texts))
        ]
        upload_resp = rest.post(f"/indexes/{name}/docs/index", {"value": docs})
        assert upload_resp.status_code in (200, 207)
        _wait_for_count(rest, name, expected=len(docs), timeout=30)

        # Query with kind:text through quantized + vectorizer profile
        search_body = {
            "count": True,
            "top": 3,
            "select": "id, content",
            "vectorQueries": [{
                "kind": "text",
                "text": "neural networks and deep learning for AI",
                "fields": "contentVector",
                "k": 3,
            }],
        }
        search_resp = rest.post(f"/indexes/{name}/docs/search", search_body)
        assert search_resp.status_code == 200, (
            f"Quantized vectorizer query failed: {search_resp.status_code}"
        )
        values = search_resp.json().get("value", [])
        assert len(values) > 0, "Expected results from quantized vectorizer query"

    def test_vec_19_verify_e2e_index_populated(self, rest):
        """VEC-19: Verify the E2E vectorization index is populated (cleanup deferred to Phase 18)."""
        resp = rest.get(f"/indexes/{_E2E_INDEX}")
        assert resp.status_code == 200, (
            f"E2E index should exist after Phase 11, got {resp.status_code}"
        )
        count_resp = rest.get(f"/indexes/{_E2E_INDEX}/docs/$count")
        assert count_resp.status_code == 200, (
            f"E2E index doc count check failed: {count_resp.status_code}"
        )
        count = int(count_resp.text.strip())
        assert count >= 100, (
            f"E2E index should have >= 100 docs, got {count}"
        )
