"""
Base Adapter Interface

Defines the interface that all framework adapters must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from evalscope.viewer.protocol.models import (
    ExperimentRun,
    EvaluationSummary,
    Sample,
)


class BaseAdapter(ABC):
    """Base class for evaluation framework adapters"""

    @property
    @abstractmethod
    def framework_name(self) -> str:
        """Return the framework name"""
        pass

    @abstractmethod
    def validate(self, source_path: Path) -> bool:
        """
        Validate if the directory is a valid output for this framework

        Args:
            source_path: Evaluation output directory

        Returns:
            True if the directory is a valid output for this framework
        """
        pass

    @abstractmethod
    def extract_run_meta(self, source_path: Path) -> ExperimentRun:
        """
        Extract run metadata

        Args:
            source_path: Evaluation output directory

        Returns:
            ExperimentRun object
        """
        pass

    @abstractmethod
    def extract_eval_summary(self, source_path: Path) -> EvaluationSummary:
        """
        Extract evaluation summary

        Args:
            source_path: Evaluation output directory

        Returns:
            EvaluationSummary object
        """
        pass

    @abstractmethod
    def extract_samples(
        self,
        source_path: Path,
        dataset: str,
        limit: int = 100,
    ) -> List[Sample]:
        """
        Extract sample data

        Args:
            source_path: Evaluation output directory
            dataset: Dataset name
            limit: Maximum number of samples to extract

        Returns:
            List of Sample objects
        """
        pass

    def extract_all_samples(
        self,
        source_path: Path,
        datasets: List[str],
        limit: int = 100,
    ) -> Dict[str, List[Sample]]:
        """
        Extract samples for all datasets

        Args:
            source_path: Evaluation output directory
            datasets: List of dataset names
            limit: Maximum number of samples per dataset

        Returns:
            Dictionary mapping dataset name to list of samples
        """
        result = {}
        for dataset in datasets:
            samples = self.extract_samples(source_path, dataset, limit)
            if samples:
                result[dataset] = samples
        return result
