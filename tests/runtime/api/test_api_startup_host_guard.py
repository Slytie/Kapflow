from __future__ import annotations

import sys
import types

import pytest

from onetruth.api.main import (
    _UNSAFE_LOCAL_DEV_NON_LOOPBACK_BIND_ENV,
    main,
)


def _install_uvicorn_stub(monkeypatch) -> list[tuple[str, int]]:
    calls: list[tuple[str, int]] = []
    uvicorn = types.SimpleNamespace(
        run=lambda app, host, port: calls.append((host, port))
    )
    monkeypatch.setitem(sys.modules, "uvicorn", uvicorn)
    return calls


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_local_dev_allows_loopback_hosts(monkeypatch, host: str) -> None:
    monkeypatch.delenv(_UNSAFE_LOCAL_DEV_NON_LOOPBACK_BIND_ENV, raising=False)
    calls = _install_uvicorn_stub(monkeypatch)

    result = main(
        ["--host", host, "--port", "9090", "--api-boundary-profile", "local_dev"]
    )

    assert result == 0
    assert calls == [(host, 9090)]


def test_local_dev_rejects_non_loopback_host_without_override(monkeypatch) -> None:
    monkeypatch.delenv(_UNSAFE_LOCAL_DEV_NON_LOOPBACK_BIND_ENV, raising=False)
    calls = _install_uvicorn_stub(monkeypatch)

    with pytest.raises(SystemExit) as excinfo:
        main(["--host", "0.0.0.0", "--api-boundary-profile", "local_dev"])

    assert calls == []
    assert str(excinfo.value) == (
        "local_dev must bind only to loopback hosts (127.0.0.1, localhost, ::1). "
        "Refusing non-loopback host '0.0.0.0'. "
        "Set ONETRUTH_UNSAFE_ALLOW_LOCAL_DEV_NON_LOOPBACK_BIND=1 only for controlled test scenarios."
    )


def test_local_dev_allows_non_loopback_host_with_explicit_unsafe_override(
    monkeypatch,
) -> None:
    monkeypatch.setenv(_UNSAFE_LOCAL_DEV_NON_LOOPBACK_BIND_ENV, "1")
    calls = _install_uvicorn_stub(monkeypatch)

    result = main(["--host", "0.0.0.0", "--api-boundary-profile", "local_dev"])

    assert result == 0
    assert calls == [("0.0.0.0", 8080)]


@pytest.mark.parametrize("boundary_profile", ["shared_env", "ci_test"])
def test_non_local_dev_profiles_are_unaffected_by_host_guard(
    monkeypatch,
    boundary_profile: str,
) -> None:
    monkeypatch.delenv(_UNSAFE_LOCAL_DEV_NON_LOOPBACK_BIND_ENV, raising=False)
    calls = _install_uvicorn_stub(monkeypatch)

    result = main(
        ["--host", "0.0.0.0", "--api-boundary-profile", boundary_profile]
    )

    assert result == 0
    assert calls == [("0.0.0.0", 8080)]
