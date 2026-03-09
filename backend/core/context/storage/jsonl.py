"""JSONL append-only 存储后端

借鉴 OpenClaw：每行一条 JSON，append-only 写入，长会话下 I/O 稳定、并发友好。
"""
import json
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from backend.core.context.storage.base import StorageBackend
from backend.core.context.models import Message, Session


def _safe_session_id(session_id: str) -> str:
    """确保 session_id 安全，避免路径遍历。"""
    if not session_id or ".." in session_id or "/" in session_id or "\\" in session_id:
        raise ValueError(f"Invalid session_id: {session_id!r}")
    return session_id.strip()


class JsonlStorageBackend(StorageBackend):
    """JSONL append-only 存储后端"""

    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            from shared.platform_utils import get_app_data_dir
            storage_dir = get_app_data_dir() / "contexts"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_file = self.storage_dir / "sessions.json"
        self._load_sessions()

    def _get_session_dir(self, session_id: str) -> Path:
        return self.storage_dir / _safe_session_id(session_id)

    def _get_messages_file(self, session_id: str) -> Path:
        return self._get_session_dir(session_id) / "messages.jsonl"

    def _get_article_file(self, session_id: str) -> Path:
        return self._get_session_dir(session_id) / "current_article.md"

    def get_session_article(self, session_id: str) -> Optional[str]:
        path = self._get_article_file(session_id)
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None

    def set_session_article(self, session_id: str, content: str) -> bool:
        try:
            session_dir = self._get_session_dir(session_id)
            session_dir.mkdir(parents=True, exist_ok=True)
            self._get_article_file(session_id).write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False

    def _get_mw_sources_file(self, session_id: str) -> Path:
        return self._get_session_dir(session_id) / "mw_sources.json"

    def get_session_mw_sources(self, session_id: str) -> List[str]:
        path = self._get_mw_sources_file(session_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            titles = data.get("titles") if isinstance(data, dict) else []
            return list(titles) if isinstance(titles, list) else []
        except Exception:
            return []

    def set_session_mw_sources(self, session_id: str, titles: List[str]) -> bool:
        try:
            session_dir = self._get_session_dir(session_id)
            session_dir.mkdir(parents=True, exist_ok=True)
            self._get_mw_sources_file(session_id).write_text(
                json.dumps({"titles": list(titles)}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return True
        except Exception:
            return False

    def _load_sessions(self) -> None:
        if self.sessions_file.exists():
            with open(self.sessions_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.sessions = {
                    s["session_id"]: Session.from_dict(s)
                    for s in data.get("sessions", [])
                }
        else:
            self.sessions = {}

    def _save_sessions(self) -> None:
        with open(self.sessions_file, "w", encoding="utf-8") as f:
            json.dump(
                {"sessions": [s.to_dict() for s in self.sessions.values()]},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _get_legacy_messages_file(self, session_id: str) -> Path:
        """旧版 JSON 格式消息文件路径。"""
        return self._get_session_dir(session_id) / "messages.json"

    def _migrate_json_to_jsonl(self, session_id: str) -> bool:
        """从旧版 messages.json 迁移到 messages.jsonl，迁移后删除 .json。"""
        jsonl_path = self._get_messages_file(session_id)
        json_path = self._get_legacy_messages_file(session_id)
        if jsonl_path.exists() or not json_path.exists():
            return False
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            msgs = data.get("messages", [])
            if not msgs:
                json_path.unlink(missing_ok=True)
                return True
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(jsonl_path, "w", encoding="utf-8") as f:
                for m in msgs:
                    f.write(json.dumps({"message": m}, ensure_ascii=False) + "\n")
            json_path.unlink(missing_ok=True)
            return True
        except Exception:
            return False

    def _read_messages_jsonl(self, messages_file: Path, session_id: str = "") -> List[Message]:
        """逐行读取 JSONL，解析 message 记录。若仅有旧版 .json 则先迁移。"""
        if not messages_file.exists():
            if session_id:
                self._migrate_json_to_jsonl(session_id)
                if messages_file.exists():
                    return self._read_messages_jsonl(messages_file, "")
            return []
        messages: List[Message] = []
        with open(messages_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    msg_data = data.get("message")
                    if msg_data:
                        messages.append(Message.from_dict(msg_data))
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
        return messages

    def _has_idempotency_key(self, messages_file: Path, key: str, session_id: str = "") -> bool:
        """检查是否已存在相同 idempotency_key 的消息。"""
        if not key:
            return False
        if not messages_file.exists() and session_id:
            self._migrate_json_to_jsonl(session_id)
        if not messages_file.exists():
            return False
        with open(messages_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    msg_data = data.get("message") or data
                    meta = msg_data.get("metadata") if isinstance(msg_data, dict) else {}
                    if isinstance(meta, dict) and meta.get("idempotency_key") == key:
                        return True
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
        return False

    def save_message(self, session_id: str, message: Message) -> bool:
        session_dir = self._get_session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        messages_file = self._get_messages_file(session_id)

        # 幂等检查
        idempotency_key = (message.metadata or {}).get("idempotency_key")
        if idempotency_key and self._has_idempotency_key(messages_file, idempotency_key, session_id):
            return True  # 已存在，跳过

        if not message.message_id:
            message.message_id = str(uuid.uuid4())

        line = json.dumps({"message": message.to_dict()}, ensure_ascii=False) + "\n"
        with open(messages_file, "a", encoding="utf-8") as f:
            f.write(line)

        if session_id not in self.sessions:
            session = Session(session_id=session_id, metadata={})
            self.sessions[session_id] = session
            self._save_sessions()
        else:
            self.sessions[session_id].updated_at = datetime.now()
            self._save_sessions()

        return True

    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Message]:
        messages_file = self._get_messages_file(session_id)
        messages = self._read_messages_jsonl(messages_file, session_id)
        if offset > 0:
            messages = messages[offset:]
        if limit is not None:
            messages = messages[:limit]
        return messages

    def delete_message(self, session_id: str, message_id: str) -> bool:
        messages_file = self._get_messages_file(session_id)
        if not messages_file.exists():
            return False
        messages = self._read_messages_jsonl(messages_file, session_id)
        original_count = len(messages)
        messages = [m for m in messages if m.message_id != message_id]
        if len(messages) < original_count:
            with open(messages_file, "w", encoding="utf-8") as f:
                for m in messages:
                    f.write(json.dumps({"message": m.to_dict()}, ensure_ascii=False) + "\n")
            if session_id in self.sessions:
                self.sessions[session_id].updated_at = datetime.now()
                self._save_sessions()
            return True
        return False

    def clear_session(self, session_id: str) -> bool:
        session_dir = self._get_session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)
        if session_id in self.sessions:
            self.sessions[session_id].updated_at = datetime.now()
            self._save_sessions()
        return True

    def delete_session(self, session_id: str) -> bool:
        session_dir = self._get_session_dir(session_id)
        dir_existed = session_dir.exists()
        if dir_existed:
            shutil.rmtree(session_dir)
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()
            return True
        return dir_existed

    def create_session(self, session: Session) -> bool:
        self.sessions[session.session_id] = session
        self._save_sessions()
        return True

    def get_session(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)

    def update_session_metadata(self, session_id: str, updates: dict) -> bool:
        if session_id not in self.sessions:
            return False
        self.sessions[session_id].metadata.update(updates)
        self.sessions[session_id].updated_at = datetime.now()
        self._save_sessions()
        return True

    def list_sessions(
        self,
        limit: Optional[int] = None,
        sort: str = "updated_at",
        order: str = "desc",
        offset: int = 0,
    ) -> List[Session]:
        sessions = list(self.sessions.values())
        key_attr = sort if sort in ("updated_at", "created_at") else "updated_at"
        reverse = (order or "desc").lower() != "asc"
        sessions.sort(key=lambda s: getattr(s, key_attr, s.updated_at), reverse=reverse)
        if offset > 0:
            sessions = sessions[offset:]
        if limit is not None:
            sessions = sessions[:limit]
        return sessions
