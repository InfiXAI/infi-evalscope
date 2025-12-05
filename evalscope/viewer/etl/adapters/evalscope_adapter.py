"""
EvalScope Framework Adapter

Converts EvalScope evaluation outputs to standard protocol.
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from evalscope.viewer.protocol.models import (
    CategoryBreakdown,
    DatasetEvaluation,
    Environment,
    EvalConfig,
    EvaluationSummary,
    ExperimentRun,
    MetricValue,
    ModelInfo,
    OverallStatistics,
    Sample,
    SampleMetadata,
    SubsetDetail,
)
from .base import BaseAdapter


class EvalScopeAdapter(BaseAdapter):
    """EvalScope framework adapter"""

    @property
    def framework_name(self) -> str:
        return "evalscope"

    def validate(self, source_path: Path) -> bool:
        """Check if directory is a valid evalscope output"""
        source_path = Path(source_path)
        # Must have configs and reports directories
        required_dirs = ["configs", "reports"]
        return all((source_path / d).exists() for d in required_dirs)

    def _generate_run_id(self, timestamp: str, model_name: str) -> str:
        """Generate unique run_id"""
        model_hash = hashlib.md5(model_name.encode()).hexdigest()[:8]
        return f"run_{timestamp}_{model_hash}"

    def _parse_log_times(self, logs_dir: Path) -> tuple:
        """Parse start and end times from log file"""
        log_file = logs_dir / "eval_log.log"
        start_time = None
        end_time = None

        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                time_pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"

                if lines:
                    match = re.search(time_pattern, lines[0])
                    if match:
                        start_time = (
                            datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").isoformat() + "Z"
                        )

                    match = re.search(time_pattern, lines[-1])
                    if match:
                        end_time = (
                            datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").isoformat() + "Z"
                        )
            except Exception:
                pass

        return start_time, end_time

    def _find_config_file(self, source_path: Path) -> Optional[Path]:
        """Find the task config file"""
        config_files = list(source_path.glob("configs/task_config_*.yaml"))
        if config_files:
            return config_files[0]
        # Fallback: any yaml file in configs
        config_files = list(source_path.glob("configs/*.yaml"))
        return config_files[0] if config_files else None

    def extract_run_meta(self, source_path: Path) -> ExperimentRun:
        """Extract run metadata from evalscope output"""
        source_path = Path(source_path)

        # Find and read config file
        config_file = self._find_config_file(source_path)
        if not config_file:
            raise FileNotFoundError(f"No config file found in {source_path}/configs/")

        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Extract timestamp from directory name
        timestamp = source_path.name

        # Parse log times
        start_time, end_time = self._parse_log_times(source_path / "logs")

        # Calculate duration
        duration_seconds = None
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.rstrip("Z"))
                end_dt = datetime.fromisoformat(end_time.rstrip("Z"))
                duration_seconds = (end_dt - start_dt).total_seconds()
            except Exception:
                pass

        # Extract model info (handle different config formats)
        # config.model can be a string (model name) or dict (model config)
        model_config = config.get("model")
        if isinstance(model_config, str):
            # model is a string, use model_id from config if available
            model_name = config.get("model_id", model_config)
            model_revision = "master"
            model_params = {}
        elif isinstance(model_config, dict):
            # model is a dict with detailed config
            model_name = model_config.get("model_id", model_config.get("model", "unknown"))
            model_revision = model_config.get("model_revision", model_config.get("revision", "master"))
            model_params = {
                "precision": model_config.get("precision"),
                "device_map": model_config.get("device_map"),
            }
        else:
            # Fallback: try model_id from top-level config
            model_name = config.get("model_id", "unknown")
            model_revision = "master"
            model_params = {}

        model_info = ModelInfo(
            name=model_name,
            revision=model_revision,
            type=config.get("eval_type", "checkpoint"),
            parameters=model_params,
        )

        # Extract eval config
        eval_config = EvalConfig(
            eval_batch_size=config.get("eval_batch_size", 1),
            seed=config.get("seed"),
            limit=config.get("limit"),
            generation_config=config.get("generation_config", {}),
        )

        # Extract environment info
        environment = Environment(
            framework="evalscope",
            framework_version=config.get("evalscope_version"),
        )

        # Get datasets from config or scan reports directory
        datasets = config.get("datasets", [])
        if not datasets:
            # Scan reports directory for dataset names
            reports_dir = source_path / "reports"
            if reports_dir.exists():
                for report_file in reports_dir.rglob("*.json"):
                    try:
                        with open(report_file, "r", encoding="utf-8") as f:
                            report = json.load(f)
                        if "dataset_name" in report:
                            datasets.append(report["dataset_name"])
                    except Exception:
                        pass

        # Generate run_id
        run_id = self._generate_run_id(timestamp, model_name)

        # Use current time as fallback
        now = datetime.now().isoformat() + "Z"

        return ExperimentRun(
            run_id=run_id,
            timestamp=timestamp,
            start_time=start_time or now,
            end_time=end_time,
            duration_seconds=duration_seconds,
            model=model_info,
            datasets=datasets,
            config=eval_config,
            status="completed",
            tags=[],
            environment=environment,
            metadata={
                "evalscope": {
                    "work_dir": str(source_path),
                    "config_file": config_file.name,
                }
            },
        )

    def extract_eval_summary(self, source_path: Path) -> EvaluationSummary:
        """Extract evaluation summary from evalscope output"""
        source_path = Path(source_path)
        reports_dir = source_path / "reports"

        datasets = []
        total_samples = 0
        total_score = 0.0

        # Iterate all report files
        for report_file in reports_dir.rglob("*.json"):
            try:
                with open(report_file, "r", encoding="utf-8") as f:
                    report = json.load(f)
            except Exception:
                continue

            # Extract metrics
            metrics = {}
            for metric in report.get("metrics", []):
                metrics[metric["name"]] = MetricValue(
                    score=metric["score"],
                    macro_score=metric.get("macro_score"),
                    num_samples=metric["num"],
                )

            # Extract categories
            categories = []
            if report.get("metrics"):
                primary_metric = report["metrics"][0]
                for cat in primary_metric.get("categories", []):
                    subsets = [
                        SubsetDetail(name=s["name"], score=s["score"], num=s["num"])
                        for s in cat.get("subsets", [])
                    ]
                    categories.append(
                        CategoryBreakdown(
                            name=cat["name"],
                            score=cat["score"],
                            macro_score=cat.get("macro_score"),
                            num_samples=cat["num"],
                            subsets=subsets,
                        )
                    )

            dataset_eval = DatasetEvaluation(
                dataset=report["dataset_name"],
                dataset_pretty_name=report.get("dataset_pretty_name"),
                dataset_description=report.get("dataset_description"),
                metrics=metrics,
                overall_score=report["score"],
                categories=categories,
            )
            datasets.append(dataset_eval)

            # Accumulate statistics
            if metrics:
                first_metric = list(metrics.values())[0]
                total_samples += first_metric.num_samples
            total_score += report["score"]

        # Calculate overall statistics
        avg_score = total_score / len(datasets) if datasets else 0.0

        # Get run_id
        run_meta = self.extract_run_meta(source_path)

        return EvaluationSummary(
            run_id=run_meta.run_id,
            datasets=datasets,
            overall=OverallStatistics(
                avg_score=avg_score,
                total_samples=total_samples,
                total_datasets=len(datasets),
            ),
        )

    def extract_samples(
        self,
        source_path: Path,
        dataset: str,
        limit: int = 100,
    ) -> List[Sample]:
        """Extract sample data from evalscope output"""
        source_path = Path(source_path)
        samples = []

        # Find prediction and review files
        # Try exact match first, then pattern match (e.g., gsm8k_main.jsonl)
        pred_files = list(source_path.glob(f"predictions/*/{dataset}.jsonl"))
        if not pred_files:
            pred_files = list(source_path.glob(f"predictions/*/{dataset}_*.jsonl"))

        review_files = list(source_path.glob(f"reviews/*/{dataset}.jsonl"))
        if not review_files:
            review_files = list(source_path.glob(f"reviews/*/{dataset}_*.jsonl"))

        if not pred_files:
            return samples

        # Read predictions
        predictions = []
        try:
            with open(pred_files[0], "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        predictions.append(json.loads(line))
        except Exception:
            return samples

        # Read reviews
        reviews_dict = {}
        if review_files:
            try:
                with open(review_files[0], "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            review = json.loads(line)
                            # Try different ID field names
                            review_id = review.get("index", review.get("id", review.get("sample_id")))
                            reviews_dict[review_id] = review
            except Exception:
                pass

        # Merge data - handle different evalscope output formats
        for pred in predictions[:limit]:
            # Get sample ID from 'index', 'id', or 'sample_id'
            sample_id = pred.get("index", pred.get("id", pred.get("sample_id", 0)))
            review = reviews_dict.get(sample_id, {})

            # Extract input (from review or prediction)
            input_text = review.get("input", "")
            if not input_text:
                # Try to get from prediction file
                input_text = pred.get("input", "")

            # Extract target (from review or prediction metadata)
            target = review.get("target", "")
            if not target:
                target = pred.get("metadata", {}).get("reasoning", "")

            # Extract prediction (model output)
            prediction = ""
            if "messages" in pred and pred["messages"]:
                prediction = pred["messages"][0].get("content", "")
            elif "model_output" in pred:
                choices = pred["model_output"].get("choices", [])
                if choices:
                    prediction = choices[0].get("message", {}).get("content", "")
            else:
                prediction = pred.get("prediction", "")

            # Build scores from review
            scores = {}
            extracted_prediction = None
            sample_score = review.get("sample_score", {})
            if sample_score:
                score_value = sample_score.get("score", {}).get("value", {})
                if isinstance(score_value, dict):
                    scores = {k: float(v) for k, v in score_value.items() if isinstance(v, (int, float))}
                # Extract the extracted_prediction field
                extracted_pred = sample_score.get("score", {}).get("extracted_prediction")
                if extracted_pred is not None:
                    extracted_prediction = str(extracted_pred)
                    # Fallback: use as prediction if prediction is empty
                    if not prediction:
                        prediction = extracted_prediction

            # Fallback to old format
            if not scores:
                scores = review.get("sample_scores", {})

            # Determine correctness - check if any score value equals 1.0
            # Works for acc, accuracy, exact_match, pass@1, etc.
            is_correct = None
            if scores:
                # Check first score value (primary metric)
                first_score = next(iter(scores.values()), None)
                if first_score is not None:
                    is_correct = abs(float(first_score) - 1.0) < 1e-9

            # Build metadata
            sample_metadata_raw = review.get("sample_score", {}).get("sample_metadata", {})
            metadata = SampleMetadata(
                category=pred.get("metadata", {}).get("category"),
                subset=pred.get("metadata", {}).get("subset"),
                judge_type=sample_metadata_raw.get("judge_type"),
            )

            sample = Sample(
                id=sample_id,
                input=input_text,
                target=target,
                prediction=prediction,
                extracted_prediction=extracted_prediction,
                choices=pred.get("choices"),
                scores=scores,
                is_correct=is_correct,
                metadata=metadata,
            )
            samples.append(sample)

        return samples
