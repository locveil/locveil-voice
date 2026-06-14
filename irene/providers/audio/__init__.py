"""
Audio Providers - Audio playback implementation modules

This package contains audio provider implementations managed by UniversalAudioPlugin.

Available Providers:
- ConsoleAudioProvider: Console-based output for testing
- SoundDeviceAudioProvider: High-quality audio using sounddevice
- AplayAudioProvider: Linux ALSA audio using aplay
- MiniaudioAudioProvider: Self-contained cross-platform streaming (no system libs)
"""

from .base import AudioProvider
from .console import ConsoleAudioProvider
from .sounddevice import SoundDeviceAudioProvider
from .aplay import AplayAudioProvider
from .miniaudio import MiniaudioAudioProvider

__all__ = [
    "AudioProvider",
    "ConsoleAudioProvider",
    "SoundDeviceAudioProvider",
    "AplayAudioProvider",
    "MiniaudioAudioProvider",
]
