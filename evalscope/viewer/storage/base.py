"""
Storage Backend Abstract Interface

Defines the interface for data persistence using DuckDB + Parquet.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field


# ============================================================
# Storage Layer Schema Definitions (like TypeScript interfaces)
# ============================================================


class SampleStorageSchema(BaseModel):
    """
    Schema for sample data stored in Parquet.

    This defines the exact structure of data stored in:
    .viewer/cache/samples/{run_id}/{dataset}.parquet
    """

    run_id: str = Field(..., description="Run identifier")
    dataset: str = Field(..., description="Dataset name")
    sample_id: str = Field(..., description="Sample index/ID")
    input: str = Field(..., description="Input text (JSON string if complex)")
    target: Optional[str] = Field(None, description="Expected answer")
    prediction: Optional[str] = Field(None, description="Model raw output")
    extracted_prediction: Optional[str] = Field(None, description="Extracted answer from prediction")
    scores: Optional[str] = Field(None, description="Scores as JSON string, e.g. '{\"acc\": 1.0}'")
    is_correct: Optional[bool] = Field(None, description="Whether prediction is correct")


class SampleAPISchema(BaseModel):
    """
    Schema for sample data returned by API.

    This is the transformed format sent to frontend,
    matching frontend types.ts Sample interface.
    """

    id: Union[str, int] = Field(..., description="Sample ID")
    input: Union[str, List[Dict[str, str]]] = Field(..., description="Input text or messages")
    target: Optional[Union[str, List[str]]] = Field(None, description="Expected answer(s)")
    prediction: Optional[str] = Field(None, description="Model raw output")
    extracted_prediction: Optional[str] = Field(None, description="Extracted answer")
    scores: Dict[str, float] = Field(default_factory=dict, description="Metric scores")
    is_correct: Optional[bool] = Field(None, description="Whether prediction is correct")


class RunStorageSchema(BaseModel):
    """
    Schema for run metadata stored in Parquet.

    This defines the structure of data stored in:
    .viewer/cache/runs.parquet
    """

    run_id: str
    timestamp: str
    model_name: str
    model_type: str
    model_revision: Optional[str] = None
    datasets: List[str]
    overall_score: float
    total_samples: int
    status: str
    config: str  # JSON string
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None


class StorageBackend(ABC):
    """Abstract base class for storage backends"""

    @abstractmethod
    def sync(self, outputs_dir: str) -> int:
        """
        Sync cache from outputs directory

        Args:
            outputs_dir: EvalScope outputs directory

        Returns:
            Number of new runs cached
        """
        pass

    @abstractmethod
    def list_runs(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List all runs

        Returns:
            (runs, total): List of runs and total count
        """
        pass

    @abstractmethod
    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run metadata"""
        pass

    @abstractmethod
    def get_run_summary(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run evaluation summary"""
        pass

    @abstractmethod
    def get_samples(
        self,
        run_id: str,
        dataset: str,
        limit: int = 100,
        offset: int = 0,
        filter_correct: Optional[bool] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get sample data with pagination

        Returns:
            (samples, total): List of samples and total count
        """
        pass

    @abstractmethod
    def get_sample_stats(self, run_id: str, dataset: str) -> Dict[str, Any]:
        """Get sample statistics for a dataset"""
        pass

    @abstractmethod
    def delete_run(self, run_id: str) -> bool:
        """Delete a run and its cache"""
        pass

    @abstractmethod
    def run_exists(self, run_id: str) -> bool:
        """Check if a run exists"""
        pass

    @abstractmethod
    def get_cached_run_ids(self) -> List[str]:
        """Get list of cached run IDs"""
        pass
