from __future__ import annotations

import base64
import ctypes
import os
from ctypes import wintypes
from pathlib import Path
from typing import Protocol


class SecretStore(Protocol):
    persistent: bool
    name: str

    def get(self) -> str: ...
    def set(self, value: str) -> None: ...
    def clear(self) -> None: ...


class ProcessSecretStore:
    """Process-local fallback for platforms without an OS credential backend."""

    persistent = False
    name = "process_memory"
    _values: dict[str, str] = {}

    def __init__(self, namespace: str):
        self.namespace = namespace

    def get(self) -> str:
        return self._values.get(self.namespace, "")

    def set(self, value: str) -> None:
        if value:
            self._values[self.namespace] = value
        else:
            self.clear()

    def clear(self) -> None:
        self._values.pop(self.namespace, None)


if os.name == "nt":
    class _DataBlob(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
        ]


class WindowsDpapiSecretStore:
    """Current-Windows-user encrypted storage backed by DPAPI."""

    persistent = True
    name = "windows_dpapi"

    def __init__(self, path: Path):
        if os.name != "nt":
            raise RuntimeError("Windows DPAPI is only available on Windows")
        self.path = path

    @staticmethod
    def _blob(data: bytes) -> tuple[_DataBlob, object]:
        buffer = ctypes.create_string_buffer(data)
        blob = _DataBlob(
            len(data),
            ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
        )
        return blob, buffer

    @staticmethod
    def _copy_and_free(blob: _DataBlob) -> bytes:
        try:
            return ctypes.string_at(blob.pbData, blob.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob.pbData)

    def _protect(self, value: str) -> bytes:
        source, source_buffer = self._blob(value.encode("utf-8"))
        protected = _DataBlob()
        result = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(source),
            "genetic-circuit-ui",
            None,
            None,
            None,
            0,
            ctypes.byref(protected),
        )
        del source_buffer
        if not result:
            raise ctypes.WinError()
        return self._copy_and_free(protected)

    def _unprotect(self, payload: bytes) -> str:
        source, source_buffer = self._blob(payload)
        clear = _DataBlob()
        result = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(source),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(clear),
        )
        del source_buffer
        if not result:
            raise ctypes.WinError()
        return self._copy_and_free(clear).decode("utf-8")

    def get(self) -> str:
        if not self.path.exists():
            return ""
        payload = base64.b64decode(self.path.read_bytes(), validate=True)
        return self._unprotect(payload)

    def set(self, value: str) -> None:
        if not value:
            self.clear()
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = base64.b64encode(self._protect(value))
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_bytes(encoded)
        temporary.replace(self.path)

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)


def create_secret_store(settings_path: Path) -> SecretStore:
    secret_path = settings_path.with_suffix(".secret")
    if os.name == "nt":
        return WindowsDpapiSecretStore(secret_path)
    return ProcessSecretStore(str(secret_path.resolve()))
