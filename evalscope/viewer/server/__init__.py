"""
API Server Layer

FastAPI-based server for serving viewer data.
"""

from .app import create_app

__all__ = ["create_app"]
