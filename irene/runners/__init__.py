"""
Application Runners - Different ways to run Irene

Provides various entry points for different deployment scenarios.
Replaces legacy runva_*.py files with modern async architecture.
"""

from .cli import CLIRunner, run_cli
from .vosk_runner import VoskRunner, run_vosk
from .webapi_runner import WebAPIRunner, run_webapi

__all__ = [
    # Runner classes
    "CLIRunner",
    "VoskRunner",
    "WebAPIRunner",

    # Entry point functions
    "run_cli",
    "run_vosk",
    "run_webapi",
] 