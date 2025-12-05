"""
Storage Backend Factory

Creates storage backend instances based on mode.
"""

from typing import Optional

from .base import StorageBackend


def get_storage(
    mode: str = "single",
    outputs_dir: str = "./outputs",
    data_dir: str = ".viewer",
) -> StorageBackend:
    """
    Get storage backend based on mode

    Args:
        mode: Storage mode ('single' or 'team')
        outputs_dir: EvalScope outputs directory (for single mode)
        data_dir: Data directory for viewer storage

    Returns:
        StorageBackend instance
    """
    if mode == "single":
        from .duckdb import SingleModeStorage

        return SingleModeStorage(outputs_dir=outputs_dir, data_dir=data_dir)
    elif mode == "team":
        # Team mode will be implemented later
        raise NotImplementedError("Team mode is not yet implemented")
    else:
        raise ValueError(f"Unknown storage mode: {mode}. Available: single, team")
