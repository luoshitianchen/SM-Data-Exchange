"""SM Data Exchange —— 数据交换与集成：连接器、交换任务、运行日志与调度。"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field

from app import base

SERVICE = "sm-data-exchange"
VERSION = "2.0.0"
NAME = "SM Data Exchange"
DESCRIPTION = "数据交换与集成：连接器、交换任务、运行日志与调度"
PORT = 8480


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _init() -> None:
    with base.db_ctx() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS connectors (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, connector_type TEXT NOT NULL,
                endpoint TEXT NOT NULL, auth_type TEXT NOT NULL DEFAULT 'none',
                enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, source_id TEXT NOT NULL,
                target_id TEXT NOT NULL, mapping TEXT NOT NULL DEFAULT '{}',
                schedule TEXT NOT NULL DEFAULT 'manual', status TEXT NOT NULL DEFAULT 'idle',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY, job_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'running',
                rows_read INTEGER NOT NULL DEFAULT 0, rows_written INTEGER NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL, finished_at TEXT, error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_runs_job ON runs(job_id, started_at DESC);
            """
        )


app = base.create_app(
    service=SERVICE, name=NAME, description=DESCRIPTION, version=VERSION, port=PORT,
    dependencies=["sm-iam", "sm-data-governance", "sm-audit-log-center"],
    events=["exchange.job_started", "exchange.job_completed", "exchange.job_failed"],
    overview_fn=lambda _r: {
        "summary": {
            "connectors": base.get_db().execute("SELECT COUNT(*) FROM connectors").fetchone()[0],
            "jobs": base.get_db().execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
            "runs": base.get_db().execute("SELECT COUNT(*) FROM runs").fetchone()[0],
        }
    },
)
_init()


class ConnectorIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    connector_type: str = Field(pattern=r"^(database|api|file|message-queue)$")
    endpoint: str = Field(min_length=2, max_length=300)
    auth_type: str = Field(default="none", pattern=r"^(none|basic|token|oauth2)$")


class JobIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    source_id: str = Field(min_length=8)
    target_id: str = Field(min_length=8)
    mapping: dict[str, Any] = Field(default_factory=dict)
    schedule: str = Field(default="manual", pattern=r"^(manual|hourly|daily|event-driven)$")


@app.get("/api/exchange/connectors")
def list_connectors() -> dict[str, Any]:
    with base.db_ctx() as conn:
        rows = conn.execute("SELECT * FROM connectors ORDER BY created_at DESC").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/exchange/connectors", status_code=status.HTTP_201_CREATED)
def create_connector(payload: ConnectorIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    connector_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        try:
            conn.execute("INSERT INTO connectors VALUES (?,?,?,?,?,1,?)", (connector_id, payload.name, payload.connector_type, payload.endpoint, payload.auth_type, _now()))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_409_CONFLICT, "连接器已存在") from exc
    return {"id": connector_id, "name": payload.name}


@app.get("/api/exchange/jobs")
def list_jobs() -> dict[str, Any]:
    with base.db_ctx() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/exchange/jobs", status_code=status.HTTP_201_CREATED)
def create_job(payload: JobIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    with base.db_ctx() as conn:
        source = conn.execute("SELECT * FROM connectors WHERE id=?", (payload.source_id,)).fetchone()
        target = conn.execute("SELECT * FROM connectors WHERE id=?", (payload.target_id,)).fetchone()
        if not source or not target:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "连接器不存在")
        if not source["enabled"] or not target["enabled"]:
            raise HTTPException(status.HTTP_423_LOCKED, "连接器已停用")
        job_id = str(uuid.uuid4())
        try:
            conn.execute("INSERT INTO jobs (id, name, source_id, target_id, mapping, schedule, status, created_at) VALUES (?,?,?,?,?,?,?,?)", (job_id, payload.name, payload.source_id, payload.target_id, __import__("json").dumps(payload.mapping, ensure_ascii=False), payload.schedule, "idle", _now()))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_409_CONFLICT, "任务名已存在") from exc
        base.record_audit("exchange.job_created", "internal", f"job={job_id} name={payload.name}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": job_id, "name": payload.name}


@app.post("/api/exchange/jobs/{job_id}/run")
def run_job(job_id: str, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    with base.db_ctx() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换任务不存在")
        run_id = str(uuid.uuid4())
        # 模拟管道执行：读取/写入行数可基于映射字段数派生
        rows_read = secrets.randbelow(10000) + 100
        rows_written = rows_read  # 全量同步语义
        conn.execute("INSERT INTO runs (id, job_id, status, rows_read, rows_written, started_at, finished_at) VALUES (?,?,?,?,?,?,?)", (run_id, job_id, "success", rows_read, rows_written, _now(), _now()))
        conn.execute("UPDATE jobs SET status='success' WHERE id=?", (job_id,))
        base.record_audit("exchange.job_completed", "internal", f"job={job_id} run={run_id} rows={rows_written}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": run_id, "job_id": job_id, "status": "success", "rows_read": rows_read, "rows_written": rows_written}


@app.get("/api/exchange/jobs/{job_id}/runs")
def list_runs(job_id: str) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if not conn.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "交换任务不存在")
        rows = conn.execute("SELECT * FROM runs WHERE job_id=? ORDER BY started_at DESC LIMIT 100", (job_id,)).fetchall()
    return {"job_id": job_id, "items": [dict(r) for r in rows], "total": len(rows)}


@app.get("/api/exchange/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    with base.db_ctx() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "运行记录不存在")
    return dict(row)


@app.get("/api/exchange/stats")
def stats() -> dict[str, Any]:
    with base.db_ctx() as conn:
        def _count(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]
        total_written = conn.execute("SELECT COALESCE(SUM(rows_written),0) FROM runs").fetchone()[0]
        return {
            "connectors": _count("SELECT COUNT(*) FROM connectors"),
            "jobs": _count("SELECT COUNT(*) FROM jobs"),
            "runs": _count("SELECT COUNT(*) FROM runs"),
            "success_runs": _count("SELECT COUNT(*) FROM runs WHERE status='success'"),
            "failed_runs": _count("SELECT COUNT(*) FROM runs WHERE status='failed'"),
            "total_rows_written": int(total_written),
        }
