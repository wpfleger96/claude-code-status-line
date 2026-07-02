"""Persistent-install bootstrap for the statusline command.

When invoked ephemerally (e.g. ``uvx claude-code-statusline install``) the console
script is not on the user's PATH, so the ``statusLine`` command written into
settings.json would point at a missing binary. ``ensure_command_installed`` installs
the tool persistently (via ``uv tool`` or ``pipx``) before Claude Code is configured,
mirroring the detection in scripts/install.sh.
"""

import shutil
import subprocess

NAME = "claude-code-statusline"


def ensure_command_installed() -> tuple[bool, str]:
    """Ensure the ``claude-code-statusline`` command is persistently on PATH.

    Returns a ``(ok, message)`` pair. ``ok`` is False only for hard failures (no
    installer found, or the install command failed); callers should abort before
    writing settings.json. A successful no-op returns ``(True, "")``. If the tool
    was installed but is not yet visible on PATH, returns ``(True, warning)`` so the
    caller can still write the config (a fresh shell/session resolves it).
    """
    if shutil.which(NAME):
        return True, ""

    if shutil.which("uv"):
        installer, command = "uv", ["uv", "tool", "install", NAME]
    elif shutil.which("pipx"):
        installer, command = "pipx", ["pipx", "install", NAME]
    else:
        return False, (
            f"'{NAME}' is not on PATH and neither 'uv' nor 'pipx' was found.\n"
            f"Install uv (https://astral.sh/uv) or run: pipx install {NAME}"
        )

    print(f"Installing {NAME} with {installer}...")
    try:
        subprocess.run(command, check=True)
    except (subprocess.CalledProcessError, OSError) as e:
        return False, f"Failed to install {NAME} via {installer}: {e}"

    if shutil.which(NAME):
        return True, f"Installed {NAME} via {installer}."
    return True, (
        f"Installed {NAME} via {installer}, but '{NAME}' is not yet on PATH. "
        f"Restart your shell (or run 'uv tool update-shell') so Claude Code can find it."
    )
