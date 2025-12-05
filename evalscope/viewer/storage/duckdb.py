"""
DuckDB + Parquet Storage Implementation (Single Mode)

Stores evaluation results using DuckDB for queries and Parquet for data storage.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import duckdb
import numpy as np
import pandas as pd
import yaml

from .base import StorageBackend
from evalscope.viewer.etl.adapters.evalscope_adapter import EvalScopeAdapter


def _convert_numpy_types(data: Union[Dict, List]) -> Union[Dict, List]:
    """Convert numpy types to Python native types recursively"""
    if isinstance(data, dict):
        return {k: _convert_numpy_types(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_convert_numpy_types(item) for item in data]
    elif isinstance(data, np.ndarray):
        return data.tolist()
    elif hasattr(data, "item"):  # numpy scalar
        return data.item()
    return data


class SingleModeStorage(StorageBackend):
    """
    Single mode storage using DuckDB + Parquet

    Directory structure:
    data_dir/
    ├── viewer.duckdb         # DuckDB database (indexes + views)
    └── cache/                # Parquet cache
        ├── runs.parquet      # All runs metadata
        └── samples/          # Samples per run
            └── {run_id}/
                └── {dataset}.parquet
    """

    def __init__(self, outputs_dir: str, data_dir: str = ".viewer"):
        self.outputs_dir = Path(outputs_dir)
        self.data_dir = Path(data_dir)
        self.cache_dir = self.data_dir / "cache"
        self.samples_dir = self.cache_dir / "samples"
        self.db_path = self.data_dir / "viewer.duckdb"
        self.runs_parquet = self.cache_dir / "runs.parquet"

        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        self.samples_dir.mkdir(exist_ok=True)

        # Initialize adapter for data transformation
        self.adapter = EvalScopeAdapter()

        # Connect to DuckDB
        self.conn = duckdb.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self):
        """Initialize DuckDB tables"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cache_index (
                run_id VARCHAR PRIMARY KEY,
                source_dir VARCHAR NOT NULL,
                datasets VARCHAR[],
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def sync(self, outputs_dir: str = None) -> int:
        """Sync cache from outputs directory"""
        outputs = Path(outputs_dir) if outputs_dir else self.outputs_dir

        if not outputs.exists():
            return 0

        # Get already cached runs
        cached_runs = set(self.get_cached_run_ids())

        # Scan for new runs
        new_count = 0
        for run_dir in sorted(outputs.iterdir()):
            if not run_dir.is_dir():
                continue

            run_id = run_dir.name

            # Skip if already cached
            if run_id in cached_runs:
                continue

            # Validate it's an evalscope output
            if not self._is_valid_run(run_dir):
                continue

            # Cache the run
            try:
                self._cache_run(run_dir, run_id)
                new_count += 1
            except Exception as e:
                print(f"  Warning: Failed to cache {run_id}: {e}")

        # Rebuild runs.parquet if new runs were cached
        if new_count > 0:
            self._rebuild_runs_parquet()

        return new_count

    def _is_valid_run(self, run_dir: Path) -> bool:
        """Check if directory is a valid evalscope output"""
        # Must have reports directory with at least one JSON file
        reports_dir = run_dir / "reports"
        if not reports_dir.exists():
            return False
        # Check for JSON files directly or in subdirectories (model dirs)
        return any(reports_dir.glob("*.json")) or any(reports_dir.glob("*/*.json"))

    def _cache_run(self, run_dir: Path, run_id: str):
        """Cache a single run to Parquet"""
        # Create samples directory for this run
        run_samples_dir = self.samples_dir / run_id
        run_samples_dir.mkdir(parents=True, exist_ok=True)

        datasets = []

        # Collect dataset names from reviews directory
        reviews_dir = run_dir / "reviews"
        if reviews_dir.exists():
            for model_dir in reviews_dir.iterdir():
                if not model_dir.is_dir():
                    continue
                for jsonl_file in model_dir.glob("*.jsonl"):
                    dataset = jsonl_file.stem
                    if dataset not in datasets:
                        datasets.append(dataset)

        # Use Adapter to cache samples for each dataset
        for dataset in datasets:
            self._cache_samples(run_dir, run_id, dataset, run_samples_dir)

        # Register in cache index
        self.conn.execute("""
            INSERT OR REPLACE INTO cache_index (run_id, source_dir, datasets)
            VALUES (?, ?, ?)
        """, [run_id, str(run_dir), datasets])

    def _cache_samples(self, run_dir: Path, run_id: str, dataset: str, output_dir: Path):
        """Convert samples to Parquet using Adapter for transformation"""
        parquet_file = output_dir / f"{dataset}.parquet"

        # Use Adapter to extract and transform samples
        samples = self.adapter.extract_samples(run_dir, dataset, limit=100000)

        if not samples:
            return

        # Convert Sample objects to DataFrame-ready dicts
        sample_dicts = []
        for s in samples:
            sample_dicts.append({
                "run_id": run_id,
                "dataset": dataset,
                "sample_id": str(s.id),
                "input": s.input if isinstance(s.input, str) else json.dumps(s.input),
                "target": s.target,
                "prediction": s.prediction,
                "extracted_prediction": s.extracted_prediction,
                "scores": json.dumps(s.scores) if s.scores else None,
                "is_correct": s.is_correct,
            })

        # Use pandas DataFrame + DuckDB to write Parquet
        df = pd.DataFrame(sample_dicts)
        self.conn.register("_samples_df", df)
        self.conn.execute(f"""
            COPY _samples_df TO '{parquet_file}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """)
        self.conn.unregister("_samples_df")

    def _rebuild_runs_parquet(self):
        """Rebuild runs.parquet from source reports"""
        # Collect all run data
        runs_data = []

        result = self.conn.execute("SELECT run_id, source_dir, datasets FROM cache_index").fetchall()

        for run_id, source_dir, datasets in result:
            run_dir = Path(source_dir)
            run_info = self._extract_run_info(run_dir, run_id, datasets)
            if run_info:
                runs_data.append(run_info)

        if not runs_data:
            return

        # Create runs.parquet
        self.conn.execute(f"""
            COPY (
                SELECT * FROM (VALUES {self._format_runs_values(runs_data)})
                AS t(run_id, timestamp, model_name, model_type, model_revision, datasets,
                     overall_score, total_samples, status, config, start_time, end_time, duration_seconds)
            )
            TO '{self.runs_parquet}' (FORMAT PARQUET)
        """)

    def _format_runs_values(self, runs_data: List[Dict]) -> str:
        """Format runs data as SQL VALUES"""
        values = []
        for r in runs_data:
            datasets_str = "[" + ", ".join(f"'{d}'" for d in r["datasets"]) + "]"
            config_str = json.dumps(r.get("config", {})).replace("'", "''")
            model_revision = r.get("model_revision")
            revision_str = f"'{model_revision}'" if model_revision else "NULL"
            end_time = r.get("end_time")
            end_time_str = f"'{end_time}'" if end_time else "NULL"
            duration = r.get("duration_seconds")
            duration_str = str(duration) if duration is not None else "NULL"
            values.append(
                f"('{r['run_id']}', '{r['timestamp']}', '{r['model_name']}', "
                f"'{r['model_type']}', {revision_str}, {datasets_str}::VARCHAR[], "
                f"{r['overall_score']}, {r['total_samples']}, '{r['status']}', "
                f"'{config_str}', '{r['start_time']}', {end_time_str}, {duration_str})"
            )
        return ", ".join(values)

    def _extract_run_info(self, run_dir: Path, run_id: str, datasets: List[str]) -> Optional[Dict]:
        """Extract run info from source directory"""
        import re

        # Read config
        config = {}
        model_name = "unknown"
        model_type = "unknown"
        model_revision = None

        config_dir = run_dir / "configs"
        if config_dir.exists():
            for yaml_file in config_dir.glob("*.yaml"):
                try:
                    with open(yaml_file) as f:
                        config = yaml.safe_load(f) or {}
                    model_name = config.get("model", config.get("model_id", "unknown"))
                    model_type = config.get("eval_type", "unknown")
                    model_revision = config.get("model_revision") or config.get("revision")
                    break
                except Exception:
                    pass

        # Extract timing from log file
        start_time = None
        end_time = None
        duration_seconds = None

        log_file = run_dir / "logs" / "eval_log.log"
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        # Parse first line for start time
                        first_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', lines[0])
                        if first_match:
                            start_time = first_match.group(1).replace(' ', 'T')

                        # Parse last few lines for end time
                        for line in reversed(lines[-10:]):
                            last_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                            if last_match:
                                end_time = last_match.group(1).replace(' ', 'T')
                                break

                        # Calculate duration
                        if start_time and end_time:
                            from datetime import datetime
                            start_dt = datetime.fromisoformat(start_time)
                            end_dt = datetime.fromisoformat(end_time)
                            duration_seconds = (end_dt - start_dt).total_seconds()
            except Exception:
                pass

        # Calculate overall score from reports
        total_score = 0.0
        total_samples = 0
        report_count = 0

        reports_dir = run_dir / "reports"
        if reports_dir.exists():
            # Look for JSON files directly and in subdirectories
            json_files = list(reports_dir.glob("*.json")) + list(reports_dir.glob("*/*.json"))
            for json_file in json_files:
                try:
                    with open(json_file) as f:
                        report = json.load(f)
                    score = report.get("score", 0)
                    if score:
                        total_score += float(score)
                        report_count += 1
                    # Get sample count from metrics
                    for metric in report.get("metrics", []):
                        if "num" in metric:
                            total_samples += metric["num"]
                            break
                except Exception:
                    pass

        overall_score = total_score / report_count if report_count > 0 else 0.0

        return {
            "run_id": run_id,
            "timestamp": run_id,
            "model_name": str(model_name).replace("'", "''"),
            "model_type": str(model_type).replace("'", "''"),
            "model_revision": str(model_revision).replace("'", "''") if model_revision else None,
            "datasets": datasets,
            "overall_score": round(overall_score, 4),
            "total_samples": total_samples,
            "status": "completed",
            "config": config,
            "start_time": start_time or datetime.now().isoformat(),
            "end_time": end_time,
            "duration_seconds": duration_seconds,
        }

    def list_runs(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List all runs"""
        if not self.runs_parquet.exists():
            return [], 0

        # Build query
        where_clauses = []
        if filters:
            if "model_name" in filters:
                where_clauses.append(f"model_name ILIKE '%{filters['model_name']}%'")
            if "dataset" in filters:
                where_clauses.append(f"list_contains(datasets, '{filters['dataset']}')")
            if "status" in filters:
                where_clauses.append(f"status = '{filters['status']}'")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Get total count
        total = self.conn.execute(f"""
            SELECT count(*) FROM '{self.runs_parquet}' {where_sql}
        """).fetchone()[0]

        # Get paginated results
        df = self.conn.execute(f"""
            SELECT * FROM '{self.runs_parquet}'
            {where_sql}
            ORDER BY timestamp DESC
            LIMIT {limit} OFFSET {offset}
        """).fetchdf()

        runs = df.to_dict("records")

        # Convert numpy types to Python types
        runs = [_convert_numpy_types(run) for run in runs]

        return runs, total

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run metadata"""
        if not self.runs_parquet.exists():
            return None

        df = self.conn.execute(f"""
            SELECT * FROM '{self.runs_parquet}'
            WHERE run_id = '{run_id}'
        """).fetchdf()

        if df.empty:
            return None

        run = df.to_dict("records")[0]

        return _convert_numpy_types(run)

    def get_run_summary(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run evaluation summary"""
        # Get source directory
        result = self.conn.execute("""
            SELECT source_dir, datasets FROM cache_index WHERE run_id = ?
        """, [run_id]).fetchone()

        if not result:
            return None

        source_dir, datasets_list = result
        run_dir = Path(source_dir)

        # Read reports (handle both direct and nested structures)
        dataset_evaluations = []
        total_samples = 0
        total_score = 0.0
        reports_dir = run_dir / "reports"

        if reports_dir.exists():
            # Look for JSON files directly and in subdirectories
            json_files = list(reports_dir.glob("*.json")) + list(reports_dir.glob("*/*.json"))
            for json_file in json_files:
                try:
                    with open(json_file) as f:
                        report = json.load(f)

                    score = report.get("score", 0)
                    num_samples = 0
                    metrics_dict = {}

                    # Process metrics
                    for metric in report.get("metrics", []):
                        metric_name = metric.get("name", "unknown")
                        metrics_dict[metric_name] = {
                            "score": metric.get("value", 0),
                            "num_samples": metric.get("num", 0),
                        }
                        if "num" in metric:
                            num_samples = max(num_samples, metric["num"])

                    dataset_evaluations.append({
                        "dataset": report.get("dataset_name", json_file.stem),
                        "dataset_pretty_name": report.get("dataset_name", json_file.stem),
                        "overall_score": float(score) if score else 0.0,
                        "metrics": metrics_dict,
                        "categories": [],
                    })

                    total_samples += num_samples
                    if score:
                        total_score += float(score)
                except Exception:
                    pass

        num_datasets = len(dataset_evaluations)
        avg_score = total_score / num_datasets if num_datasets > 0 else 0.0

        return {
            "run_id": run_id,
            "schema_version": "1.0",
            "datasets": dataset_evaluations,
            "overall": {
                "avg_score": avg_score,
                "total_samples": total_samples,
                "total_datasets": num_datasets,
            },
        }

    def get_samples(
        self,
        run_id: str,
        dataset: str,
        limit: int = 100,
        offset: int = 0,
        filter_correct: Optional[bool] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get sample data with pagination"""
        parquet_file = self.samples_dir / run_id / f"{dataset}.parquet"

        if not parquet_file.exists():
            return [], 0

        # Build where clause
        where_clauses = []
        if filter_correct is not None:
            where_clauses.append(f"is_correct = {str(filter_correct).lower()}")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Get total count
        total = self.conn.execute(f"""
            SELECT count(*) FROM '{parquet_file}' {where_sql}
        """).fetchone()[0]

        # Get paginated results
        df = self.conn.execute(f"""
            SELECT * FROM '{parquet_file}'
            {where_sql}
            ORDER BY sample_id
            LIMIT {limit} OFFSET {offset}
        """).fetchdf()

        samples = df.to_dict("records")

        # Convert numpy types to Python types
        samples = [_convert_numpy_types(s) for s in samples]

        # Transform to frontend-expected format
        for sample in samples:
            # Rename sample_id to id
            if "sample_id" in sample:
                sample["id"] = sample.pop("sample_id")
            # Parse scores JSON string to dict
            if "scores" in sample and isinstance(sample["scores"], str):
                try:
                    sample["scores"] = json.loads(sample["scores"])
                except (json.JSONDecodeError, TypeError):
                    sample["scores"] = {}

        return samples, total

    def get_sample_stats(self, run_id: str, dataset: str) -> Dict[str, Any]:
        """Get sample statistics for a dataset"""
        parquet_file = self.samples_dir / run_id / f"{dataset}.parquet"

        if not parquet_file.exists():
            return {"total": 0, "correct": 0, "incorrect": 0, "accuracy": 0}

        result = self.conn.execute(f"""
            SELECT
                count(*) as total,
                sum(CASE WHEN is_correct = TRUE THEN 1 ELSE 0 END) as correct,
                sum(CASE WHEN is_correct = FALSE THEN 1 ELSE 0 END) as incorrect
            FROM '{parquet_file}'
        """).fetchone()

        total, correct, incorrect = result
        accuracy = correct / total if total > 0 else 0

        return {
            "total": total,
            "correct": correct,
            "incorrect": incorrect,
            "accuracy": round(accuracy, 4),
        }

    def delete_run(self, run_id: str) -> bool:
        """Delete a run and its cache"""
        # Delete samples directory
        samples_dir = self.samples_dir / run_id
        if samples_dir.exists():
            shutil.rmtree(samples_dir)

        # Remove from index
        self.conn.execute("DELETE FROM cache_index WHERE run_id = ?", [run_id])

        # Rebuild runs.parquet
        self._rebuild_runs_parquet()

        return True

    def run_exists(self, run_id: str) -> bool:
        """Check if a run exists"""
        result = self.conn.execute("""
            SELECT 1 FROM cache_index WHERE run_id = ?
        """, [run_id]).fetchone()
        return result is not None

    def get_cached_run_ids(self) -> List[str]:
        """Get list of cached run IDs"""
        result = self.conn.execute("SELECT run_id FROM cache_index").fetchall()
        return [r[0] for r in result]
