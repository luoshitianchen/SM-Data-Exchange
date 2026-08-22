# SM Data Exchange

数据交换与ETL：同步任务、质量校验、失败重试和数据血缘。

```powershell
git clone https://github.com/luoshitianchen/SM-Data-Exchange.git
cd SM-Data-Exchange
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8480
```

接口：`/health`、`/readyz`、`/api/overview`、`/api/items`、`/api/ops/metrics`、`/api/crypto/status`。

内置 TrustedHost、安全响应头、CSP、国密状态接口和容器加固。
