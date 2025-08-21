# Claude Code Statusline Script

## Overview

A Python script that generates a formatted [status line](https://docs.anthropic.com/en/docs/claude-code/statusline) for Claude Code, displaying the current model, working directory, and context usage information. The script provides real-time feedback on token consumption relative to the model's context window limit.

<img width="782" height="501" alt="image" src="https://github.com/user-attachments/assets/58b07f9c-dda8-4687-a0fe-477651534eab" />

## Features

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
    "command": "/path/to/repo/claude-code/statusline/statusline-with-context.py",
    "padding": 0 // Optional: set to 0 to let status line go to edge
  }
}
```

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
