"""
Framework Adapters

Adapters for converting different evaluation framework outputs to standard protocol.
"""

from .base import BaseAdapter
from .evalscope_adapter import EvalScopeAdapter


def get_adapter(framework: str) -> BaseAdapter:
    """Get adapter by framework name"""
    adapters = {
        "evalscope": EvalScopeAdapter,
    }
    if framework not in adapters:
        raise ValueError(f"Unknown framework: {framework}. Available: {list(adapters.keys())}")
    return adapters[framework]()


__all__ = ["BaseAdapter", "EvalScopeAdapter", "get_adapter"]
