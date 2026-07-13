from __future__ import annotations

import io
import json
from unittest.mock import Mock

from scripts import launch_web_workspace as launcher


class _Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_service_is_ready_identifies_expected_service(monkeypatch):
    payload = {"data": {"status": "ok", "service": launcher.SERVICE_NAME}}
    monkeypatch.setattr(
        launcher.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(json.dumps(payload).encode()),
    )

    assert launcher.service_is_ready("http://example.test/health") is True


def test_service_is_ready_rejects_unrelated_server(monkeypatch):
    payload = {"data": {"status": "ok", "service": "another-service"}}
    monkeypatch.setattr(
        launcher.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(json.dumps(payload).encode()),
    )

    assert launcher.service_is_ready("http://example.test/health") is False


def test_existing_service_opens_browser_without_starting_process(monkeypatch):
    opened = []
    monkeypatch.setattr(launcher, "service_is_ready", lambda _url: True)
    monkeypatch.setattr(launcher.webbrowser, "open", opened.append)
    popen = Mock()
    monkeypatch.setattr(launcher.subprocess, "Popen", popen)

    assert launcher.main([]) == 0
    assert opened == ["http://127.0.0.1:8000/web"]
    popen.assert_not_called()


def test_occupied_port_from_other_service_is_rejected(monkeypatch):
    monkeypatch.setattr(launcher, "service_is_ready", lambda _url: False)
    monkeypatch.setattr(launcher, "port_is_in_use", lambda _host, _port: True)
    popen = Mock()
    monkeypatch.setattr(launcher.subprocess, "Popen", popen)

    assert launcher.main(["--no-browser"]) == 1
    popen.assert_not_called()


def test_startup_timeout_terminates_process(monkeypatch):
    process = Mock()
    process.poll.return_value = None
    monkeypatch.setattr(launcher, "service_is_ready", lambda _url: False)
    monkeypatch.setattr(launcher, "port_is_in_use", lambda _host, _port: False)
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(launcher, "wait_until_ready", lambda *_args, **_kwargs: False)

    assert launcher.main(["--no-browser", "--startup-timeout", "0.1"]) == 1
    process.terminate.assert_called_once()


def test_wait_until_ready_stops_when_process_exits(monkeypatch):
    process = Mock()
    process.poll.return_value = 3
    monkeypatch.setattr(launcher, "service_is_ready", lambda _url: False)

    assert launcher.wait_until_ready(process, "http://example.test", timeout=1) is False


def test_invalid_port_does_not_probe_or_start(monkeypatch):
    probe = Mock()
    monkeypatch.setattr(launcher, "service_is_ready", probe)

    assert launcher.main(["--port", "70000"]) == 2
    probe.assert_not_called()
