"""JsonlStorageBackend 测试"""
import pytest
import tempfile
import shutil
from pathlib import Path
from backend.core.context.storage.jsonl import JsonlStorageBackend
from backend.core.context.models import Message, MessageRole, Session


class TestJsonlStorageBackend:
    @pytest.fixture
    def temp_dir(self):
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def storage(self, temp_dir):
        return JsonlStorageBackend(storage_dir=temp_dir)

    def test_append_only_save(self, storage):
        """验证 append-only：多次保存应追加行，不重写整文件"""
        session_id = "s1"
        storage.create_session(Session(session_id=session_id))
        for i in range(5):
            storage.save_message(session_id, Message(role=MessageRole.USER, content=f"msg{i}"))
        msgs = storage.get_messages(session_id)
        assert len(msgs) == 5
        assert msgs[2].content == "msg2"

    def test_idempotency_skip_duplicate(self, storage):
        """幂等：相同 idempotency_key 只保存一次"""
        session_id = "s1"
        storage.create_session(Session(session_id=session_id))
        msg = Message(role=MessageRole.USER, content="once", metadata={"idempotency_key": "k1"})
        storage.save_message(session_id, msg)
        storage.save_message(session_id, msg)  # 重复
        msgs = storage.get_messages(session_id)
        assert len(msgs) == 1

    def test_migrate_from_json(self, temp_dir):
        """从旧版 messages.json 迁移到 messages.jsonl"""
        import json
        session_dir = temp_dir / "legacy_session"
        session_dir.mkdir()
        legacy = session_dir / "messages.json"
        legacy.write_text(
            json.dumps({
                "messages": [
                    {"role": "user", "content": "old", "timestamp": "2024-01-01T00:00:00", "metadata": {}, "message_id": "m1"}
                ]
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        storage = JsonlStorageBackend(storage_dir=temp_dir)
        storage.sessions["legacy_session"] = Session(session_id="legacy_session", metadata={})
        msgs = storage.get_messages("legacy_session")
        assert len(msgs) == 1
        assert msgs[0].content == "old"
        assert not legacy.exists()
        assert (session_dir / "messages.jsonl").exists()
