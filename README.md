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

<img width="1734" height="400" alt="image" src="https://github.com/user-attachments/assets/60b6c88f-b223-46d1-9490-b5b447057619" />

## Project Structure

```
claude-code-status-line/
├── src/
│   └── claude_code_statusline/
│       ├── __init__.py          # Package initialization
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
│       ├── cli/                 # CLI commands
│       │   └── commands.py      # install/uninstall/doctor
│       └── utils/               # Shared utilities
├── scripts/
│   ├── install.sh               # One-liner installation
│   └── uninstall.sh             # Clean removal
└── tests/                       # Test suite
```

## Installation

### Quick Install (Recommended)

Install with a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/wpfleger96/claude-code-status-line/main/scripts/install.sh | bash
```

This will:
- Install `claude-code-statusline` using `uv` or `pipx`
- Configure Claude Code automatically
- Create a backup of existing configuration

**Requirements:** Either `uv` or `pipx`

### Manual Installation

#### Option 1: Using uv tool

```bash
uv tool install claude-code-statusline
claude-statusline install
```

#### Option 2: Using pipx

```bash
pipx install claude-code-statusline
claude-statusline install
```

### Upgrading

To upgrade to the latest version:

```bash
# If installed with uv
uv tool upgrade claude-code-statusline

# If installed with pipx
pipx upgrade claude-code-statusline
```

### Uninstalling

To uninstall:

```bash
# Quick uninstall
curl -fsSL https://raw.githubusercontent.com/wpfleger96/claude-code-status-line/main/scripts/uninstall.sh | bash

# Or manually
claude-statusline uninstall
uv tool uninstall claude-code-statusline  # or: pipx uninstall claude-code-statusline
```

## CLI Commands

```bash
claude-statusline              # Output statusline (reads JSON from stdin)
claude-statusline install      # Configure Claude Code integration
claude-statusline uninstall    # Remove Claude Code configuration
claude-statusline doctor       # Verify installation health
claude-statusline --version    # Show version
```

### Health Check

Verify your installation is working correctly:

```bash
claude-statusline doctor
```

This checks:
- settings.json configuration
- Config file validity
- Statusline execution
- Claude Code directory

## Configuration

### Widget Customization

Customize your status line by creating `~/.config/claude-statusline/config.yaml`:

```yaml
version: 2
widgets:
  model:
    color: cyan
  directory:
    color: blue
  git-branch:
    color: magenta
  context-percentage:
    color: auto  # auto-colors based on usage
  cost:
    color: auto  # auto-colors based on amount
  session-clock:
    color: white
```

**Widget Options:**
- `type` (required): Widget identifier (see Available Widgets list below)
- `color` (optional): Color name or "auto" for dynamic coloring
- `bold` (optional): Make text bold (default: false)
- `metadata` (optional): Widget-specific configuration

**Color Options:** `white`, `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `dim`, `auto`, `none`

**Default Config:**
If no config file exists, all default widgets are shown with built-in defaults. Create `~/.config/claude-statusline/config.yaml` to customize colors, ordering, or disable specific widgets.

## Features

### Customizable Widget System
- **Configurable Layout**: Customize which widgets appear and in what order via `~/.config/claude-statusline/config.yaml`
- **Built-in Widgets**: 14 widgets including model, directory, git status, context, cost, session info
- **Flexible Styling**: Per-widget color customization and bold formatting
- **Automatic Fallback**: Missing config uses sensible defaults with all widgets enabled

**Available Widgets:**
- `model` - Claude model name (e.g., "Sonnet 4.5")
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
- **Primary Source**: Uses Claude Code's `context_window` field from status payload for authoritative token counts
- **Fallback Support**: Falls back to transcript parsing for older Claude Code versions or when `context_window` is unavailable
- **Actual Token Values**: Reads real token counts instead of estimating (from `context_window.current_usage` or transcript `message.usage` fields)
- **Compact-Aware**: Correctly handles `/compact` boundaries, counting only active context
- **Accurate Context Limit**: Uses `context_window.context_window_size` directly from Claude Code instead of model lookups

### Smart Context Tracking
- **Priority-Based Sources**: Prefers `context_window` payload data → transcript parsing → model lookups
- **Session Metrics**: Continues parsing transcripts for session duration and compact boundary detection
- **Backwards Compatible**: Gracefully handles missing or null `context_window` data from older Claude Code versions

### Token Calculation

#### How It Works

**Primary Method (Claude Code 2.0.70+):**
- Uses `context_window.current_usage` from Claude Code's status payload
- Calculates current context: `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`
- Uses `context_window.context_window_size` for accurate model limit
- No estimation or overhead calculation needed - values are authoritative from Claude Code

**Fallback Method (Older Versions):**
- Reads actual token counts from transcript `message.usage` fields (input_tokens + output_tokens)
- Falls back to estimation (character count ÷ 3.31) only when usage data is unavailable
- Retrieves model-specific context limits from cached API data, live fetches, or hardcoded fallbacks

#### Configuration

Token counting now uses Claude Code's authoritative `context_window` data when available. For older Claude Code versions using the fallback method, system overhead is automatically managed.

#### API Cache System

**With `context_window` (Claude Code 2.0.70+):**
- Context limits come directly from `context_window.context_window_size`
- No cache or API lookups needed - authoritative value from Claude Code

**Without `context_window` (Older Versions):**
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

## Development

### Setup

1. **Clone and install dependencies:**
   ```bash
   git clone https://github.com/wpfleger96/claude-code-status-line.git
   cd claude-code-status-line
   uv sync
   ```

2. **Configure Claude Code to use local version:**
   ```bash
   uv run claude-statusline install
   ```

### Testing Changes

```bash
# Test statusline output
echo '{"workspace": {"current_dir": "/test"}, "transcript_path": "", "model": {"id": "test", "display_name": "Test"}, "cost": {}, "version": "test"}' | uv run claude-statusline

# Run test suite
uv run pytest

# Enable debug logging
export CLAUDE_CODE_STATUSLINE_DEBUG=1
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
