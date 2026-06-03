#!/usr/bin/env python3
"""
Runner Migration Tool - Convert legacy runva_*.py usage to v13 runners

This tool helps users migrate from legacy runva_*.py scripts to the new
v13 runner system with modern async architecture.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple


# Legacy to v13 runner mappings
RUNNER_MAPPINGS = {
    "runva_cmdline.py": {
        "v13_runner": "irene.runners.cli",
        "v13_entry": "run_cli",
        "v13_class": "CLIRunner",
        "description": "Command line interface",
        "migration_notes": [
            "Now supports --command for single command execution",
            "Added --test-greeting for legacy compatibility", 
            "Enhanced with deployment profile options",
            "Better error handling and logging"
        ]
    },
    "runva_vosk.py": {
        "v13_runner": "irene.runners.vosk_runner", 
        "v13_entry": "run_vosk",
        "v13_class": "VoskRunner",
        "description": "VOSK speech recognition",
        "migration_notes": [
            "Async architecture for non-blocking operation",
            "Better audio device management",
            "Integrated with component system",
            "Graceful dependency checking"
        ]
    },
    "runva_webapi.py": {
        "v13_runner": "irene.runners.webapi_runner",
        "v13_entry": "run_webapi", 
        "v13_class": "WebAPIRunner",
        "description": "Web API server (FastAPI)",
        "migration_notes": [
            "Modern FastAPI instead of legacy implementation",
            "WebSocket support for real-time communication",
            "Automatic API documentation at /docs",
            "Better CORS and SSL support"
        ]
    },
    "runva_settings_manager.py": {
        "v13_runner": None,  # removed in v15 — config is edited via config-ui (TOML) or directly
        "v13_entry": None,
        "v13_class": None,
        "description": "Web-based settings manager (removed; use config-ui or edit the TOML config directly)",
        "migration_notes": [
            "The standalone settings runner was removed in v15",
            "Configuration is edited via config-ui (TOML editor) or by editing the config file",
        ]
    },
    "runva_speechrecognition.py": {
        "v13_runner": "irene.runners.cli",
        "v13_entry": "run_cli", 
        "v13_class": "CLIRunner",
        "description": "Use CLI runner with cloud recognition",
        "migration_notes": [
            "Legacy cloud recognition deprecated",
            "Use VOSK runner for offline recognition",
            "Or CLI runner with manual input"
        ]
    },
    "runva_voskrem.py": {
        "v13_runner": "irene.runners.webapi_runner",
        "v13_entry": "run_webapi",
        "v13_class": "WebAPIRunner", 
        "description": "Use Web API runner for remote access",
        "migration_notes": [
            "Remote VOSK functionality replaced by Web API",
            "Use WebSocket endpoint for real-time communication",
            "Better architecture for distributed setups"
        ]
    },
    "runva_plugin_installer.py": {
        "v13_runner": None,  # removed in v15 — plugins are intent handlers with JSON donations
        "v13_entry": None,
        "v13_class": None,
        "description": "Plugin management (settings manager removed; plugins are now intent handlers with JSON donations)",
        "migration_notes": [
            "Plugin installation integrated into settings manager",
            "Modern plugin system with interfaces",
            "Better dependency management"
        ]
    }
}


def analyze_legacy_usage(file_path: Path) -> Dict:
    """Analyze how a legacy runner was being used"""
    analysis = {
        "file_exists": file_path.exists(),
        "file_size": file_path.stat().st_size if file_path.exists() else 0,
        "estimated_usage": "unknown"
    }
    
    if file_path.exists():
        try:
            content = file_path.read_text()
            
            # Simple heuristics to determine usage pattern
            if "model" in content.lower():
                analysis["estimated_usage"] = "vosk_recognition"
            elif "fastapi" in content.lower() or "webapi" in content.lower():
                analysis["estimated_usage"] = "web_api"
            elif "gradio" in content.lower():
                analysis["estimated_usage"] = "settings_manager" 
            else:
                analysis["estimated_usage"] = "command_line"
                
        except Exception:
            pass
    
    return analysis


def generate_migration_command(legacy_file: str, analysis: Dict) -> str:
    """Generate v13 equivalent command"""
    mapping = RUNNER_MAPPINGS.get(legacy_file, {})
    
    if not mapping:
        return f"# No direct v13 equivalent for {legacy_file}"
    
    base_command = f"python -m {mapping['v13_runner']}"
    
    # Add common options based on legacy usage
    if "vosk" in legacy_file:
        base_command += " --model model --device 0"
    elif "webapi" in legacy_file:
        base_command += " --host 127.0.0.1 --port 5003"
    elif "settings" in legacy_file:
        base_command += " --host 127.0.0.1 --port 7860"
    elif "cmdline" in legacy_file:
        base_command += " --command 'привет'"
    
    return base_command


def print_migration_report(legacy_files: List[str], show_details: bool = False):
    """Print comprehensive migration report"""
    print("🔄 Legacy Runner Migration Report")
    print("=" * 60)
    print()
    
    found_files = []
    missing_files = []
    
    for legacy_file in legacy_files:
        file_path = Path(legacy_file)
        analysis = analyze_legacy_usage(file_path)
        mapping = RUNNER_MAPPINGS.get(legacy_file, {})
        
        if analysis["file_exists"]:
            found_files.append((legacy_file, analysis, mapping))
        else:
            missing_files.append(legacy_file)
    
    # Found files section
    if found_files:
        print("📋 Found Legacy Runners:")
        print("-" * 30)
        for legacy_file, analysis, mapping in found_files:
            status_icon = "✅" if mapping else "❓"
            print(f"{status_icon} {legacy_file}")
            
            if mapping:
                print(f"   📦 Replaces with: {mapping['v13_class']}")
                print(f"   📄 Description: {mapping['description']}")
                print(f"   💻 Command: {generate_migration_command(legacy_file, analysis)}")
                
                if show_details and mapping.get("migration_notes"):
                    print(f"   📝 Migration notes:")
                    for note in mapping["migration_notes"]:
                        print(f"      • {note}")
            else:
                print(f"   ❓ No direct v13 equivalent available")
            
            print()
    
    # Missing files section
    if missing_files:
        print("❌ Legacy Runners Not Found:")
        print("-" * 30)
        for legacy_file in missing_files:
            print(f"   {legacy_file} (not present in current directory)")
        print()
    
    # Migration commands summary
    if found_files:
        print("🚀 V13 Migration Commands:")
        print("-" * 30)
        for legacy_file, analysis, mapping in found_files:
            if mapping:
                command = generate_migration_command(legacy_file, analysis)
                print(f"# Instead of: python {legacy_file}")
                print(f"{command}")
                print()
    
    # General migration tips
    print("💡 General Migration Tips:")
    print("-" * 30)
    print("• All v13 runners support --help for detailed options")
    print("• Use --check-deps to verify component dependencies")
    print("• Configuration now uses TOML format instead of JSON")
    print("• Edit configuration via config-ui (TOML editor) or the config file directly")
    print("• Legacy compatibility maintained where possible")
    print()


def create_migration_script(output_file: Path):
    """Create a migration script for easy transition"""
    script_content = '''#!/bin/bash
# Irene v13 Runner Migration Script
# Auto-generated migration from legacy runva_*.py files

echo "🔄 Migrating to Irene v13 runners..."

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "💡 Consider using: uv venv && source .venv/bin/activate"
fi

# Function to run v13 command with error handling
run_v13() {
    local description="$1"
    local command="$2"
    
    echo "📦 $description"
    echo "💻 Command: $command"
    
    if command -v python >/dev/null 2>&1; then
        echo "▶️  Running..."
        $command
    else
        echo "❌ Python not found in PATH"
    fi
    echo
}

# Migration commands (customize as needed)
'''
    
    # Add migration commands for each found legacy file
    for legacy_file in RUNNER_MAPPINGS.keys():
        file_path = Path(legacy_file)
        if file_path.exists():
            mapping = RUNNER_MAPPINGS[legacy_file]
            analysis = analyze_legacy_usage(file_path)
            command = generate_migration_command(legacy_file, analysis)
            
            script_content += f'''
# Migration for {legacy_file}
run_v13 "{mapping['description']}" "{command}"
'''
    
    script_content += '''
echo "✅ Migration script completed"
echo "💡 Run individual commands as needed"
'''
    
    output_file.write_text(script_content)
    output_file.chmod(0o755)  # Make executable
    print(f"📄 Migration script created: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate from legacy runva_*.py files to v13 runners",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Analyze current directory
  %(prog)s --details                 # Show detailed migration notes
  %(prog)s --create-script migrate.sh # Create migration script
        """
    )
    
    parser.add_argument(
        "--details",
        action="store_true",
        help="Show detailed migration notes"
    )
    parser.add_argument(
        "--create-script",
        type=Path,
        help="Create executable migration script"
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=list(RUNNER_MAPPINGS.keys()),
        help="Specific legacy files to analyze"
    )
    
    args = parser.parse_args()
    
    # Print migration report
    print_migration_report(args.files, args.details)
    
    # Create migration script if requested
    if args.create_script:
        create_migration_script(args.create_script)
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 