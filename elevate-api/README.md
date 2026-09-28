# Elevate API

Local FastAPI employee-record service backed by deterministic in-memory seed data.

## Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:api --reload --host 0.0.0.0 --port 8000
```

Every `/api/*` endpoint requires a seeded development identity, for example:

```powershell
curl.exe -H "X-Dev-User: jenny.marsh" http://localhost:8000/api/employees
```

Interactive documentation is available at `http://localhost:8000/docs`.
