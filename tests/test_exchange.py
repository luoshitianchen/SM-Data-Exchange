"""SM-Data-Exchange 业务深化测试：伙伴/协议/交换任务全生命周期。"""
from __future__ import annotations

import pytest

H = {"X-Internal-Token": "test-internal-key-12345"}


async def _create_partner(client, code: str, name: str = "测试伙伴") -> dict:
    resp = await client.post("/api/exchange/partners", json={
        "code": code, "name": name, "partner_type": "supplier",
        "endpoint": f"https://{code.lower()}.example.com", "auth_type": "token",
    }, headers=H)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_protocol(client, code: str, partner_id: str | None = None) -> dict:
    payload = {
        "code": code, "name": f"协议-{code}", "protocol_type": "sftp",
        "config": {"host": "sftp.example.com", "port": 22},
    }
    if partner_id:
        payload["partner_id"] = partner_id
    resp = await client.post("/api/exchange/protocols", json=payload, headers=H)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_task(client, code: str, partner_id: str, protocol_id: str) -> dict:
    resp = await client.post("/api/exchange/tasks", json={
        "code": code, "name": f"任务-{code}", "partner_id": partner_id,
        "protocol_id": protocol_id, "direction": "import", "schedule_cron": "0 2 * * *",
    }, headers=H)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ═══════════════════════════════════════════════════════════
# 交换伙伴
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_partner_success(client):
    data = await _create_partner(client, "EXT-P-A01", "供应商A")
    assert data["code"] == "EXT-P-A01"
    assert data["status"] == "active"
    assert data["partner_type"] == "supplier"


@pytest.mark.asyncio
async def test_create_partner_requires_token(client):
    resp = await client.post("/api/exchange/partners", json={
        "code": "EXT-P-NOAUTH", "name": "无令牌",
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_partner_duplicate_code(client):
    await _create_partner(client, "EXT-P-DUP")
    resp = await client.post("/api/exchange/partners", json={
        "code": "EXT-P-DUP", "name": "重复",
    }, headers=H)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_partners_filter_and_keyword(client):
    await _create_partner(client, "EXT-P-FILT", "关键词伙伴")
    resp = await client.get("/api/exchange/partners?keyword=EXT-P-FILT", headers=H)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(p["code"] == "EXT-P-FILT" for p in body["items"])
    # 状态过滤
    resp2 = await client.get("/api/exchange/partners?status=active", headers=H)
    assert resp2.status_code == 200
    assert all(p["status"] == "active" for p in resp2.json()["items"])


@pytest.mark.asyncio
async def test_get_partner_not_found(client):
    resp = await client.get("/api/exchange/partners/no-such-id", headers=H)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_partner(client):
    p = await _create_partner(client, "EXT-P-UPD")
    resp = await client.patch(f"/api/exchange/partners/{p['id']}", json={
        "name": "更新后伙伴", "endpoint": "https://new.example.com",
    }, headers=H)
    assert resp.status_code == 200
    assert resp.json()["name"] == "更新后伙伴"


@pytest.mark.asyncio
async def test_update_partner_status_disable(client):
    p = await _create_partner(client, "EXT-P-DIS")
    resp = await client.patch(f"/api/exchange/partners/{p['id']}/status", json={
        "status": "disabled",
    }, headers=H)
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"


@pytest.mark.asyncio
async def test_delete_partner_not_found(client):
    resp = await client.delete("/api/exchange/partners/no-such-id", headers=H)
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════
# 交换协议
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_protocol_success(client):
    partner = await _create_partner(client, "EXT-P-PROT")
    data = await _create_protocol(client, "PROTO-P01", partner["id"])
    assert data["code"] == "PROTO-P01"
    assert data["protocol_type"] == "sftp"
    assert data["config"]["host"] == "sftp.example.com"
    assert data["partner_id"] == partner["id"]


@pytest.mark.asyncio
async def test_create_protocol_duplicate_code(client):
    await _create_protocol(client, "PROTO-DUP")
    resp = await client.post("/api/exchange/protocols", json={
        "code": "PROTO-DUP", "name": "重复",
    }, headers=H)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_protocol_partner_not_found(client):
    resp = await client.post("/api/exchange/protocols", json={
        "code": "PROTO-BADREF", "name": "坏引用", "partner_id": "no-such-partner",
    }, headers=H)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_protocols_keyword(client):
    await _create_protocol(client, "PROTO-FIND")
    resp = await client.get("/api/exchange/protocols?keyword=PROTO-FIND", headers=H)
    assert resp.status_code == 200
    assert any(p["code"] == "PROTO-FIND" for p in resp.json()["items"])


@pytest.mark.asyncio
async def test_update_protocol(client):
    proto = await _create_protocol(client, "PROTO-UPD")
    resp = await client.patch(f"/api/exchange/protocols/{proto['id']}", json={
        "config": {"host": "new.sftp", "port": 2222},
    }, headers=H)
    assert resp.status_code == 200
    assert resp.json()["config"]["port"] == 2222


@pytest.mark.asyncio
async def test_update_protocol_status(client):
    proto = await _create_protocol(client, "PROTO-DIS")
    resp = await client.patch(f"/api/exchange/protocols/{proto['id']}/status", json={
        "status": "disabled",
    }, headers=H)
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"


# ═══════════════════════════════════════════════════════════
# 交换任务与状态机
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_task_success(client):
    partner = await _create_partner(client, "EXT-P-T01")
    proto = await _create_protocol(client, "PROTO-T01", partner["id"])
    task = await _create_task(client, "TASK-T01", partner["id"], proto["id"])
    assert task["status"] == "draft"
    assert task["direction"] == "import"


@pytest.mark.asyncio
async def test_create_task_duplicate_code(client):
    partner = await _create_partner(client, "EXT-P-DUPT")
    proto = await _create_protocol(client, "PROTO-DUPT", partner["id"])
    await _create_task(client, "TASK-DUP", partner["id"], proto["id"])
    resp = await client.post("/api/exchange/tasks", json={
        "code": "TASK-DUP", "name": "重复", "partner_id": partner["id"],
        "protocol_id": proto["id"],
    }, headers=H)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_task_partner_not_found(client):
    proto = await _create_protocol(client, "PROTO-BADP")
    resp = await client.post("/api/exchange/tasks", json={
        "code": "TASK-BADP", "name": "坏伙伴", "partner_id": "no-partner",
        "protocol_id": proto["id"],
    }, headers=H)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_task_protocol_not_found(client):
    partner = await _create_partner(client, "EXT-P-BADPR")
    resp = await client.post("/api/exchange/tasks", json={
        "code": "TASK-BADPR", "name": "坏协议", "partner_id": partner["id"],
        "protocol_id": "no-proto",
    }, headers=H)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_task_state_machine_happy_path(client):
    partner = await _create_partner(client, "EXT-P-SM")
    proto = await _create_protocol(client, "PROTO-SM", partner["id"])
    task = await _create_task(client, "TASK-SM", partner["id"], proto["id"])
    tid = task["id"]

    # draft -> running
    r1 = await client.patch(f"/api/exchange/tasks/{tid}/status", json={"status": "running"}, headers=H)
    assert r1.status_code == 200 and r1.json()["status"] == "running"
    # running -> paused
    r2 = await client.patch(f"/api/exchange/tasks/{tid}/status", json={"status": "paused"}, headers=H)
    assert r2.json()["status"] == "paused"
    # paused -> running
    r3 = await client.patch(f"/api/exchange/tasks/{tid}/status", json={"status": "running"}, headers=H)
    assert r3.json()["status"] == "running"
    # running -> completed
    r4 = await client.patch(f"/api/exchange/tasks/{tid}/status", json={"status": "completed"}, headers=H)
    assert r4.status_code == 200 and r4.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_task_invalid_transition(client):
    partner = await _create_partner(client, "EXT-P-BADT")
    proto = await _create_protocol(client, "PROTO-BADT", partner["id"])
    task = await _create_task(client, "TASK-BADT", partner["id"], proto["id"])
    # draft 不能直接 -> completed
    resp = await client.patch(f"/api/exchange/tasks/{task['id']}/status", json={"status": "completed"}, headers=H)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_task_delete_running_blocked(client):
    partner = await _create_partner(client, "EXT-P-RUN")
    proto = await _create_protocol(client, "PROTO-RUN", partner["id"])
    task = await _create_task(client, "TASK-RUN", partner["id"], proto["id"])
    await client.patch(f"/api/exchange/tasks/{task['id']}/status", json={"status": "running"}, headers=H)
    resp = await client.delete(f"/api/exchange/tasks/{task['id']}", headers=H)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_partner_referenced_blocked(client):
    partner = await _create_partner(client, "EXT-P-USED")
    proto = await _create_protocol(client, "PROTO-USED", partner["id"])
    await _create_task(client, "TASK-USED", partner["id"], proto["id"])
    resp = await client.delete(f"/api/exchange/partners/{partner['id']}", headers=H)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_terminal_task_ok(client):
    partner = await _create_partner(client, "EXT-P-TERM")
    proto = await _create_protocol(client, "PROTO-TERM", partner["id"])
    task = await _create_task(client, "TASK-TERM", partner["id"], proto["id"])
    # draft 状态可删除（未运行）
    resp = await client.delete(f"/api/exchange/tasks/{task['id']}", headers=H)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


@pytest.mark.asyncio
async def test_list_tasks_status_filter(client):
    partner = await _create_partner(client, "EXT-P-LST")
    proto = await _create_protocol(client, "PROTO-LST", partner["id"])
    await _create_task(client, "TASK-LST", partner["id"], proto["id"])
    resp = await client.get("/api/exchange/tasks?status=draft", headers=H)
    assert resp.status_code == 200
    body = resp.json()
    assert all(t["status"] == "draft" for t in body["items"])
    assert any(t["code"] == "TASK-LST" for t in body["items"])
