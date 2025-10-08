#!/usr/bin/env python3

import os
import sys
import time
from dataclasses import dataclass
from typing import List, Optional

from claude_code_statusline.common import (
    calculate_total_tokens,
    get_context_limit,
    parse_transcript,
)


@dataclass
class CalibrationResult:
    """Results from calibrating token counting against Claude's official measurements."""

    session_file: str = ""
    file_size_bytes: int = 0
    script_tokens: int = 0
    claude_tokens: int = 0
    discrepancy: int = 0
    discrepancy_percent: float = 0.0
    model_id: str = ""
    context_limit: int = 0
    success: bool = False
    error_message: str = ""


def debug_log(message: str) -> None:
    """Log debug messages to stdout if verbose mode is enabled."""
    if os.getenv("CALIBRATION_VERBOSE"):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}", file=sys.stderr)


def get_claude_context_tokens(session_file: str) -> Optional[int]:
    """Get token count from Claude's /context command for a session.

    Note: Claude --resume appears to be interactive-only and doesn't support
    programmatic slash command execution. This function provides instructions
    for manual token collection.
    """
    try:
        # Extract session ID from filename
        basename = os.path.basename(session_file)
        if basename.endswith(".jsonl"):
            session_id = basename[:-6]  # Remove .jsonl extension
        else:
            debug_log(f"Invalid session file format: {basename}")
            return None

        # Extract original launch directory for user instructions
        session_dir = os.path.dirname(session_file)
        project_dir_name = os.path.basename(session_dir)

        if project_dir_name.startswith("-"):
            encoded_path = project_dir_name[1:]
            # Convert encoded path back to original directory
            launch_dir = "/" + encoded_path.replace("-", "/")

            # Try to find the actual directory by testing progressively shorter paths
            # This handles cases where directory names contain hyphens (like claude-code-status-line)
            if not os.path.isdir(launch_dir):
                parts = encoded_path.split("-")
                for i in range(len(parts) - 1, 0, -1):
                    test_parts = parts[:i] + ["-".join(parts[i:])]
                    test_path = "/" + "/".join(test_parts)
                    if os.path.isdir(test_path):
                        launch_dir = test_path
                        break
                else:
                    launch_dir = "unknown directory (could not decode path)"
        else:
            launch_dir = "unknown directory (non-encoded path)"

        # Provide clear instructions for manual token collection
        print(f"\n🔍 Session {session_id} requires manual token collection:")
        print(f"   1. cd {launch_dir}")
        print(f"   2. claude --resume {session_id}")
        print("   3. Run: /context")
        print(
            "   4. Note the token count from /context output (e.g., '108k/200k tokens')"
        )
        print("   5. Enter the used tokens below:")
        print("      • Just the used count: '108k' or '108000'")
        print("      • Or paste the full output: '108k/200k tokens'")

        try:
            user_input = input(f"   Token count for {session_id}: ").strip()
            if not user_input:
                return None

            # Parse user input - handle various formats
            import re

            # Try to extract from full context output (e.g., "31k/200k tokens")
            context_match = re.match(
                r"^(\d+(?:\.\d+)?[kK]?)/\d+(?:\.\d+)?[kK]?\s+tokens?$", user_input
            )
            if context_match:
                token_str = context_match.group(1)
            else:
                # Use the input as-is (raw number or number with K suffix)
                token_str = user_input

            # Parse the token string
            if token_str.lower().endswith("k"):
                tokens = float(token_str[:-1]) * 1000
            else:
                tokens = float(token_str)

            debug_log(f"User provided token count: {tokens}")
            return int(tokens)

        except (ValueError, KeyboardInterrupt):
            debug_log("Invalid input or user cancelled")
            return None

    except Exception as e:
        debug_log(f"Error getting Claude context tokens: {e}")
        return None


def run_script_calculation(session_file: str) -> Optional[int]:
    """Run our token counting script and extract the token count."""
    try:
        transcript = parse_transcript(session_file)
        total_tokens = calculate_total_tokens(transcript)
        debug_log(f"Script calculated tokens: {total_tokens}")
        return total_tokens
    except Exception as e:
        debug_log(f"Error running script calculation: {e}")
        return None


def calibrate_session(
    session_file: str,
    model_id: str = "claude-opus-4.1",
    known_claude_tokens: Optional[int] = None,
) -> CalibrationResult:
    """Calibrate token counting for a single session file."""
    result = CalibrationResult(
        session_file=session_file,
        model_id=model_id,
        context_limit=get_context_limit(model_id),
    )

    if not os.path.isfile(session_file):
        result.error_message = f"Session file not found: {session_file}"
        return result

    result.file_size_bytes = os.path.getsize(session_file)
    debug_log(f"Calibrating {session_file} ({result.file_size_bytes} bytes)")

    # Get token count from our script
    script_tokens = run_script_calculation(session_file)
    if script_tokens is None:
        result.error_message = "Failed to get token count from script"
        return result
    result.script_tokens = script_tokens

    # Get token count from Claude's /context command or use provided value
    if known_claude_tokens is not None:
        claude_tokens = known_claude_tokens
        debug_log(f"Using provided Claude token count: {claude_tokens}")
    else:
        claude_tokens = get_claude_context_tokens(session_file)
        if claude_tokens is None:
            result.error_message = (
                "Failed to get token count from Claude /context command"
            )
            return result

    result.claude_tokens = claude_tokens

    # Calculate discrepancy
    result.discrepancy = result.claude_tokens - result.script_tokens
    if result.claude_tokens > 0:
        result.discrepancy_percent = (result.discrepancy * 100.0) / result.claude_tokens

    result.success = True
    debug_log(
        f"Calibration complete: Script={script_tokens}, Claude={claude_tokens}, Discrepancy={result.discrepancy}"
    )

    return result


def find_session_files(root_directory: str) -> List[str]:
    """Find all JSONL session files recursively in all subdirectories."""
    session_files = []

    if not os.path.isdir(root_directory):
        return session_files

    # Recursively search all subdirectories under ~/.claude/projects/
    for root, _, files in os.walk(root_directory):
        for filename in files:
            if filename.endswith(".jsonl"):
                full_path = os.path.join(root, filename)
                session_files.append(full_path)

    return sorted(session_files, key=lambda x: os.path.getmtime(x), reverse=True)


def print_calibration_report(results: List[CalibrationResult]) -> None:
    """Print a detailed calibration report."""
    print("=" * 80)
    print("TOKEN COUNTING CALIBRATION REPORT")
    print("=" * 80)
    print()

    successful_results = [r for r in results if r.success]
    failed_results = [r for r in results if not r.success]

    if not successful_results:
        print("❌ No successful calibrations to report")
        if failed_results:
            print("\nFailed calibrations:")
            for result in failed_results:
                print(
                    f"  • {os.path.basename(result.session_file)}: {result.error_message}"
                )
        return

    print(f"📊 Successfully calibrated {len(successful_results)} session(s)")
    print()

    # Individual results
    print("INDIVIDUAL RESULTS:")
    print("-" * 80)
    for result in successful_results:
        filename = os.path.basename(result.session_file)
        size_kb = result.file_size_bytes / 1024
        status = (
            "✅"
            if abs(result.discrepancy_percent) < 10
            else "⚠️"
            if abs(result.discrepancy_percent) < 25
            else "❌"
        )

        print(f"{status} {filename}")
        print(f"   File size: {size_kb:.1f} KB")
        print(f"   Script:    {result.script_tokens:,} tokens")
        print(f"   Claude:    {result.claude_tokens:,} tokens")
        print(
            f"   Difference: {result.discrepancy:+,} tokens ({result.discrepancy_percent:+.1f}%)"
        )
        print()

    # Summary statistics
    discrepancies = [r.discrepancy for r in successful_results]
    discrepancy_percentages = [r.discrepancy_percent for r in successful_results]

    avg_discrepancy = sum(discrepancies) / len(discrepancies)
    avg_discrepancy_percent = sum(discrepancy_percentages) / len(
        discrepancy_percentages
    )

    print("SUMMARY STATISTICS:")
    print("-" * 80)
    print(
        f"Average discrepancy: {avg_discrepancy:+.0f} tokens ({avg_discrepancy_percent:+.1f}%)"
    )
    print(f"Min discrepancy: {min(discrepancies):+,} tokens")
    print(f"Max discrepancy: {max(discrepancies):+,} tokens")
    print()

    # Recommendations
    print("RECOMMENDATIONS:")
    print("-" * 80)
    if abs(avg_discrepancy_percent) < 5:
        print("✅ Token counting is highly accurate (within 5%)")
    elif abs(avg_discrepancy_percent) < 15:
        print("⚠️  Token counting has moderate accuracy (within 15%)")
        if avg_discrepancy_percent > 0:
            print("   Consider reducing CHARS_PER_TOKEN ratio or system overhead")
        else:
            print("   Consider increasing CHARS_PER_TOKEN ratio or system overhead")
    else:
        print("❌ Token counting needs significant adjustment")
        if avg_discrepancy_percent > 0:
            print("   Script significantly undercounts - review token estimation logic")
        else:
            print("   Script significantly overcounts - review token estimation logic")

    # Calibration factor suggestion
    if successful_results:
        script_total = sum(r.script_tokens for r in successful_results)
        claude_total = sum(r.claude_tokens for r in successful_results)
        if script_total > 0:
            suggested_factor = claude_total / script_total
            print(f"\n💡 Suggested calibration factor: {suggested_factor:.3f}")
            print("   (Multiply script results by this factor for better accuracy)")


def main():
    """Main calibration script entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Calibrate token counting accuracy against Claude's official measurements"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Specific JSONL session files to calibrate (default: auto-discover recent sessions)",
    )
    parser.add_argument(
        "--model",
        default="claude-opus-4.1",
        help="Model ID to use for calibration (default: claude-opus-4.1)",
    )
    parser.add_argument(
        "--session-dir",
        default=os.path.expanduser("~/.claude/projects"),
        help="Directory to search for session files (default: ~/.claude/projects)",
    )
    parser.add_argument(
        "--max-sessions",
        type=int,
        default=5,
        help="Maximum number of recent sessions to calibrate (default: 5)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose debug output"
    )
    parser.add_argument(
        "--known-tokens",
        nargs="+",
        help="Known token counts for the session files (in same order as files)",
    )

    args = parser.parse_args()

    if args.verbose:
        os.environ["CALIBRATION_VERBOSE"] = "1"

    # Determine which files to calibrate
    session_files = []

    if args.files:
        # Use explicitly provided files
        session_files = args.files
    else:
        # Auto-discover session files by recursively searching all Claude Code project directories
        debug_log(f"Recursively searching for session files in {args.session_dir}")

        # Search all subdirectories under ~/.claude/projects/ since Claude Code creates
        # subdirectories based on where it was launched from (e.g., -Users-wpfleger-Development-Personal)
        session_files = find_session_files(args.session_dir)[: args.max_sessions]
        debug_log(
            f"Found {len(session_files)} total session files across all project directories"
        )

    if not session_files:
        print("❌ No session files found to calibrate", file=sys.stderr)
        print(f"   Searched in: {args.session_dir}", file=sys.stderr)
        print(
            "   Provide explicit file paths or ensure session files exist",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"🔧 Calibrating token counting with {len(session_files)} session(s)...")
    print()

    # Parse known tokens if provided
    known_tokens_list = []
    if args.known_tokens:
        for token_str in args.known_tokens:
            try:
                if token_str.lower().endswith("k"):
                    tokens = float(token_str[:-1]) * 1000
                else:
                    tokens = float(token_str)
                known_tokens_list.append(int(tokens))
            except ValueError:
                print(f"❌ Invalid token count: {token_str}", file=sys.stderr)
                sys.exit(1)

        if len(known_tokens_list) != len(session_files):
            print(
                f"❌ Number of known token counts ({len(known_tokens_list)}) doesn't match number of files ({len(session_files)})",
                file=sys.stderr,
            )
            sys.exit(1)

    # Run calibration on each session file
    results = []
    for i, session_file in enumerate(session_files):
        try:
            known_claude_tokens = known_tokens_list[i] if known_tokens_list else None
            result = calibrate_session(session_file, args.model, known_claude_tokens)
            results.append(result)

            # Show progress
            filename = os.path.basename(session_file)
            if result.success:
                print(
                    f"✅ {filename}: {result.discrepancy:+,} tokens ({result.discrepancy_percent:+.1f}%)"
                )
            else:
                print(f"❌ {filename}: {result.error_message}")

        except KeyboardInterrupt:
            print("\n⏹️  Calibration interrupted by user")
            break
        except Exception as e:
            print(f"❌ {os.path.basename(session_file)}: Unexpected error: {e}")

    print()

    # Generate report
    if results:
        print_calibration_report(results)
    else:
        print("❌ No calibration results to report")


if __name__ == "__main__":
    main()
