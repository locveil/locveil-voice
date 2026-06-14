"""
Audio Providers - Audio playback implementation modules

This package contains audio provider implementations managed by UniversalAudioPlugin.

Available Providers:
- ConsoleAudioProvider: Console-based output for testing
- SoundDeviceAudioProvider: High-quality audio using sounddevice
- AplayAudioProvider: Linux ALSA audio using aplay
"""

from .base import AudioProvider
from .console import ConsoleAudioProvider
from .sounddevice import SoundDeviceAudioProvider
from .aplay import AplayAudioProvider

__all__ = [
    "AudioProvider",
    "ConsoleAudioProvider",
    "SoundDeviceAudioProvider",
    "AplayAudioProvider",
]
