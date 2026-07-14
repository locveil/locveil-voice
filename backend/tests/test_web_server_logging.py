"""QUAL-78: successful healthcheck-probe access lines stay out of the logs.

The container healthcheck probes /health every 30 s; uvicorn access-logs each probe, which
drowns real events and burns the BUG-30 rotation budget. The filter drops only 2xx probe
lines — a failing probe must stay visible.
"""

import logging
from types import SimpleNamespace

from locveil_voice.runners.web_server import (WebServerMixin, _HEALTH_PROBE_FILTER,
                                              _HealthProbeAccessFilter)


def _access_record(path="/health", status=200):
    # the shape uvicorn.access emits: '%s - "%s %s HTTP/%s" %d'
    return logging.LogRecord("uvicorn.access", logging.INFO, __file__, 0,
                             '%s - "%s %s HTTP/%s" %d',
                             ("127.0.0.1:1", "GET", path, "1.1", status), None)


def test_drops_successful_health_probe():
    f = _HealthProbeAccessFilter()
    assert f.filter(_access_record("/health", 200)) is False
    assert f.filter(_access_record("/ready", 204)) is False


def test_query_string_does_not_unhide_the_probe():
    assert _HealthProbeAccessFilter().filter(_access_record("/health?verbose=1", 200)) is False


def test_keeps_failing_probe():
    # a non-2xx probe is exactly the event worth seeing
    assert _HealthProbeAccessFilter().filter(_access_record("/health", 503)) is True


def test_keeps_other_requests():
    f = _HealthProbeAccessFilter()
    assert f.filter(_access_record("/execute/command", 200)) is True
    assert f.filter(_access_record("/healthz", 200)) is True  # exact paths only


def test_tolerates_non_access_shaped_records():
    # records without the 5-tuple args (other uvicorn loggers, plain messages) pass through
    rec = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 0, "shutting down", None, None)
    assert _HealthProbeAccessFilter().filter(rec) is True


def test_build_uvicorn_server_installs_filter_once():
    runner = WebServerMixin()
    runner.app = object()  # uvicorn.Config takes any callable/app object without running it
    args = SimpleNamespace(host="127.0.0.1", port=0, log_level="INFO", reload=False,
                           workers=1, ssl_cert=None, ssl_key=None)
    access_logger = logging.getLogger("uvicorn.access")
    try:
        runner._build_uvicorn_server(args)
        runner._build_uvicorn_server(args)  # a second build must not stack a duplicate
        assert access_logger.filters.count(_HEALTH_PROBE_FILTER) == 1
    finally:
        access_logger.removeFilter(_HEALTH_PROBE_FILTER)
