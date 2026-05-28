"""Tests for dev.py startup-hardening helpers.

Covers: _pid_on_port, _port_free, _kill_tree, _free_port
(AC-001 through AC-005 of specs/startup-hardening.feature)
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, call, patch

import pytest

import dev


# ── _pid_on_port ──────────────────────────────────────────────────────────────

_NETSTAT_WITH_8000 = """\
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       1256
  TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       4242
  TCP    0.0.0.0:443            0.0.0.0:0              LISTENING       999
"""

_NETSTAT_WITHOUT_8000 = """\
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       1256
  TCP    0.0.0.0:443            0.0.0.0:0              LISTENING       999
"""

_NETSTAT_WITH_5173 = """\
  TCP    0.0.0.0:5173           0.0.0.0:0              LISTENING       7777
"""


def _netstat_result(output: str) -> MagicMock:
    m = MagicMock()
    m.stdout = output
    return m


def test_pid_on_port_found(monkeypatch):
    monkeypatch.setattr(
        "dev.subprocess.run",
        lambda *a, **kw: _netstat_result(_NETSTAT_WITH_8000),
    )
    assert dev._pid_on_port(8000) == 4242


def test_pid_on_port_not_found_returns_none(monkeypatch):
    monkeypatch.setattr(
        "dev.subprocess.run",
        lambda *a, **kw: _netstat_result(_NETSTAT_WITHOUT_8000),
    )
    assert dev._pid_on_port(8000) is None


def test_pid_on_port_different_port(monkeypatch):
    monkeypatch.setattr(
        "dev.subprocess.run",
        lambda *a, **kw: _netstat_result(_NETSTAT_WITH_5173),
    )
    assert dev._pid_on_port(5173) == 7777
    assert dev._pid_on_port(8000) is None


def test_pid_on_port_exception_returns_none(monkeypatch):
    def boom(*a, **kw):
        raise OSError("netstat not found")

    monkeypatch.setattr("dev.subprocess.run", boom)
    assert dev._pid_on_port(8000) is None


# ── _port_free ────────────────────────────────────────────────────────────────

def test_port_free_when_connect_fails(monkeypatch):
    mock_sock = MagicMock()
    mock_sock.__enter__ = lambda s: s
    mock_sock.__exit__ = MagicMock(return_value=False)
    mock_sock.connect_ex.return_value = 111  # non-zero = refused = free

    monkeypatch.setattr(dev.socket, "socket", lambda: mock_sock)
    assert dev._port_free(8000) is True


def test_port_not_free_when_connect_succeeds(monkeypatch):
    mock_sock = MagicMock()
    mock_sock.__enter__ = lambda s: s
    mock_sock.__exit__ = MagicMock(return_value=False)
    mock_sock.connect_ex.return_value = 0  # zero = connected = occupied

    monkeypatch.setattr(dev.socket, "socket", lambda: mock_sock)
    assert dev._port_free(8000) is False


# ── _kill_tree ────────────────────────────────────────────────────────────────

def test_kill_tree_calls_taskkill(monkeypatch):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)

    monkeypatch.setattr("dev.subprocess.run", fake_run)
    dev._kill_tree(4242)

    assert len(calls) == 1
    assert calls[0] == ["taskkill", "/F", "/T", "/PID", "4242"]


def test_kill_tree_uses_str_pid(monkeypatch):
    """PID must be a string arg, not an int, for taskkill."""
    received = []

    def fake_run(cmd, **kw):
        received.extend(cmd)

    monkeypatch.setattr("dev.subprocess.run", fake_run)
    dev._kill_tree(99)
    assert "/PID" in received
    idx = received.index("/PID")
    assert received[idx + 1] == "99"
    assert isinstance(received[idx + 1], str)


# ── _free_port ────────────────────────────────────────────────────────────────

def test_free_port_does_nothing_when_already_free(monkeypatch):
    monkeypatch.setattr("dev._pid_on_port", lambda p: None)
    kill_calls = []
    monkeypatch.setattr("dev._kill_tree", lambda pid: kill_calls.append(pid))
    dev._free_port(8000)
    assert kill_calls == []


def test_free_port_kills_pid_and_returns_when_freed(monkeypatch, capsys):
    monkeypatch.setattr("dev._pid_on_port", lambda p: 4242)
    kill_calls = []
    monkeypatch.setattr("dev._kill_tree", lambda pid: kill_calls.append(pid))
    # Port is free immediately after kill
    monkeypatch.setattr("dev._port_free", lambda p: True)
    monkeypatch.setattr("dev.time.sleep", lambda _: None)

    dev._free_port(8000)

    assert kill_calls == [4242]
    out = capsys.readouterr().out
    assert "4242" in out
    assert "8000" in out


def test_free_port_polls_until_free(monkeypatch):
    """Port is not free on first two polls, then becomes free."""
    monkeypatch.setattr("dev._pid_on_port", lambda p: 4242)
    monkeypatch.setattr("dev._kill_tree", lambda pid: None)

    poll_count = 0

    def fake_port_free(p):
        nonlocal poll_count
        poll_count += 1
        return poll_count >= 3  # free on 3rd check

    monkeypatch.setattr("dev._port_free", fake_port_free)
    monkeypatch.setattr("dev.time.sleep", lambda _: None)

    # Ensure deadline never expires during test
    _monotonic_calls = [0.0]

    def fake_monotonic():
        t = _monotonic_calls[0]
        _monotonic_calls[0] += 0.05  # advance 50 ms per call
        return t

    monkeypatch.setattr("dev.time.monotonic", fake_monotonic)

    dev._free_port(8000)
    assert poll_count == 3


def test_free_port_exits_if_port_stays_held(monkeypatch, capsys):
    """sys.exit(1) is called with a clear message when the port cannot be freed."""
    monkeypatch.setattr("dev._pid_on_port", lambda p: 4242)
    monkeypatch.setattr("dev._kill_tree", lambda pid: None)
    monkeypatch.setattr("dev._port_free", lambda p: False)  # never frees
    monkeypatch.setattr("dev.time.sleep", lambda _: None)

    # Deadline expires immediately
    _calls = [0.0, 999.0]

    def fake_monotonic():
        return _calls.pop(0) if _calls else 999.0

    monkeypatch.setattr("dev.time.monotonic", fake_monotonic)

    with pytest.raises(SystemExit) as exc_info:
        dev._free_port(8000)

    assert exc_info.value.code == 1
    out = capsys.readouterr().out
    assert "8000" in out
    assert "4242" in out


def test_free_port_message_names_both_port_and_pid_on_success(monkeypatch, capsys):
    monkeypatch.setattr("dev._pid_on_port", lambda p: 1234)
    monkeypatch.setattr("dev._kill_tree", lambda pid: None)
    monkeypatch.setattr("dev._port_free", lambda p: True)
    monkeypatch.setattr("dev.time.sleep", lambda _: None)

    dev._free_port(5173)

    out = capsys.readouterr().out
    assert "5173" in out
    assert "1234" in out
