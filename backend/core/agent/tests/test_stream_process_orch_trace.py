"""stream_process 在 orchestration_trace=summary 时下发 __ORCH_TRACE__"""
import json
import pytest
from unittest.mock import AsyncMock, patch

from backend.core.agent.orchestrator import Orchestrator


def _orch_frames(chunks):
    out = []
    for c in chunks:
        if isinstance(c, str) and c.startswith("__ORCH_TRACE__:"):
            out.append(json.loads(c[len("__ORCH_TRACE__:") :].strip()))
    return out


@pytest.mark.asyncio
async def test_summary_emits_orch_trace_frames():
    async def mock_stream():
        yield "x"

    orch = Orchestrator()
    with patch.object(orch.skill_registry, "match", new_callable=AsyncMock, return_value=None):
        with patch.object(orch.llm_service, "stream_chat", return_value=mock_stream()):
            chunks = []
            async for c in orch.stream_process(
                "hi",
                context={
                    "orchestration_trace": "summary",
                    "session_id": "sess_orch_1",
                    "context_type": "work_assistant",
                },
            ):
                chunks.append(c)
    frames = _orch_frames(chunks)
    assert len(frames) >= 3
    phases = {f.get("phase") for f in frames}
    assert "intent" in phases
    assert "step" in phases
    assert "synthesis" in phases
    assert any(f.get("payload", {}).get("step_id") == "skill_prematch" for f in frames)
    assert all(f.get("audience") == "user" for f in frames)
