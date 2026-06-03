"""
Input Abstraction Layer - Multiple input source support

Provides abstraction for different input sources: microphone, web, CLI, etc.
V14 features configuration-driven input source discovery and management.
"""

from .base import InputSource          # the port (no longer imports its adapters → SCC-2 cycle broken)
from .manager import InputManager      # the orchestrator / input-layer composition point
from .cli import CLIInput
from .microphone import MicrophoneInput
from .web import WebInput

__all__ = [
    "InputManager",
    "InputSource",
    "CLIInput",
    "MicrophoneInput", 
    "WebInput"
] 