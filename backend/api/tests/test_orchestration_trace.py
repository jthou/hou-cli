"""编排 trace：resolve_orchestration_trace_verbosity、build_orchestration_trace"""
import json
import pytest

from backend.api.stream_sender import (
    StreamMessageBuilder,
    resolve_orchestration_trace_verbosity,
)


def test_resolve_verbosity_context_over_env(monkeypatch):
    monkeypatch.setenv("ORCH_TRACE_VERBOSITY", "off")
    assert resolve_orchestration_trace_verbosity({"orchestration_trace": "summary"}) == "summary"
    assert resolve_orchestration_trace_verbosity({"trace_verbosity": "full"}) == "full"


def test_resolve_verbosity_env(monkeypatch):
    monkeypatch.setenv("ORCH_TRACE_VERBOSITY", "summary")
    assert resolve_orchestration_trace_verbosity({}) == "summary"
    monkeypatch.setenv("ORCH_TRACE_VERBOSITY", "full")
    assert resolve_orchestration_trace_verbosity(None) == "full"


def test_build_orchestration_trace_format():
    line = StreamMessageBuilder.build_orchestration_trace(
        {"v": 1, "audience": "user", "phase": "intent", "event": "started", "payload": {}}
    )
    assert line.startswith("__ORCH_TRACE__:")
    obj = json.loads(line[len("__ORCH_TRACE__:") :].strip())
    assert obj["phase"] == "intent"
