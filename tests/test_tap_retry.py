"""Offline unit tests for the TAP retry/backoff logic (no network).

Swaps in a fake pyvo TAPService so transient failures and deterministic
rejections can be exercised without hitting a live service. Runs as a plain
script (no pytest), matching tests/test_smoke.py.
"""
from __future__ import annotations

from astropy.table import Table
from pyvo.dal.exceptions import DALQueryError, DALServiceError

from astrodata_mcp.core import tap


class _FakeSearchResult:
    def __init__(self, table: Table):
        self._table = table

    def to_table(self) -> Table:
        return self._table


class _FakeService:
    """A TAPService whose search() fails a set number of times, then succeeds."""

    def __init__(self, fail_times: int, exc: Exception):
        self.calls = 0
        self._fail_times = fail_times
        self._exc = exc

    def search(self, query, maxrec=None):
        self.calls += 1
        if self.calls <= self._fail_times:
            raise self._exc
        return _FakeSearchResult(Table({"n": [1]}))


def _install(service):
    """Point run_adql at the fake service and make backoff instant."""
    tap.pyvo.dal.TAPService = lambda endpoint: service
    tap.time.sleep = lambda s: None
    tap.clear_cache()


def _run_with(service):
    orig_service = tap.pyvo.dal.TAPService
    orig_sleep = tap.time.sleep
    try:
        _install(service)
        return tap.run_adql("http://x", "SELECT 1", use_cache=False)
    finally:
        tap.pyvo.dal.TAPService = orig_service
        tap.time.sleep = orig_sleep


def test_retry_then_success():
    svc = _FakeService(fail_times=2, exc=DALServiceError("503 boom"))
    table = _run_with(svc)
    assert len(table) == 1
    assert svc.calls == 3  # failed twice, succeeded on the third


def test_retry_exhausted_raises():
    svc = _FakeService(fail_times=99, exc=DALServiceError("still down"))
    raised = False
    try:
        _run_with(svc)
    except tap.TAPQueryError:
        raised = True
    assert raised
    assert svc.calls == tap._MAX_ATTEMPTS


def test_query_error_not_retried():
    svc = _FakeService(fail_times=99, exc=DALQueryError("bad ADQL"))
    raised = False
    try:
        _run_with(svc)
    except tap.TAPQueryError:
        raised = True
    assert raised
    assert svc.calls == 1  # deterministic rejection: no retry


if __name__ == "__main__":
    for fn in (test_retry_then_success, test_retry_exhausted_raises,
               test_query_error_not_retried):
        fn()
        print(f"PASS {fn.__name__}")
    print("ALL TAP RETRY TESTS PASSED")
