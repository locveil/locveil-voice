"""
Input Manager - Manages multiple input sources

Coordinates different input sources and provides unified interface
for the core engine.
"""

import logging
from typing import List, Dict, Any, Optional, AsyncIterator, Union
from abc import ABC, abstractmethod

from ..core.metadata import EntryPointMetadata
from ..intents.models import AudioData

logger = logging.getLogger(__name__)

# Type alias for input data - can be text commands or raw audio data
InputData = Union[str, AudioData]


class ComponentNotAvailable(Exception):
    """Exception raised when a required component is not available"""
    pass


class InputSource(EntryPointMetadata, ABC):
    """
    Abstract base class for input sources.
    
    Provides async iterator interface for command streams.
    """
    
    @abstractmethod
    def listen(self) -> AsyncIterator[InputData]:
        """
        Start listening for input and yield data as it arrives.
        
        Yields:
            InputData - either text commands (str) or audio data (AudioData)
            - CLI/Web text: str
            - Microphone: AudioData
            - Web audio: Could be either
        """
        # This is an async generator method
        # Implementations should use: async def listen(self) -> AsyncIterator[InputData]:
        # with yield statements inside
        return
        yield  # This makes it an async generator
        
    @abstractmethod
    async def start_listening(self) -> None:
        """Initialize and start the input source."""
        pass
        
    @abstractmethod
    async def stop_listening(self) -> None:
        """Stop listening and clean up resources."""
        pass
        
    def is_listening(self) -> bool:
        """
        Check if currently listening for input.
        
        Returns:
            True if actively listening
        """
        return False
        
    def is_available(self) -> bool:
        """
        Check if input source is available.
        
        Returns:
            True if input source can be used
        """
        return True
        
    def get_input_type(self) -> str:
        """
        Get the type of input this source handles.
        
        Returns:
            Input type identifier (e.g., 'microphone', 'web', 'cli')
        """
        return "unknown"
        
    def get_settings(self) -> Dict[str, Any]:
        """
        Get current input settings.
        
        Returns:
            Dictionary of current settings
        """
        return {}
        
    async def configure_input(self, **settings) -> None:
        """
        Configure input source settings.
        
        Args:
            **settings: Input-specific configuration options
        """
        pass
        
    async def test_input(self) -> bool:
        """
        Test if input source is working correctly.
        
        Returns:
            True if input test was successful
        """
        return True

