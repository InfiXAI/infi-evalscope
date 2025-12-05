# EvalScope Viewer

A visualization tool for EvalScope evaluation results. Provides a REST API and web interface for browsing evaluation runs, metrics, and sample-level results.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EvalScope Viewer                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   outputs/              ETL Layer              Storage Layer    │
│   ├── configs/    ──→  EvalScopeAdapter  ──→  DuckDB +         │
│   ├── predictions/      (extract & transform)  Parquet         │
│   ├── reviews/                │                                │
│   └── reports/                ▼                                │
│                        Protocol Models              ▲          │
│                        (ExperimentRun,              │          │
│                         EvaluationSummary,          │          │
│                         Sample)              Server Layer      │
│                                              (FastAPI REST)    │
│                                                     │          │
│                                                     ▼          │
│                                              Web Frontend      │
│                                              (Next.js)         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Install dependencies
pip install -e '.[viewer]'

# Run evaluation (API mode)
evalscope eval \
    --model Qwen2.5-3B-Instruct \
    --api-url http://192.168.1.250:30000/v1 \
    --api-key EMPTY \
    --eval-type openai_api \
    --datasets gsm8k \
    --limit 10 \
    --eval-batch-size 8

# Start viewer (API + Web)
evalscope-viewer serve --outputs-dir ./outputs --with-web

# Open browser: http://localhost:3000
```

## CLI Reference

### `evalscope-viewer serve`

Start the viewer server.

```bash
evalscope-viewer serve [OPTIONS]

Options:
  --host TEXT           Server host (default: 127.0.0.1)
  --port INTEGER        API server port (default: 7862)
  --with-web            Also start the web frontend server
  --frontend-port INT   Frontend server port (default: 3000)
  --outputs-dir TEXT    EvalScope outputs directory (default: ./outputs)
  --data-dir TEXT       Viewer cache directory (default: .viewer)
  --mode TEXT           Storage mode: single or team (default: single)
```

**Examples:**

```bash
# Full stack: API + Web
evalscope-viewer serve --outputs-dir ./outputs --with-web

# API only
evalscope-viewer serve --outputs-dir ./outputs

# Custom ports
evalscope-viewer serve --outputs-dir ./outputs --with-web \
  --port 8000 --frontend-port 3001

# Allow external access
evalscope-viewer serve --outputs-dir ./outputs --with-web --host 0.0.0.0
```

### `evalscope-viewer sync`

Manually sync evaluation results from outputs directory to cache.

```bash
evalscope-viewer sync --outputs-dir ./outputs
```

### `evalscope-viewer list`

List all cached runs.

```bash
evalscope-viewer list [OPTIONS]

Options:
  --limit INT         Maximum runs to list (default: 100)
  --outputs-dir TEXT  EvalScope outputs directory (default: ./outputs)
  --data-dir TEXT     Viewer cache directory (default: .viewer)
```

### `evalscope-viewer delete`

Delete a run from cache.

```bash
evalscope-viewer delete <RUN_ID> [OPTIONS]

Options:
  -f, --force         Skip confirmation prompt
  --outputs-dir TEXT  EvalScope outputs directory (default: ./outputs)
  --data-dir TEXT     Viewer cache directory (default: .viewer)
```

## REST API

The server exposes a REST API at `/api/v1/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/runs` | GET | List all runs (supports filtering, pagination) |
| `/api/v1/runs/{run_id}` | GET | Get run details |
| `/api/v1/runs/{run_id}/samples/{dataset}` | GET | Get samples (supports pagination) |
| `/api/v1/runs/{run_id}` | DELETE | Delete a run |

**Query Parameters for `/api/v1/runs`:**
- `limit`: Maximum results (default: 100)
- `offset`: Pagination offset (default: 0)
- `sort_by`: Sort field (default: start_time)
- `sort_order`: asc or desc (default: desc)
- `model_name`: Filter by model name (partial match)
- `status`: Filter by status

**Query Parameters for samples:**
- `limit`: Maximum samples (default: 100)
- `offset`: Pagination offset (default: 0)

## Data Storage

Viewer uses **DuckDB + Parquet** for data storage:

```
.viewer/                      # Cache directory (configurable via --data-dir)
├── viewer.duckdb            # DuckDB database (indexes and views)
└── cache/                   # Parquet cache files
    ├── runs.parquet         # All runs metadata
    └── samples/             # Sample data per run
        └── {run_id}/
            └── {dataset}.parquet
```

> Note: The `.viewer/` directory is auto-generated cache. Add it to `.gitignore`.

## Data Flow

```
1. Run Evaluation
   evalscope eval \
       --model Qwen2.5-3B-Instruct \
       --api-url http://192.168.1.250:30000/v1 \
       --api-key EMPTY \
       --eval-type openai_api \
       --datasets gsm8k

   Output:
   outputs/20251204_143025/
   ├── configs/task_config_xxx.yaml
   ├── predictions/<model>/gsm8k_main.jsonl
   ├── reviews/<model>/gsm8k_main.jsonl
   └── reports/<model>/gsm8k.json

2. Start Viewer (auto-sync)
   evalscope-viewer serve --outputs-dir ./outputs --with-web

   Cache created:
   .viewer/
   ├── viewer.duckdb
   └── cache/
       ├── runs.parquet
       └── samples/20251204_143025/gsm8k_main.parquet

3. Access Web UI
   http://localhost:3000
```

## Directory Structure

```
evalscope/viewer/
├── cli.py              # CLI entry point
├── protocol/           # Data models (Pydantic)
│   └── models.py       # ExperimentRun, Sample, etc.
├── etl/                # Extract-Transform-Load
│   └── adapters/
│       ├── base.py
│       └── evalscope_adapter.py
├── storage/            # Persistence layer
│   ├── base.py         # Abstract StorageBackend
│   ├── duckdb.py       # DuckDB + Parquet storage
│   └── factory.py      # get_storage()
├── server/             # API server
│   └── app.py          # FastAPI app
└── web/                # Frontend (Next.js)
    ├── app/            # Next.js pages
    └── components/     # React components
```

## Development

### Running the Server

```bash
# From project root
python -m evalscope.viewer.cli serve --outputs-dir ./outputs --port 7862
```

### Running the Frontend

```bash
cd evalscope/viewer/web
npm install
npm run dev
```

## Requirements

**Python:**
- Python 3.8+
- fastapi
- uvicorn
- pydantic
- pyyaml
- duckdb
- pandas
- pyarrow

**Frontend:**
- Node.js 18+
- npm
