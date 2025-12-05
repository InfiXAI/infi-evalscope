"""
Standard Data Protocol Models

Framework-agnostic data models for evaluation visualization.
Based on Pydantic v2 for validation and serialization.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

# Protocol version
PROTOCOL_VERSION = "1.0"


class ModelInfo(BaseModel):
    """Model information"""

    name: str = Field(..., description="Model name or path")
    revision: Optional[str] = Field(None, description="Model version/commit hash")
    type: str = Field("unknown", description="Model type: openai_api, checkpoint, mock")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Model parameters")


class EvalConfig(BaseModel):
    """Evaluation configuration"""

    eval_batch_size: Optional[int] = None
    seed: Optional[int] = None
    limit: Optional[Union[int, float]] = None
    generation_config: Optional[Dict[str, Any]] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class Environment(BaseModel):
    """Runtime environment information"""

    framework: Optional[str] = None
    framework_version: Optional[str] = None
    python_version: Optional[str] = None
    cuda_version: Optional[str] = None
    gpu: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class ExperimentRun(BaseModel):
    """
    Experiment run metadata

    Describes a complete evaluation run including model, config, status, etc.
    """

    # Core identifiers
    run_id: str = Field(..., description="Unique run identifier: run_<timestamp>_<hash>")
    schema_version: str = Field(PROTOCOL_VERSION, description="Protocol version")

    # Time information
    timestamp: str = Field(..., description="Creation timestamp: YYYYMMDD_HHMMSS")
    start_time: str = Field(..., description="Start time (ISO 8601)")
    end_time: Optional[str] = Field(None, description="End time (ISO 8601)")
    duration_seconds: Optional[float] = Field(None, description="Duration in seconds")

    # Model and datasets
    model: ModelInfo
    datasets: List[str] = Field(..., description="List of evaluation datasets")

    # Configuration
    config: EvalConfig = Field(default_factory=EvalConfig)

    # Status
    status: str = Field("completed", description="Run status")
    tags: List[str] = Field(default_factory=list, description="User tags")
    description: Optional[str] = None

    # Environment
    environment: Environment = Field(default_factory=Environment)

    # Extension
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricValue(BaseModel):
    """Metric value"""

    score: float = Field(..., description="Micro-average score")
    macro_score: Optional[float] = Field(None, description="Macro-average score")
    num_samples: int = Field(..., description="Number of samples")
    std: Optional[float] = None
    confidence_interval: Optional[List[float]] = None


class SubsetDetail(BaseModel):
    """Subset detail"""

    name: str
    score: float
    num: int
    metrics: Optional[Dict[str, float]] = None


class CategoryBreakdown(BaseModel):
    """Category breakdown"""

    name: Union[str, List[str]] = Field(..., description="Category name, supports hierarchy")
    score: float
    macro_score: Optional[float] = None
    num_samples: int
    subsets: List[SubsetDetail] = Field(default_factory=list)
    subcategories: Optional[List["CategoryBreakdown"]] = None


class DatasetEvaluation(BaseModel):
    """Single dataset evaluation result"""

    dataset: str
    dataset_pretty_name: Optional[str] = None
    dataset_description: Optional[str] = None
    metrics: Dict[str, MetricValue]
    overall_score: float
    categories: List[CategoryBreakdown] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OverallStatistics(BaseModel):
    """Overall statistics"""

    avg_score: float
    weighted_avg_score: Optional[float] = None
    total_samples: int
    total_datasets: int
    best_dataset: Optional[str] = None
    worst_dataset: Optional[str] = None


class EvaluationSummary(BaseModel):
    """
    Evaluation summary

    Aggregated evaluation results supporting multiple datasets, metrics, and hierarchical statistics.
    """

    run_id: str
    schema_version: str = PROTOCOL_VERSION
    datasets: List[DatasetEvaluation]
    overall: OverallStatistics


class SampleMetadata(BaseModel):
    """Sample metadata"""

    category: Optional[Union[str, List[str]]] = None
    subset: Optional[str] = None
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None
    judge_type: Optional[str] = None
    judge_model: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class Sample(BaseModel):
    """
    Sample data

    Sample-level details for error analysis and badcase exploration.
    """

    id: Union[str, int]
    input: Union[str, List[Dict[str, str]]]  # String or list of messages
    target: Union[str, List[str]]
    prediction: str
    extracted_prediction: Optional[str] = Field(None, description="Extracted/parsed prediction from raw output")
    choices: Optional[List[str]] = None
    scores: Dict[str, float] = Field(default_factory=dict)
    is_correct: Optional[bool] = None
    metadata: SampleMetadata = Field(default_factory=SampleMetadata)


class RunIndexEntry(BaseModel):
    """Run index entry"""

    run_id: str
    timestamp: str
    framework: str
    model: Dict[str, str]
    datasets: List[str]
    overall_score: Optional[float]
    num_samples: int
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[float]
    status: str
    tags: List[str] = Field(default_factory=list)


# Update forward references
CategoryBreakdown.model_rebuild()
