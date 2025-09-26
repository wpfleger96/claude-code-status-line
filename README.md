# Claude Code Statusline Script

## Overview

A Python script that generates a formatted [status line](https://docs.anthropic.com/en/docs/claude-code/statusline) for Claude Code, displaying the current model, working directory, and context usage information. The script provides real-time feedback on token consumption relative to the model's context window limit.

<img width="1217" height="427" alt="image" src="https://github.com/user-attachments/assets/a5542835-f523-402c-8364-9a3efa156a04" />

## Requirements

- Python 3.6 or higher
- No external dependencies (uses Python standard library only)
- Script must be executable (`chmod +x statusline-with-context.py`)

## Features

### Smart Context Tracking
- **Compact-Aware Token Counting**: Accurately counts only active context after Claude Code's `/compact` command, ignoring compacted history
- **JSONL Transcript Parsing**: Analyzes Claude Code's session files to find compact boundaries and count only relevant tokens
- **Fallback Compatibility**: Falls back to simple file size calculation for non-JSONL transcript formats

### Token Calculation
- Estimates tokens by dividing character count by 4 (industry standard approximation)
- Retrieves model-specific context limits from:
  1. Cached API data (refreshed weekly)
  2. Live API fetch from LiteLLM repository ([link](https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json))
  3. Hardcoded fallback values

### Visual Indicators
- **Progress Bar**: 10-segment bar using filled (●) and empty (○) circles
- **Color Coding**:
  - Context usage:
    - Grey: No active transcript or empty transcript
    - Green: < 50% usage
    - Yellow: 50-79% usage
    - Red: >= 80% usage
  - Cost tracking:
    - Grey: $0.00 USD (no cost incurred yet)
    - Green: $0.01-$4.99 USD
    - Yellow: $5.00-$9.99 USD
    - Red: >= $10.00 USD

### Cost Tracking
- Always displays total cost in USD for the current session (starts at $0.00)
- Always shows lines added and lines removed for the session (starts at +0/-0)
- Uses grey color for zero values, green for lines added (>0), red for lines removed (>0)
- Cost information appears after context usage

## Usage

Add a `statusLine` section to your `~/.claude/settings.json` file with the following configuration:
```json
{
  "statusLine": {
    "type": "command",
    "command": "/full/path/to/statusline-with-context.py",
    "padding": 0
  }
}
```

Replace `/full/path/to/` with the absolute path to where you downloaded this script.

## Example Outputs

```
Opus 4.1 | wpfleger-ai-tools | Context: ●●●●●●○○○○ 60% (120K/200K tokens) | Cost: $2.50 USD | +150 lines added | -25 lines removed
```

```
Opus 4.1 | wpfleger-ai-tools | Context: ●●●●●●●●●○ 90% (180K/200K tokens) | Cost: $8.75 USD | +500 lines added | -100 lines removed
```

```
Opus 4.1 | wpfleger-ai-tools | Context: ○○○○○○○○○○ 0% (783/200K tokens) | Cost: $0.00 USD | +0 lines added | -0 lines removed
```

```
Opus 4.1 | wpfleger-ai-tools | Context: No active transcript | Cost: $0.00 USD | +0 lines added | -0 lines removed
```

## Debug Logging (Power Users)

For debugging and understanding how the script processes Claude Code sessions, you can enable detailed logging:

### Enable Debug Mode
```bash
export CLAUDE_CODE_STATUSLINE_DEBUG=1
```

### Log Files Location
Debug logs are written to a single file in the `logs/` directory:

- **All logs**: `logs/statusline_debug.log` (includes session ID prefixes when available)

### What Gets Logged
- **Compact boundary detection**: Location of `/compact` markers in transcript
- **Token calculations**: Before/after comparison showing token reduction from compaction
- **Session information**: Session ID, total lines, active context analysis
- **Error handling**: File parsing errors and fallback behavior

### Example Debug Output
```
[2025-09-25 13:43:42] Parsing transcript: claude_code_example_session.jsonl (8855 chars)
[2025-09-25 13:43:42] [ddae8b71-a770-4e55-8246-50dc7280b9cd] Found compact boundary at line 5
[2025-09-25 13:43:42] [ddae8b71-a770-4e55-8246-50dc7280b9cd] Session: ddae8b71-a770-4e55-8246-50dc7280b9cd, boundaries: 1
[2025-09-25 13:43:42] [ddae8b71-a770-4e55-8246-50dc7280b9cd] Active chars: 3631/8855
[2025-09-25 13:43:42] [ddae8b71-a770-4e55-8246-50dc7280b9cd] Token reduction: 1306
[2025-09-25 13:43:57] Parsing transcript: statusline-with-context.py (12195 chars)
[2025-09-25 13:43:57] File is not JSONL format, using fallback
```

### Debug Mode Benefits
- **Verify compact detection**: Confirm the script correctly identifies when `/compact` has been used
- **Compare token calculations**: See the difference between naive file-size counting vs smart context-aware counting
- **Session correlation**: Logs include session ID prefixes for easy correlation with Claude Code sessions
- **Troubleshoot issues**: Debug transcript parsing problems or unexpected token counts
- **Single file**: All debug information in one convenient location

**Note**: Debug logs are automatically excluded from git via `.gitignore` to prevent accidental commits.
