"""CLI commands for installation and maintenance."""

import json
import subprocess
import sys

from pathlib import Path

from ..config.loader import get_config_path, load_config_file
from ..utils.settings import (
    configure_statusline,
    get_settings_path,
    read_settings,
    remove_statusline,
)


def cmd_install(force: bool = False) -> int:
    """Configure Claude Code to use claude-statusline.

    Args:
        force: If True, skip confirmation prompt for existing config

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    settings_path = get_settings_path()
    settings = read_settings()

    print(f"Configuring Claude Code at {settings_path}...")

    if "statusLine" in settings and not force:
        existing = settings["statusLine"]
        new_config = {
            "type": "command",
            "command": "claude-statusline",
            "padding": 0,
        }

        print("\nExisting statusLine configuration detected:\n")
        print("  Current:")
        for line in json.dumps(existing, indent=2).split("\n"):
            print(f"    {line}")
        print("\n  New:")
        for line in json.dumps(new_config, indent=2).split("\n"):
            print(f"    {line}")
        print("\nA backup will be created before making changes.")

        try:
            response = input("Proceed? [y/N]: ").strip().lower()
            if response not in ("y", "yes"):
                print("Aborted.")
                return 1
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return 1

    success, message = configure_statusline()

    if success:
        print(f"✓ {message}")
        print("\nNext steps:")
        print("1. Restart Claude Code or start a new session")
        print("2. The statusline should appear automatically")
        print(f"3. Customize via {get_config_path()}")
        return 0

    print(f"✗ {message}", file=sys.stderr)
    return 1


def cmd_uninstall() -> int:
    """Remove claude-statusline from Claude Code configuration.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    settings_path = get_settings_path()

    print(f"Removing statusLine configuration from {settings_path}...")

    success, message = remove_statusline()

    if success:
        print(f"✓ {message}")
        print("\nNote: This only removes the statusLine configuration.")
        print("To uninstall the package, run: uv tool uninstall claude-code-statusline")
        print("                          or: pipx uninstall claude-code-statusline")
        return 0

    print(f"✗ {message}", file=sys.stderr)
    return 1


def cmd_doctor() -> int:
    """Verify installation health.

    Returns:
        Exit code (0 if healthy, 1 if issues found)
    """
    from .. import __version__

    print(f"claude-statusline v{__version__}")
    print("\nChecking installation...\n")

    issues = 0

    settings_path = get_settings_path()
    print(f"[1/4] Checking settings.json at {settings_path}")

    if not settings_path.exists():
        print("      ⚠ settings.json not found (Claude Code will create it)")
    else:
        try:
            with open(settings_path, encoding="utf-8") as f:
                settings = json.load(f)

            if "statusLine" not in settings:
                print("      ⚠ No statusLine configuration found")
                print("      → Run 'claude-statusline install' to configure")
                issues += 1
            else:
                statusline_config = settings["statusLine"]
                expected_command = "claude-statusline"
                actual_command = statusline_config.get("command", "")

                if expected_command in actual_command:
                    print("      ✓ statusLine configured correctly")
                else:
                    print(f"      ⚠ Unexpected command: {actual_command}")
                    print(f"      → Expected: {expected_command}")
                    issues += 1

        except (json.JSONDecodeError, OSError) as e:
            print(f"      ✗ Failed to read settings.json: {e}")
            issues += 1

    config_path = get_config_path()
    print(f"\n[2/4] Checking config file at {config_path}")

    if not config_path.exists():
        print("      ⓘ Config file not found (will use defaults)")
    else:
        try:
            load_config_file()
            print("      ✓ Config file is valid")
        except Exception as e:
            print(f"      ✗ Config file has errors: {e}")
            issues += 1

    print("\n[3/4] Testing statusline execution")

    test_input = json.dumps(
        {
            "workspace": {"current_dir": "/test"},
            "transcript_path": "",
            "model": {"id": "test", "display_name": "Test Model"},
            "cost": {},
            "version": "test",
        }
    )

    try:
        result = subprocess.run(
            ["claude-statusline"],
            input=test_input,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout:
            print("      ✓ Statusline executes successfully")
        else:
            print(f"      ✗ Execution failed (exit code: {result.returncode})")
            if result.stderr:
                print(f"      → Error: {result.stderr}")
            issues += 1

    except FileNotFoundError:
        print("      ✗ claude-statusline command not found")
        print("      → Install with: uv tool install claude-code-statusline")
        print("                  or: pipx install claude-code-statusline")
        issues += 1
    except subprocess.TimeoutExpired:
        print("      ✗ Execution timed out")
        issues += 1
    except Exception as e:
        print(f"      ✗ Execution error: {e}")
        issues += 1

    print("\n[4/4] Checking Claude Code status")
    claude_dir = Path.home() / ".claude"
    if claude_dir.exists():
        print(f"      ✓ Claude Code directory exists at {claude_dir}")
    else:
        print(f"      ⚠ Claude Code directory not found at {claude_dir}")
        print("      → Make sure Claude Code is installed")
        issues += 1

    print("\n" + "=" * 50)

    if issues == 0:
        print("✓ All checks passed!")
        return 0

    print(f"⚠ Found {issues} issue(s)")
    return 1
