"""Reliable local launcher for the server-rendered Web Workspace."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

SERVICE_NAME = "genetic-circuit-api"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def service_is_ready(health_url: str, *, timeout: float = 1.0) -> bool:
    """Return whether the URL belongs to a healthy instance of this project."""
    try:
        with urllib.request.urlopen(health_url, timeout=timeout) as response:
            if response.status != 200:
                return False
            payload = json.load(response)
    except (OSError, ValueError, urllib.error.URLError):
        return False

    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    return data.get("status") == "ok" and data.get("service") == SERVICE_NAME


def port_is_in_use(host: str, port: int, *, timeout: float = 0.5) -> bool:
    """Return whether any process is accepting TCP connections on the address."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_until_ready(
    process: subprocess.Popen[bytes],
    health_url: str,
    *,
    timeout: float,
    poll_interval: float = 0.25,
) -> bool:
    """Wait for startup, stopping early if Uvicorn exits."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if service_is_ready(health_url):
            return True
        if process.poll() is not None:
            return False
        time.sleep(poll_interval)
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--startup-timeout", type=float, default=90.0)
    parser.add_argument("--no-browser", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 1 <= args.port <= 65535:
        print("[ERROR] Port must be between 1 and 65535.", file=sys.stderr)
        return 2
    if args.startup_timeout <= 0:
        print("[ERROR] Startup timeout must be greater than zero.", file=sys.stderr)
        return 2

    project_root = Path(__file__).resolve().parents[2]
    health_url = f"http://{args.host}:{args.port}/api/v1/health"
    workspace_url = f"http://{args.host}:{args.port}/web"

    if service_is_ready(health_url):
        print(f"Web Workspace is already running: {workspace_url}")
        if not args.no_browser:
            webbrowser.open(workspace_url)
        return 0

    if port_is_in_use(args.host, args.port):
        print(
            f"[ERROR] Port {args.port} is already used by another application.\n"
            "Close that application or launch this script with a different --port.",
            file=sys.stderr,
        )
        return 1

    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    print("Starting Genetic Circuit Web Workspace...")
    print(f"Address: {workspace_url}")
    print("Keep this window open. Press Ctrl+C here to stop the server.\n")

    try:
        process = subprocess.Popen(command, cwd=project_root)
    except OSError as exc:
        print(f"[ERROR] Could not start Python/Uvicorn: {exc}", file=sys.stderr)
        return 1

    if not wait_until_ready(process, health_url, timeout=args.startup_timeout):
        exit_detail = (
            f"Uvicorn exited with code {process.returncode}."
            if process.poll() is not None
            else f"Startup did not finish within {args.startup_timeout:g} seconds."
        )
        print(f"\n[ERROR] {exit_detail}", file=sys.stderr)
        if process.poll() is None:
            process.terminate()
        return 1

    print(f"\nWeb Workspace is ready: {workspace_url}")
    if not args.no_browser:
        webbrowser.open(workspace_url)

    try:
        return process.wait()
    except KeyboardInterrupt:
        print("\nStopping Web Workspace...")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
