"""
FastAPI Application

Provides REST API for accessing viewer data.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from evalscope.viewer.storage import get_storage


def transform_run_to_protocol(run: Dict[str, Any], full: bool = False) -> Dict[str, Any]:
    """Transform flat storage format to protocol format expected by frontend

    Args:
        run: Raw run data from storage
        full: If True, include full details for single run view
    """
    config = run.get("config", {})
    if isinstance(config, str):
        import json
        try:
            config = json.loads(config)
        except Exception:
            config = {}

    result = {
        "run_id": run.get("run_id"),
        "timestamp": run.get("timestamp"),
        "framework": "evalscope",
        "model": {
            "name": run.get("model_name", "Unknown"),
            "type": run.get("model_type", "unknown"),
            "revision": run.get("model_revision"),
        },
        "datasets": run.get("datasets", []),
        "overall_score": run.get("overall_score"),
        "num_samples": run.get("total_samples", 0),
        "start_time": run.get("start_time", run.get("timestamp")),
        "end_time": run.get("end_time"),
        "duration_seconds": run.get("duration_seconds"),
        "status": run.get("status", "unknown"),
        "tags": [],
    }

    if full:
        result.update({
            "schema_version": "1.0",
            "config": {
                "eval_batch_size": config.get("eval_batch_size"),
                "seed": config.get("seed"),
                "limit": config.get("limit"),
            },
            "environment": {
                "framework": "evalscope",
                "framework_version": None,
            },
        })

    return result


class RunsResponse(BaseModel):
    """Response model for runs list"""

    runs: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class SamplesResponse(BaseModel):
    """Response model for samples list"""

    samples: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int
    stats: Dict[str, Any]


def create_app(
    mode: str = "single",
    outputs_dir: str = "./outputs",
    data_dir: str = ".viewer",
) -> FastAPI:
    """
    Create FastAPI application

    Args:
        mode: Storage mode ('single' or 'team')
        outputs_dir: EvalScope outputs directory
        data_dir: Viewer data directory

    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="EvalScope Viewer API",
        description="API for accessing evaluation results",
        version="0.2.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize storage
    storage = get_storage(mode=mode, outputs_dir=outputs_dir, data_dir=data_dir)

    # Store in app state
    app.state.storage = storage
    app.state.mode = mode
    app.state.outputs_dir = outputs_dir

    # API Routes
    @app.get("/api/v1/runs", response_model=RunsResponse)
    async def list_runs(
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        model_name: Optional[str] = None,
        dataset: Optional[str] = None,
        status: Optional[str] = None,
    ):
        """List all evaluation runs"""
        filters = {}
        if model_name:
            filters["model_name"] = model_name
        if dataset:
            filters["dataset"] = dataset
        if status:
            filters["status"] = status

        runs, total = storage.list_runs(
            limit=limit,
            offset=offset,
            filters=filters if filters else None,
        )

        # Transform to protocol format
        transformed_runs = [transform_run_to_protocol(run) for run in runs]

        return RunsResponse(runs=transformed_runs, total=total, limit=limit, offset=offset)

    @app.get("/api/v1/runs/{run_id}")
    async def get_run(run_id: str):
        """Get run metadata"""
        run = storage.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return transform_run_to_protocol(run, full=True)

    @app.get("/api/v1/runs/{run_id}/summary")
    async def get_run_summary(run_id: str):
        """Get evaluation summary for a run"""
        summary = storage.get_run_summary(run_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Summary not found")
        return summary

    @app.get("/api/v1/runs/{run_id}/samples/{dataset}", response_model=SamplesResponse)
    async def get_samples(
        run_id: str,
        dataset: str,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        correct: Optional[bool] = None,
    ):
        """Get samples for a dataset in a run"""
        if not storage.run_exists(run_id):
            raise HTTPException(status_code=404, detail="Run not found")

        samples, total = storage.get_samples(
            run_id, dataset, limit=limit, offset=offset, filter_correct=correct
        )
        stats = storage.get_sample_stats(run_id, dataset)

        return SamplesResponse(
            samples=samples,
            total=total,
            limit=limit,
            offset=offset,
            stats=stats,
        )

    @app.delete("/api/v1/runs/{run_id}")
    async def delete_run(run_id: str):
        """Delete a run"""
        if not storage.run_exists(run_id):
            raise HTTPException(status_code=404, detail="Run not found")

        success = storage.delete_run(run_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete run")

        return {"message": "Run deleted successfully"}

    @app.post("/api/v1/sync")
    async def sync_cache():
        """Sync cache from outputs directory"""
        new_count = storage.sync(outputs_dir)
        total = len(storage.get_cached_run_ids())
        return {"new_runs": new_count, "total_runs": total}

    @app.get("/api/v1/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "ok", "mode": mode}

    # Simple HTML page for demo
    @app.get("/", response_class=HTMLResponse)
    async def index():
        """Serve a simple demo page"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>EvalScope Viewer</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #333; }
        .card { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .run { border-left: 4px solid #4CAF50; }
        .run h3 { margin: 0 0 10px 0; color: #333; }
        .run p { margin: 5px 0; color: #666; }
        .score { font-size: 24px; font-weight: bold; color: #4CAF50; }
        .meta { font-size: 12px; color: #999; }
        .empty { text-align: center; padding: 60px; color: #999; }
        .api-info { background: #e3f2fd; border-left: 4px solid #2196F3; }
        code { background: #f5f5f5; padding: 2px 6px; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>EvalScope Viewer</h1>

        <div class="card api-info">
            <h3>API Endpoints</h3>
            <ul>
                <li><code>GET /api/v1/runs</code> - List all runs</li>
                <li><code>GET /api/v1/runs/{run_id}</code> - Get run details</li>
                <li><code>GET /api/v1/runs/{run_id}/summary</code> - Get evaluation summary</li>
                <li><code>GET /api/v1/runs/{run_id}/samples/{dataset}</code> - Get samples</li>
                <li><code>POST /api/v1/sync</code> - Sync cache from outputs</li>
            </ul>
        </div>

        <h2>Evaluation Runs</h2>
        <div id="runs-container">
            <div class="card empty">Loading...</div>
        </div>
    </div>

    <script>
        async function loadRuns() {
            try {
                const response = await fetch('/api/v1/runs');
                const data = await response.json();

                const container = document.getElementById('runs-container');

                if (data.runs.length === 0) {
                    container.innerHTML = '<div class="card empty">No evaluation runs found. Run evalscope-viewer sync first!</div>';
                    return;
                }

                container.innerHTML = data.runs.map(run => `
                    <div class="card run">
                        <h3>${run.model_name || 'Unknown Model'}</h3>
                        <p class="score">${((run.overall_score || 0) * 100).toFixed(1)}%</p>
                        <p><strong>Datasets:</strong> ${(run.datasets || []).join(', ') || 'N/A'}</p>
                        <p><strong>Samples:</strong> ${run.total_samples || 0}</p>
                        <p class="meta">
                            <strong>Run ID:</strong> ${run.run_id}<br>
                            <strong>Status:</strong> ${run.status}
                        </p>
                    </div>
                `).join('');
            } catch (error) {
                document.getElementById('runs-container').innerHTML =
                    '<div class="card empty">Error loading runs: ' + error.message + '</div>';
            }
        }

        loadRuns();
    </script>
</body>
</html>
        """

    return app


def run_server(
    host: str = "127.0.0.1",
    port: int = 7862,
    mode: str = "single",
    outputs_dir: str = "./outputs",
    data_dir: str = ".viewer",
):
    """Run the viewer server"""
    import uvicorn

    app = create_app(mode=mode, outputs_dir=outputs_dir, data_dir=data_dir)
    uvicorn.run(app, host=host, port=port)
