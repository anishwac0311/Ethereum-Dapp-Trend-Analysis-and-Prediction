# DApp Dataset Dashboard

Interactive React + FastAPI dashboard comparing **v1** (`dapp_data/`) and **v2** (`dapp_data_v2/`).

## Run (dev)

From the project root:

```powershell
.\dashboard\run.ps1
```

Or manually:

```powershell
# terminal 1 — API
cd dashboard\backend
..\..\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

# terminal 2 — UI
cd dashboard\frontend
npm run dev
```

Open http://127.0.0.1:5173

## Production build

```powershell
cd dashboard\frontend
npm run build
cd ..\backend
..\..\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000 (FastAPI serves `frontend/dist`).

## Live data

The backend loads CSVs into an in-memory DuckDB (never opens the pipeline’s `dapp_v2.duckdb`).  
A file watcher reloads when output CSVs settle after a write, and `/api/events` pushes `dataVersion` + pipeline status parsed from `dapp_data_v2/run.log`.
