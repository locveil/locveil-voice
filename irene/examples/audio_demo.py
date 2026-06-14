"""
Audio Demo - Demonstrate audio playback capabilities

Showcases the audio playback backends:
- SoundDevice (primary backend)
- Aplay (Linux ALSA)
- Console (debug output)
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from ..providers.audio import (
    SoundDeviceAudioProvider,
    AplayAudioProvider,
    MiniaudioAudioProvider,
    ConsoleAudioProvider
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_audio_provider(provider, test_file: Optional[Path] = None):
    """Test a single audio provider"""
    print(f"\n{'='*60}")
    print(f"🎵 Testing: {provider.get_provider_name()}")
    print(f"   Available: {await provider.is_available()}")

    if not await provider.is_available():
        print(f"   ⚠️  Provider not available - dependencies missing")
        return

    try:
        # Test device enumeration
        devices = provider.get_playback_devices()
        print(f"   📻 Available devices: {len(devices)}")
        for device in devices[:3]:  # Show first 3 devices
            print(f"      - {device.get('name', 'Unknown')} (ID: {device.get('id', 'N/A')})")
        if len(devices) > 3:
            print(f"      ... and {len(devices) - 3} more")

        # Test file playback if test file provided
        if test_file and test_file.exists():
            print(f"   🎶 Playing test file: {test_file.name}")
            await provider.play_file(test_file, volume=0.5)
        else:
            print(f"   ⚠️  No test file provided for actual playback")

        print(f"   ✅ Provider test completed successfully")

    except Exception as e:
        print(f"   ❌ Provider test failed: {e}")
        logger.exception(f"Error testing {provider.get_provider_name()}")


async def audio_provider_demo():
    """Demonstrate all audio providers"""
    print("🎵 Irene Voice Assistant - Audio Provider Demo")
    print("=" * 60)
    print()
    print("This demo showcases the audio playback backends:")
    print("1. SoundDevice - Primary high-quality backend")
    print("2. Aplay - Linux ALSA command-line")
    print("3. Miniaudio - Self-contained cross-platform streaming")
    print("4. Console - Debug output (always available)")
    print()

    # Create test audio providers with minimal config
    providers = [
        SoundDeviceAudioProvider({}),
        AplayAudioProvider({}),
        MiniaudioAudioProvider({}),
        ConsoleAudioProvider({})
    ]

    # Look for test audio file
    test_file = None
    possible_test_files = [
        Path("media/test.wav"),
        Path("test.wav"),
        Path("audio_test.wav"),
        Path("/usr/share/sounds/alsa/Front_Left.wav"),  # Common Linux test file
        Path("/System/Library/Sounds/Ping.aiff"),       # macOS test file
        Path("C:/Windows/Media/chimes.wav")              # Windows test file
    ]

    for file_path in possible_test_files:
        if file_path.exists():
            test_file = file_path
            break

    if test_file:
        print(f"📁 Using test audio file: {test_file}")
    else:
        print("📁 No test audio file found - will demonstrate capabilities without actual playback")
    print()

    # Test each provider
    for provider in providers:
        await test_audio_provider(provider, test_file)

    print(f"\n{'='*60}")
    print("🎵 Audio Provider Demo Completed")
    print()
    print("Summary:")
    print("- SoundDevice: High-quality audio with device selection")
    print("- Aplay: Linux command-line audio (no Python deps)")
    print("- Miniaudio: Self-contained streaming, no system libraries")
    print("- Console: Debug output for testing")
    print()
    print("✨ All providers implement the same AudioProvider interface")
    print("✨ Graceful fallback when dependencies missing")
    print("✨ Async operation - no blocking calls")
    print("✨ Volume control and device selection (where supported)")


async def audio_compatibility_test():
    """Test audio provider compatibility and availability"""
    print("\n🔍 Audio Provider Compatibility Report")
    print("=" * 50)

    providers = [
        ("SoundDevice", SoundDeviceAudioProvider({})),
        ("Aplay", AplayAudioProvider({})),
        ("Miniaudio", MiniaudioAudioProvider({})),
        ("Console", ConsoleAudioProvider({}))
    ]

    available_providers = []

    for name, provider in providers:
        try:
            is_available = await provider.is_available()
            status = "✅ Available" if is_available else "❌ Missing"

            print(f"{name:12} {status}")

            if is_available:
                available_providers.append(name)
        except Exception as e:
            print(f"{name:12} ❌ Error: {e}")

    print(f"\n📊 {len(available_providers)}/{len(providers)} providers available")
    print(f"Available: {', '.join(available_providers)}")

    if len(available_providers) == 0:
        print("⚠️  No audio providers available!")
        print("💡 Install audio dependencies:")
        print("   uv add 'sounddevice>=0.5.0' 'soundfile>=0.13.0' 'numpy>=1.21.0'")
    else:
        print("✅ Audio playback capabilities available")


async def main():
    """Main demo function"""
    try:
        await audio_compatibility_test()
        await audio_provider_demo()

    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logging.exception("Demo error")


if __name__ == "__main__":
    asyncio.run(main())
