# src/siren/__init__.py
"""Siren: The Infinite Honeypot with Deception Blueprints"""

from .blueprints.fake_sql import FakeSQLDatabase
from .blueprints.fake_fs import FakeFileSystem
from .sandbox import SandboxManager
from .recorder import AttackRecorder

__all__ = [
    "FakeSQLDatabase",
    "FakeFileSystem",
    "SandboxManager",
    "AttackRecorder",
]
