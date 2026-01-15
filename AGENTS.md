# AGENTS.md

CLI tool that generates a formatted status line for Claude Code, displaying model, directory, git status, context/token usage, session cost, and elapsed time by parsing JSONL transcript files.

## Quick Commands

```bash
# Setup (first time)
just sync             # Install dependencies (uv sync)

# Development workflow
just                  # Quick quality check (sync, type-check, lint-check, format-check)
just check-all        # All quality checks + tests
just ci               # Match CI locally (exactly what runs in GitHub Actions)
just pre-commit       # Pre-commit with auto-fix (type-check, lint, format, test)

# Code quality (check only)
just type-check       # mypy strict mode
just lint-check       # ruff check (no fixes)
just format-check     # ruff format --check

# Code quality (auto-fix)
just lint             # ruff check --fix
just format           # ruff format

# Testing
just test                                       # Full suite (excludes performance)
uv run pytest tests/unit/test_file.py          # Single file
uv run pytest tests/unit/test_file.py::test_fn # Single test
uv run pytest -m unit                           # Unit tests only
uv run pytest -m integration                    # Integration tests only
uv run pytest -m performance                    # Performance benchmarks (opt-in)

# CLI testing (local development)
uv run claude-statusline                        # Test with stdin
echo '{"transcript_path": "..."}' | uv run claude-statusline
uv run claude-statusline install                # Install local version to Claude Code
uv run claude-statusline doctor                 # Verify installation health
uv run claude-statusline --version              # Show version

# Installation scripts (for end users)
curl -fsSL https://raw.githubusercontent.com/wpfleger96/claude-code-status-line/main/scripts/install.sh | bash
curl -fsSL https://raw.githubusercontent.com/wpfleger96/claude-code-status-line/main/scripts/uninstall.sh | bash
```

## Project Structure

```
src/claude_code_statusline/
├── statusline.py          # Main CLI entry point
├── renderer.py            # Status line rendering
├── types.py               # Dataclasses (RenderContext, TokenMetrics, etc.)
├── cli/
│   └── commands.py        # install/uninstall/doctor commands
├── config/
│   ├── defaults.py        # Default widget configuration
│   ├── loader.py          # Config file loading with mtime caching
│   └── schema.py          # Pydantic validation schemas
├── parsers/
│   ├── jsonl.py           # JSONL transcript parser
│   └── tokens.py          # Token counting with compact boundary detection
├── utils/                 # Shared utilities (colors, git, formatting, settings)
└── widgets/
    ├── base.py            # Abstract Widget base class
    ├── registry.py        # @register_widget() decorator
    └── builtin/           # 14 built-in widgets (context, cost, directory, git, model, etc.)
scripts/
├── install.sh             # One-liner automated installation
└── uninstall.sh           # Clean removal script
tests/
├── unit/                  # Unit tests (no I/O)
├── integration/           # Integration tests (mocked I/O)
├── performance/           # Benchmarks (opt-in)
└── fixtures/              # Test data (JSONL transcripts)
```

## Tech Stack

- Python 3.13 (requires >=3.9, see `.python-version`)
- Package manager: uv (development), uv tool or pipx (end user installation)
- Task runner: just
- Build: setuptools (see pyproject.toml)
- Dependencies: pyyaml>=6.0, pydantic>=2.0
- Linting: ruff (isort, pyflakes, pyupgrade, bugbear via `uvx ruff`)
- Type checking: mypy strict mode (Python 3.13 target)
- Testing: pytest, pytest-cov, pytest-benchmark
- Release: python-semantic-release (conventional commits, auto-versioning)

## Key Patterns

**Widget System**: All widgets extend `Widget` base class with `render(context: RenderContext) -> Optional[str]`. Register with `@register_widget(display_name, default_color, description, fallback_text)`.

**RenderContext**: Dataclass passed to all widgets containing `data`, `token_metrics`, `git_status`, `session_metrics`, `subscription_info`, `context_window`.

**Parallel I/O**: `statusline.py` uses `ThreadPoolExecutor(max_workers=3)` for transcript parsing, subscription loading, and model prefetch.

**Config Caching**: `config/loader.py` caches config files by mtime to avoid re-reading unchanged files.

## Testing

```bash
just test                           # Full suite (excludes performance)
uv run pytest -m unit               # Unit tests only
uv run pytest -m integration        # Integration tests only
uv run pytest -m performance        # Performance benchmarks
```

Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.performance`

Fixtures in `tests/conftest.py`: `mock_stdin`, `sample_input_payload`, `basic_session_file`, `compact_session_file`

## Common Gotchas

1. **Local dev vs installed tool** - **CRITICAL**: Always use `uv run claude-statusline` when developing locally:
   - **Local dev (from repo)**: `uv run claude-statusline <args>` → runs YOUR local code changes
   - **Installed tool (any directory)**: `claude-statusline <args>` → runs installed version from `~/.local/share/uv/tools/`
   - Running `claude-statusline` without `uv run` will NOT reflect local changes
   - **NEVER use editable install** (`uv pip install -e .`) - risks conflicts, unnecessary complexity

2. **Context window priority** (Claude Code 2.0.70+): `context_window` field from payload takes priority over transcript parsing for token counts. Falls back to transcript if `context_window` missing/null. This is the authoritative source.

3. **Compact boundary resets tokens**: Token counting resets when `/compact` boundary detected in transcript. Tests mark this as "Critical".

4. **Base64 images excluded**: Images must be filtered from token counting. Tests mark this as "Critical".

5. **Session ID priority**: After `/compact`, session_id from transcript takes priority over payload session_id.

6. **V1 config auto-deleted**: V1 configs automatically deleted and replaced with V2 format on load.

7. **Performance tests opt-in**: Excluded by default. Run with `uv run pytest -m performance`.

8. **Installation scripts handle both uv and pipx**: `scripts/install.sh` checks for uv first, falls back to pipx. Auto-configures Claude Code with `claude-statusline install --yes`.

9. **Debug logging per-session**: Set `CLAUDE_CODE_STATUSLINE_DEBUG=1` → creates `logs/statusline_debug_<session_id>.log` with token breakdown, compact boundaries, parsing errors.

## Key Files by Task

| Task | Files |
|------|-------|
| Add new widget | `widgets/builtin/<name>.py`, `widgets/builtin/__init__.py`, `config/defaults.py` |
| Modify token counting | `parsers/tokens.py`, `tests/unit/test_token_counting.py` |
| Context window handling | `types.py`, `statusline.py`, `utils/models.py`, `tests/unit/test_context_window.py` |
| Status line rendering | `renderer.py`, `config/defaults.py` |
| Config schema changes | `config/schema.py`, `config/loader.py`, `tests/integration/test_config.py` |
| CLI commands (install/doctor) | `cli/commands.py`, `statusline.py` (argparse setup) |
| Git status display | `utils/git.py`, `widgets/builtin/git.py` |
| Installation automation | `scripts/install.sh`, `scripts/uninstall.sh` |
| Release process | `.github/workflows/release.yml`, `pyproject.toml` (semantic-release config) |
