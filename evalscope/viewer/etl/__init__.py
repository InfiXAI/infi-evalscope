"""
ETL (Extract, Transform, Load) Layer

Converts evaluation framework outputs to standard protocol.
"""

from .adapters import EvalScopeAdapter, get_adapter

__all__ = ["EvalScopeAdapter", "get_adapter"]
