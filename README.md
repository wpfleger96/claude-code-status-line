# Claude Code Statusline Script

[![PyPI Downloads](https://img.shields.io/pypi/dm/claude-code-statusline.svg)](https://pypi.org/project/claude-code-statusline/)
[![PyPI version](https://img.shields.io/pypi/v/claude-code-statusline.svg)](https://pypi.org/project/claude-code-statusline/)
[![Python Versions](https://img.shields.io/pypi/pyversions/claude-code-statusline.svg)](https://pypi.org/project/claude-code-statusline/)
[![CI](https://github.com/wpfleger96/claude-code-status-line/actions/workflows/ci.yml/badge.svg)](https://github.com/wpfleger96/claude-code-status-line/actions/workflows/ci.yml)
[![GitHub Contributors](https://img.shields.io/github/contributors/wpfleger96/claude-code-status-line.svg)](https://github.com/wpfleger96/claude-code-status-line/graphs/contributors)
[![Lines of Code](https://aschey.tech/tokei/github/wpfleger96/claude-code-status-line?category=code)](https://github.com/wpfleger96/claude-code-status-line)
[![License](https://img.shields.io/github/license/wpfleger96/claude-code-status-line.svg)](https://github.com/wpfleger96/claude-code-status-line/blob/main/LICENSE)

## Overview

A Python script that generates a formatted [status line](https://docs.anthropic.com/en/docs/claude-code/statusline) for Claude Code, displaying the current model, working directory, and context usage information. The script provides real-time feedback on token consumption relative to the model's context window limit.

<img width="1217" height="427" alt="image" src="https://github.com/user-attachments/assets/a5542835-f523-402c-8364-9a3efa156a04" />

## Project Structure

```
claude-code-status-line/
├── src/
│   └── claude_code_statusline/
│       ├── __init__.py          # Package initialization
│       ├── __version__.py       # Version tracking
│       ├── statusline.py        # Main statusline command
│       ├── config/              # Configuration system
│       │   ├── defaults.py      # Default widget configuration
│       │   ├── loader.py        # Config file loading
│       │   └── schema.py        # Pydantic schemas
│       ├── widgets/             # Widget system
│       │   ├── base.py          # Base widget class
│       │   ├── registry.py      # Widget registration
│       │   └── builtin/         # Built-in widgets
│       ├── parsers/             # Transcript parsing
│       │   ├── jsonl.py         # JSONL parser
│       │   └── tokens.py        # Real token counting
│       └── utils/               # Shared utilities
├── .github/workflows/
│   └── release.yml              # Automated semantic versioning
├── pyproject.toml               # Package configuration
└── README.md
```

## Requirements

- Python 3.9 or higher
- [uv](https://docs.astral.sh/uv/) for dependency management
- No installation needed (uses `uv run`)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/wpfleger96/claude-code-status-line.git
   cd claude-code-status-line
   ```

2. **Install dependencies:**
   ```bash
   uv sync --no-config
   ```

3. **Verify installation:**
   ```bash
   uv run --no-config claude-statusline --help
   ```

## Usage

Add a `statusLine` section to your `~/.claude/settings.json` file:
```json
{
  "statusLine": {
    "type": "command",
    "command": "sh -c 'cd /path/to/claude-code-status-line && uv run --no-config claude-statusline'",
    "padding": 0
  }
}
```

Replace `/path/to/claude-code-status-line` with the absolute path to where you cloned this repository (e.g., `~/Development/Personal/claude-code-status-line`).

## Configuration

### Widget Customization

Customize your status line by creating `~/.config/claude-statusline/config.yaml`:

```yaml
version: 1
lines:
  - - type: model
      color: cyan
    - type: separator
    - type: directory
      color: blue
    - type: separator
    - type: git-branch
      color: magenta
    - type: separator
    - type: context-percentage
      color: auto  # auto-colors based on usage
    - type: separator
    - type: cost
      color: auto  # auto-colors based on amount
    - type: separator
    - type: session-clock
      color: white
```

**Widget Options:**
- `type` (required): Widget identifier (see Available Widgets list below)
- `color` (optional): Color name or "auto" for dynamic coloring
- `bold` (optional): Make text bold (default: false)
- `metadata` (optional): Widget-specific configuration

**Color Options:** `white`, `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `dim`, `auto`, `none`

**Auto-Generated Config:**
If no config file exists, one is automatically created with all widgets enabled. Delete `~/.config/claude-statusline/config.yaml` to regenerate defaults.

**Stale Config Warning:**
When new widgets are added, the script warns you:
```
Warning: Config is missing widgets from defaults: session-clock.
Delete ~/.config/claude-statusline/config.yaml to regenerate with new defaults.
```

## Features

### Customizable Widget System
- **Configurable Layout**: Customize which widgets appear and in what order via `~/.config/claude-statusline/config.yaml`
- **Built-in Widgets**: 14 widgets including model, directory, git status, context, cost, session info
- **Flexible Styling**: Per-widget color customization and bold formatting
- **Automatic Fallback**: Missing config uses sensible defaults with all widgets enabled
- **Stale Config Detection**: Warns when config is missing newly-added widgets

**Available Widgets:**
- `model` - Claude model name (e.g., "Sonnet 4.5")
- `subscription` - Subscription type (Pro/Max) or API usage indicator
- `directory` - Current working directory
- `git-branch` - Active git branch name
- `git-changes` - Staged/unstaged changes count
- `git-worktree` - Git worktree name (if applicable)
- `context-percentage` - Context usage with progress bar
- `context-tokens` - Token count (current/limit)
- `cost` - Session cost in USD
- `lines-added` - Lines added in session
- `lines-removed` - Lines removed in session
- `lines-changed` - Combined added/removed
- `session-id` - Claude Code session UUID
- `session-clock` - Elapsed session time
- `separator` - Visual separator (default: "|")

### Real Token Counting
- **Actual Token Values**: Reads real token counts from Claude Code transcript files instead of estimating
- **Message-Level Accuracy**: Extracts exact `input_tokens` and `output_tokens` from message usage data
- **Compact-Aware**: Correctly handles `/compact` boundaries, counting only active context
- **System Overhead**: Automatically accounts for Claude Code's system prompt and tool definitions (21400 tokens default)

### Smart Context Tracking
- **JSONL Transcript Parsing**: Analyzes Claude Code's session files to find compact boundaries and count only relevant tokens
- **Fallback Compatibility**: Falls back to simple file size calculation for non-JSONL transcript formats
- **Calibration Tool**: Includes `calibrate_token_counting.py` to validate and improve accuracy

### Token Calculation

#### How It Works
- Reads actual token counts from transcript `message.usage` fields (input_tokens + output_tokens)
- Falls back to estimation (character count ÷ 3.31) only when usage data is unavailable
- Adds system overhead tokens (21400 by default) for Claude Code's system prompt, tools, and memory
- Retrieves model-specific context limits from cached API data, live fetches, or hardcoded fallbacks

#### Configuration
Customize token calculations via environment variables:

```bash
# System overhead (default: 21400 tokens)
export CLAUDE_CODE_SYSTEM_OVERHEAD=20000
```

#### API Cache System
Context limits are retrieved from:
1. **Local Cache**: `/tmp/claude_code_model_data_cache.json` (1-week TTL)
2. **Live API**: [LiteLLM Model Database](https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json)
3. **Fallback**: Hardcoded model limits

Cache benefits: Faster rendering, reduced network dependency, automatic refresh.

### Display Features

**Progress Bar**: 10-segment bar using filled (●) and empty (○) circles

**Context Usage Colors**:
| Color | Usage | Condition |
|-------|-------|-----------|
| Grey  | 0%    | No active transcript |
| Green | <50%  | Low usage |
| Yellow| 50-79%| Medium usage |
| Red   | 80%+  | High usage |

**Cost Tracking Colors**:
| Color | Cost Range |
|-------|------------|
| Grey  | $0.00 (exactly zero) |
| Green | $0.01 - $4.99 |
| Yellow| $5.00 - $9.99 |
| Red   | $10.00+ |

**Line Change Colors**:
| Metric | Zero (Grey) | Non-Zero |
|--------|-------------|----------|
| Lines Added | 0 lines | Green (>0) |
| Lines Removed | 0 lines | Red (>0) |

**Git Integration**:
- `git-branch`: Shows current branch with fallback text when not in a repo
- `git-changes`: Displays staged/unstaged changes (e.g., "+5 ~3 -2")
- `git-worktree`: Shows worktree name if working in a linked worktree

**Session Tracking**:
- `session-id`: Complete Claude Code session UUID for file matching
- `session-clock`: Elapsed session time (e.g., "Elapsed: 2hr 15m")

Widget rendering is intelligent - widgets with no data hide automatically, and orphaned separators are removed.

---

## Example Outputs

**Default configuration with git integration:**
```
Sonnet 4.5 | claude-code-status-line | main | ●●●●●●○○○○ 60% (120K/200K tokens) | Cost: $2.50 USD | +150 ~25 -10 | Session: 852d18cc | Elapsed: 2hr 15m
```

**High context usage:**
```
Sonnet 4.5 | my-project | feature/auth | ●●●●●●●●●○ 90% (180K/200K tokens) | Cost: $8.75 USD | +500 ~50 -100 | Session: a3f7b2cd | Elapsed: 45m
```

**Low usage (widgets hide when zero):**
```
Sonnet 4.5 | my-project | main | ○○○○○○○○○○ 0% (783/200K tokens) | Cost: $0.00 USD | Session: d6994160 | Elapsed: 5m
```

**No active transcript:**
```
Sonnet 4.5 | my-project | develop | No active transcript | Cost: $0.00 USD | Session: 7b89c123 | Elapsed: 1m
```

---

## Debug Logging

For debugging and understanding how the script processes Claude Code sessions, you can enable detailed logging:

### Enable Debug Mode
```bash
export CLAUDE_CODE_STATUSLINE_DEBUG=1
```

### Log Files Location
Debug logs are written to **per-session files** in the `logs/` directory:

- **Session-specific logs**: `logs/statusline_debug_<session_id>.log`
- **Examples**:
  - `logs/statusline_debug_d6994160-5c39-4ecf-8922-65a36b984ec5.log` (UUID-based sessions)
  - `logs/statusline_debug_unknown.log` (fallback for edge cases)

### Debug Features
- **Session metadata**: Model ID, version, working directory logging
- **Token analysis**: Per-message-type breakdown with percentages and field contributions
- **Compact detection**: Precise `/compact` boundary locations with token reduction stats
- **Per-session logs**: Isolated debug files (`logs/statusline_debug_<session_id>.log`)
- **Error handling**: Comprehensive parsing error logging and fallback behavior

### Example Debug Output
```
[2025-09-26 15:03:09] === SESSION METADATA ===
[2025-09-26 15:03:09] Model: claude-opus-4-1-20250805 (Opus 4.1) | Version: 0.8.5
[2025-09-26 15:03:09] Found compact boundary at line 148, using content from line 149 onwards
[2025-09-26 15:03:09] Token Breakdown: assistant: 17,816 tokens (57%) | user: 13,275 tokens (42%)
[2025-09-26 15:03:09] Total: Conversation=31,092, System=15,400, Reserved=45,000 → 91,492 tokens
[2025-09-26 15:03:09] Token reduction from compaction: 146,759 tokens saved
```

**Note**: Debug logs are automatically excluded from git via `.gitignore` to prevent accidental commits of session data.

---

## Token Counting Calibration Tool

The project includes `claude-calibrate`, a command-line tool to verify and improve token counting accuracy against Claude's official measurements.

### Purpose
- Compare script calculations against Claude's official `/context` command output
- Identify discrepancies and suggest calibration factors
- Validate token counting accuracy when new Claude Code versions are released

### Usage

#### Semi-Automated Mode (Default)
```bash
uv run --no-config claude-calibrate session1.jsonl session2.jsonl --verbose
```
The tool provides precise instructions for resuming each session and prompts you to enter the official token counts.

#### Manual Override Mode
```bash
uv run --no-config claude-calibrate session1.jsonl session2.jsonl \
  --known-tokens 17.5k 68k --verbose
```
Provide known token counts to skip automatic session resumption (useful for sessions that can't be resumed).

#### Auto-Discovery Mode
```bash
uv run --no-config claude-calibrate --max-sessions 3 --verbose
```
Automatically finds recent session files from all Claude Code project directories and provides instructions for manual calibration.

### Example Calibration Report
```
📊 Successfully calibrated 2 session(s)

INDIVIDUAL RESULTS:
❌ session1.jsonl: Script 46,520 vs Claude 68,000 tokens (+31.6% difference)
✅ session2.jsonl: Script 17,470 vs Claude 17,500 tokens (+0.2% difference)

SUMMARY:
Average discrepancy: +15.9% | Suggested calibration factor: 1.231
⚠️  Token counting has moderate accuracy - consider adjusting CHARS_PER_TOKEN ratio
```

### Features
- **Auto-discovery**: Finds recent sessions from all Claude Code project directories
- **Semi-automated**: Provides precise resumption instructions for manual token collection
- **Directory decoding**: Handles hyphenated paths (`-Users-name-Project` → `/Users/name/Project`)
- **Flexible input**: Accepts raw numbers, K-suffixed values, or full `/context` output
- **Accuracy validation**: Compares against Claude's official measurements
- **Calibration recommendations**: Suggests specific improvements and correction factors
- **uv compatibility**: Uses `uv run` for portable execution across Python environments

---

## Development

### Package Structure

The project uses a modern `src/` layout following Python packaging best practices:

- **`src/claude_code_statusline/`**: Main package directory
  - Enables proper import resolution
  - Makes the package PyPI-ready
  - Prevents accidental imports from source during development

### Local Development

1. **Clone and setup:**
   ```bash
   git clone https://github.com/wpfleger96/claude-code-status-line.git
   cd claude-code-status-line
   uv sync --no-config
   ```

2. **Make changes to source files:**
   - Edit files in `src/claude_code_statusline/`
   - Changes are automatically reflected when using `uv run`

3. **Test your changes:**
   ```bash
   # Test statusline
   echo '{"workspace": {"current_dir": "/test"}, "transcript_path": "", "model": {"id": "test", "display_name": "Test"}, "cost": {}, "version": "test"}' | uv run --no-config claude-statusline

   # Test calibration
   uv run --no-config claude-calibrate --help
   ```

4. **Debug mode:**
   ```bash
   export CLAUDE_CODE_STATUSLINE_DEBUG=1
   # Debug logs will be written to logs/ directory
   ```

### Releases

This project uses [semantic-release](https://python-semantic-release.readthedocs.io/) for automated versioning and releases.

**Commit Message Format:**
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat:` New feature (minor version bump)
- `fix:` Bug fix (patch version bump)
- `docs:` Documentation changes (patch version bump)
- `chore:` Maintenance tasks (patch version bump)
- `refactor:` Code refactoring (patch version bump)
- `BREAKING CHANGE:` in footer (major version bump)

**Example:**
```bash
git commit -m "feat: add support for new Claude models"
git commit -m "fix: correct token calculation for edge cases"
```

**Release Process:**
1. Push commits to `main` branch
2. GitHub Actions automatically:
   - Analyzes commit messages
   - Determines version bump
   - Updates version in files
   - Generates CHANGELOG.md
   - Creates GitHub release and tag
   - Commits changes back to repository

### Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Use conventional commit messages
4. Push to your branch
5. Open a Pull Request

For bug reports or feature requests, please [open an issue](https://github.com/wpfleger96/claude-code-status-line/issues).
