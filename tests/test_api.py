"""SM Data Exchange 领域测试：连接器、交换任务、运行记录与统计。"""

import pytest
from fastapi.testclient import TestClient

from app import base
from app.main import VERSION, app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(base, "internal_api_key", lambda: "TEST")
    base.reset_state()
    from app.main import _init as init_db
    init_db()
    with TestClient(app) as c:
        c.headers["X-Internal-Token"] = "TEST"
        yield c


def _connectors(client):
    src = client.post("/api/exchange/connectors", json={"name": "pg-prod", "connector_type": "database", "endpoint": "postgres://prod"}).json()["id"]
    dst = client.post("/api/exchange/connectors", json={"name": "dw", "connector_type": "database", "endpoint": "postgres://dw"}).json()["id"]
    return src, dst


def test_health_and_version(client):
    r = client.get("/health", headers={"X-Request-Id": "suite-test"})
    assert r.status_code == 200
    assert r.json()["version"] == VERSION


def test_connector_lifecycle(client):
    assert client.post("/api/exchange/connectors", json={"name": "api-src", "connector_type": "api", "endpoint": "https://api.example.com"}).status_code == 201
    assert client.post("/api/exchange/connectors", json={"name": "api-src", "connector_type": "api", "endpoint": "https://api.example.com"}).status_code == 409
    assert client.get("/api/exchange/connectors").json()["total"] == 1


def test_job_and_run(client):
    src, dst = _connectors(client)
    job = client.post("/api/exchange/jobs", json={"name": "sync-orders", "source_id": src, "target_id": dst, "mapping": {"order": "order"}})
    assert job.status_code == 201
    job_id = job.json()["id"]
    run = client.post(f"/api/exchange/jobs/{job_id}/run").json()
    assert run["status"] == "success"
    assert run["rows_written"] > 0
    assert client.get(f"/api/exchange/jobs/{job_id}/runs").json()["total"] == 1
    assert client.get(f"/api/exchange/runs/{run['id']}").json()["rows_written"] == run["rows_written"]


def test_job_requires_valid_connectors(client):
    assert client.post("/api/exchange/jobs", json={"name": "bad", "source_id": "no-such-conn", "target_id": "no-such-conn"}).status_code == 404


def test_missing_job(client):
    assert client.post("/api/exchange/jobs/nope/run").status_code == 404
    assert client.get("/api/exchange/runs/nope").status_code == 404


def test_stats(client):
    src, dst = _connectors(client)
    job_id = client.post("/api/exchange/jobs", json={"name": "sync-1", "source_id": src, "target_id": dst}).json()["id"]
    client.post(f"/api/exchange/jobs/{job_id}/run")
    stats = client.get("/api/exchange/stats").json()
    assert stats["jobs"] == 1
    assert stats["success_runs"] == 1
    assert stats["total_rows_written"] > 0


def test_manifest_and_crypto(client):
    assert client.get("/api/integration/manifest").json()["version"] == VERSION
    enc = client.post("/api/crypto/encrypt", json={"value": "x"}).json()["ciphertext"]
    assert client.post("/api/crypto/decrypt", json={"value": enc}).json()["plaintext"] == "x"


def test_write_requires_auth(client):
    del client.headers["X-Internal-Token"]
    assert client.post("/api/exchange/connectors", json={"name": "c", "connector_type": "api", "endpoint": "x"}).status_code == 401
