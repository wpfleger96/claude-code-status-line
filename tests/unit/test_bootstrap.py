"""Unit tests for the install bootstrap (ensure_command_installed)."""

import subprocess

from claude_code_statusline.cli import bootstrap

CMD = "claude-code-statusline"
WHICH = "claude_code_statusline.cli.bootstrap.shutil.which"
RUN = "claude_code_statusline.cli.bootstrap.subprocess.run"


def test_noop_when_already_on_path(monkeypatch):
    monkeypatch.setattr(WHICH, {CMD: f"/bin/{CMD}"}.get)
    calls: list[object] = []
    monkeypatch.setattr(RUN, lambda *a, **k: calls.append(a))

    assert bootstrap.ensure_command_installed() == (True, "")
    assert calls == []  # never shells out when already installed


def test_installs_with_uv_when_missing(monkeypatch):
    table = {"uv": "/bin/uv"}  # command missing until installed
    monkeypatch.setattr(WHICH, table.get)

    def fake_run(cmd, **kwargs):
        assert cmd == ["uv", "tool", "install", CMD]
        table[CMD] = f"/bin/{CMD}"  # now resolvable
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(RUN, fake_run)

    ok, message = bootstrap.ensure_command_installed()
    assert ok is True
    assert "via uv" in message


def test_falls_back_to_pipx(monkeypatch):
    table = {"pipx": "/bin/pipx"}
    monkeypatch.setattr(WHICH, table.get)

    def fake_run(cmd, **kwargs):
        assert cmd == ["pipx", "install", CMD]
        table[CMD] = f"/bin/{CMD}"
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(RUN, fake_run)

    ok, message = bootstrap.ensure_command_installed()
    assert ok is True
    assert "via pipx" in message


def test_hard_failure_when_no_installer(monkeypatch):
    monkeypatch.setattr(WHICH, {}.get)
    calls: list[object] = []
    monkeypatch.setattr(RUN, lambda *a, **k: calls.append(a))

    ok, message = bootstrap.ensure_command_installed()
    assert ok is False
    assert "neither 'uv' nor 'pipx'" in message
    assert calls == []  # aborts before shelling out


def test_hard_failure_when_install_errors(monkeypatch):
    monkeypatch.setattr(WHICH, {"uv": "/bin/uv"}.get)

    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(RUN, fake_run)

    ok, message = bootstrap.ensure_command_installed()
    assert ok is False
    assert "Failed to install" in message


def test_warns_when_installed_but_not_on_path(monkeypatch):
    monkeypatch.setattr(WHICH, {"uv": "/bin/uv"}.get)  # CMD never resolvable
    monkeypatch.setattr(RUN, lambda cmd, **k: subprocess.CompletedProcess(cmd, 0))

    ok, message = bootstrap.ensure_command_installed()
    assert ok is True
    assert "not yet on PATH" in message
