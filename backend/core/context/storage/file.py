"""文件存储后端"""
import json
import uuid
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from backend.core.context.storage.base import StorageBackend
from backend.core.context.models import Message, Session


def _normalize_message_id(value) -> str:
    """message_id 在 JSON 中可能为 int/str/None，删除与比对时统一为 strip 后的 str（2026-03-13）。"""
    if value is None:
        return ""
    return str(value).strip()


class FileStorageBackend(StorageBackend):
    """文件存储后端"""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """初始化文件存储后端
        
        Args:
            storage_dir: 存储目录，如果为 None，使用项目配置目录下的 contexts
        """
        if storage_dir is None:
            from shared.platform_utils import get_app_data_dir
            storage_dir = get_app_data_dir() / "contexts"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_file = self.storage_dir / "sessions.json"
        self._sessions_lock = threading.Lock()
        # 2026-03-21：同一会话 messages.json/jsonl 的读-改-写必须串行，否则并发 batch/save 会互相覆盖（终端审查：竞态）
        self._session_msg_locks: dict = {}
        self._session_msg_locks_guard = threading.Lock()
        self._load_sessions()

    def _session_messages_lock(self, session_id: str) -> threading.Lock:
        """返回该 session 消息文件专用锁；方法：每 session 一个 threading.Lock，由 guard 字典惰性创建。"""
        with self._session_msg_locks_guard:
            if session_id not in self._session_msg_locks:
                self._session_msg_locks[session_id] = threading.Lock()
            return self._session_msg_locks[session_id]

    def _drop_session_messages_lock(self, session_id: str) -> None:
        """会话从索引移除后摘掉锁条目，避免字典无限增长（仅删会话时调用）。"""
        with self._session_msg_locks_guard:
            self._session_msg_locks.pop(session_id, None)
    
    def _get_session_dir(self, session_id: str) -> Path:
        """获取会话目录"""
        return self.storage_dir / session_id
    
    def _get_messages_file(self, session_id: str) -> Path:
        """获取消息文件（JSON 格式）"""
        return self._get_session_dir(session_id) / "messages.json"

    def _get_messages_jsonl_file(self, session_id: str) -> Path:
        """获取消息文件（JSONL 格式，2025-03-20：兼容仅存在 jsonl 的历史会话）"""
        return self._get_session_dir(session_id) / "messages.jsonl"

    def _read_messages_jsonl(self, path: Path) -> List[Message]:
        """从 JSONL 文件读取消息，每行格式为 {"message": {...}}"""
        messages: List[Message] = []
        if not path.exists():
            return messages
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    msg_data = data.get("message") or data
                    if isinstance(msg_data, dict):
                        messages.append(Message.from_dict(msg_data))
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
        return messages

    def _get_article_file(self, session_id: str) -> Path:
        """获取当前文章草稿文件路径（写文章会话的右侧输出）"""
        return self._get_session_dir(session_id) / "current_article.md"

    def get_session_article(self, session_id: str) -> Optional[str]:
        """读取会话的当前文章草稿（右侧预览内容），用于注入对话上下文。"""
        path = self._get_article_file(session_id)
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None

    def set_session_article(self, session_id: str, content: str) -> bool:
        """保存会话的当前文章草稿；对话中会多次作为上下文使用。"""
        try:
            session_dir = self._get_session_dir(session_id)
            session_dir.mkdir(parents=True, exist_ok=True)
            self._get_article_file(session_id).write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False

    def _get_mw_sources_file(self, session_id: str) -> Path:
        """写文章会话的参考 MediaWiki 页面列表（页面标题）"""
        return self._get_session_dir(session_id) / "mw_sources.json"

    def get_session_mw_sources(self, session_id: str) -> List[str]:
        """读取会话的参考 MediaWiki 页面标题列表。"""
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
        """保存会话的参考 MediaWiki 页面标题列表。"""
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

    def _load_sessions(self):
        """加载会话列表（单条解析失败不拖垮整体）"""
        self.sessions = {}
        if not self.sessions_file.exists():
            return
        try:
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        for s in data.get("sessions", []):
            if not isinstance(s, dict) or not s.get("session_id"):
                continue
            try:
                self.sessions[s["session_id"]] = Session.from_dict(s)
            except Exception:
                continue
    
    def _save_sessions(self):
        """保存会话列表（合并已有 metadata，避免用空覆盖有标题的会话）"""
        with self._sessions_lock:
            self._save_sessions_impl()

    def _save_sessions_impl(self):
        """实际写入逻辑（由 _save_sessions 加锁后调用）"""
        existing = {}
        if self.sessions_file.exists():
            try:
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for s in data.get("sessions", []):
                        if isinstance(s, dict) and s.get("session_id"):
                            existing[s["session_id"]] = s
            except (json.JSONDecodeError, OSError):
                pass
        out = []
        for s in self.sessions.values():
            d = s.to_dict()
            ex = existing.get(s.session_id)
            if ex and isinstance(ex.get("metadata"), dict) and ex["metadata"]:
                if not (d.get("metadata") or {}):
                    d["metadata"] = ex["metadata"]
                elif not (d.get("metadata") or {}).get("title") and ex["metadata"].get("title"):
                    d.setdefault("metadata", {})["title"] = ex["metadata"]["title"]
            out.append(d)
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump({"sessions": out}, f, ensure_ascii=False, indent=2)

    
    def save_message(self, session_id: str, message: Message) -> bool:
        """保存消息（支持幂等：metadata.idempotency_key 已存在则跳过）"""
        with self._session_messages_lock(session_id):
            session_dir = self._get_session_dir(session_id)
            session_dir.mkdir(parents=True, exist_ok=True)

            messages_file = self._get_messages_file(session_id)
            jsonl_file = self._get_messages_jsonl_file(session_id)

            # 加载现有消息。2025-03-20：json 不存在但 jsonl 存在时从 jsonl 加载，避免丢失历史
            messages = []
            if messages_file.exists():
                try:
                    with open(messages_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for m in data.get("messages", []):
                            if not isinstance(m, dict):
                                continue
                            try:
                                messages.append(Message.from_dict(m))
                            except Exception:
                                continue
                except (json.JSONDecodeError, OSError):
                    pass
            elif jsonl_file.exists():
                messages = self._read_messages_jsonl(jsonl_file)

            # 幂等检查
            idempotency_key = (message.metadata or {}).get("idempotency_key")
            if idempotency_key:
                for m in messages:
                    if (m.metadata or {}).get("idempotency_key") == idempotency_key:
                        return True  # 已存在，跳过

            # 添加新消息
            if not message.message_id:
                message.message_id = str(uuid.uuid4())
            messages.append(message)

            # 保存消息
            with open(messages_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "messages": [m.to_dict() for m in messages]
                }, f, ensure_ascii=False, indent=2)

            # 如果会话不存在，尝试从文件恢复（避免覆盖已有 metadata）
            if session_id not in self.sessions:
                from backend.core.context.models import Session
                session = None
                if self.sessions_file.exists():
                    try:
                        with open(self.sessions_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            for s in data.get("sessions", []):
                                if isinstance(s, dict) and s.get("session_id") == session_id:
                                    try:
                                        session = Session.from_dict(s)
                                        break
                                    except Exception:
                                        pass
                    except (json.JSONDecodeError, OSError):
                        pass
                if session is None:
                    session = Session(session_id=session_id, metadata={})
                self.sessions[session_id] = session
                self._save_sessions()
            else:
                # 更新会话时间
                self.sessions[session_id].updated_at = datetime.now()
                self._save_sessions()

            return True
    
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """获取消息列表。优先 json，无则回退到 jsonl（2025-03-20：兼容仅 jsonl 的历史会话）。"""
        with self._session_messages_lock(session_id):
            messages_file = self._get_messages_file(session_id)
            jsonl_file = self._get_messages_jsonl_file(session_id)

            messages: List[Message] = []
            needs_save = False
            use_jsonl = False

            # 本次在内存中新分配的 id（仅用于持久化失败时回滚，避免前端拿到磁盘里不存在的 id）
            freshly_assigned: List[Message] = []

            if messages_file.exists():
                with open(messages_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for m in data.get("messages", []):
                    if not isinstance(m, dict):
                        continue
                    try:
                        msg = Message.from_dict(m)
                        if not _normalize_message_id(msg.message_id):
                            msg.message_id = str(uuid.uuid4())
                            freshly_assigned.append(msg)
                            needs_save = True
                        messages.append(msg)
                    except Exception:
                        continue
            elif jsonl_file.exists():
                use_jsonl = True
                messages = self._read_messages_jsonl(jsonl_file)
                for msg in messages:
                    if not _normalize_message_id(msg.message_id):
                        msg.message_id = str(uuid.uuid4())
                        freshly_assigned.append(msg)
                        needs_save = True
            else:
                return []

            write_ok = True
            if needs_save and use_jsonl:
                try:
                    with open(jsonl_file, 'w', encoding='utf-8') as f:
                        for m in messages:
                            f.write(json.dumps({"message": m.to_dict()}, ensure_ascii=False) + "\n")
                except (OSError, TypeError):
                    write_ok = False
            elif needs_save:
                try:
                    with open(messages_file, 'w', encoding='utf-8') as f:
                        json.dump(
                            {"messages": [m.to_dict() for m in messages]},
                            f, ensure_ascii=False, indent=2
                        )
                except (OSError, TypeError):
                    write_ok = False

            # 2026-03-13：若补全 message_id 后写盘失败，必须回滚内存中的 id，否则 GET 返回的 id 无法被 DELETE 命中
            if needs_save and not write_ok:
                for msg in freshly_assigned:
                    msg.message_id = None

            if offset > 0:
                messages = messages[offset:]
            if limit:
                messages = messages[:limit]
            return messages
    
    def delete_message(self, session_id: str, message_id: str) -> bool:
        """删除消息。message_id 比较时统一转为 str 并 strip。优先 json，无则回退 jsonl（2025-03-20：兼容仅 jsonl 的历史会话）。"""
        target_id = _normalize_message_id(message_id)
        if not target_id:
            return False

        with self._session_messages_lock(session_id):
            messages_file = self._get_messages_file(session_id)
            jsonl_file = self._get_messages_jsonl_file(session_id)

            if messages_file.exists():
                with open(messages_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                messages = []
                for m in data.get("messages", []):
                    if not isinstance(m, dict):
                        continue
                    try:
                        messages.append(Message.from_dict(m))
                    except Exception:
                        continue
                use_jsonl = False
            elif jsonl_file.exists():
                messages = self._read_messages_jsonl(jsonl_file)
                use_jsonl = True
            else:
                return False

            original_count = len(messages)
            messages = [m for m in messages if _normalize_message_id(m.message_id) != target_id]

            if len(messages) < original_count:
                if use_jsonl:
                    with open(jsonl_file, 'w', encoding='utf-8') as f:
                        for m in messages:
                            f.write(json.dumps({"message": m.to_dict()}, ensure_ascii=False) + "\n")
                else:
                    with open(messages_file, 'w', encoding='utf-8') as f:
                        json.dump({"messages": [m.to_dict() for m in messages]}, f, ensure_ascii=False, indent=2)
                return True
            return False

    def delete_messages(self, session_id: str, message_ids: List[str]) -> Dict[str, Any]:
        """一次读盘、过滤、写回，避免 N 次 delete_message；与同会话 save/delete 共锁（2026-03-21，终端审查：竞态与性能）。"""
        result: Dict[str, Any] = {"success": True, "deleted": [], "failed": []}
        if not message_ids:
            result["success"] = False
            result["failed"] = [{"message_id": "", "error": "message_ids 为空"}]
            return result

        with self._session_messages_lock(session_id):
            messages_file = self._get_messages_file(session_id)
            jsonl_file = self._get_messages_jsonl_file(session_id)

            if not messages_file.exists() and not jsonl_file.exists():
                for raw in message_ids:
                    rn = _normalize_message_id(raw)
                    if rn:
                        result["failed"].append({"message_id": raw, "error": "会话无消息文件或会话目录不存在"})
                    else:
                        result["failed"].append({"message_id": raw, "error": "无效 message_id"})
                if result["failed"]:
                    result["success"] = False
                return result

            if messages_file.exists():
                with open(messages_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                messages = []
                for m in data.get("messages", []):
                    if not isinstance(m, dict):
                        continue
                    try:
                        messages.append(Message.from_dict(m))
                    except Exception:
                        continue
                use_jsonl = False
            else:
                messages = self._read_messages_jsonl(jsonl_file)
                use_jsonl = True

            want_norms = {_normalize_message_id(x) for x in message_ids if _normalize_message_id(x)}
            removed_norms: set = set()
            filtered: List[Message] = []
            for m in messages:
                nid = _normalize_message_id(m.message_id)
                if nid in want_norms:
                    removed_norms.add(nid)
                else:
                    filtered.append(m)

            for raw in message_ids:
                n = _normalize_message_id(raw)
                if not n:
                    result["failed"].append({"message_id": raw, "error": "无效 message_id"})
                    continue
                if n in removed_norms:
                    result["deleted"].append(str(raw).strip())
                else:
                    result["failed"].append({"message_id": raw, "error": "消息不存在"})

            if not result["deleted"] and result["failed"]:
                result["success"] = False

            if len(filtered) < len(messages):
                if use_jsonl:
                    with open(jsonl_file, 'w', encoding='utf-8') as f:
                        for m in filtered:
                            f.write(json.dumps({"message": m.to_dict()}, ensure_ascii=False) + "\n")
                else:
                    with open(messages_file, 'w', encoding='utf-8') as f:
                        json.dump({"messages": [m.to_dict() for m in filtered]}, f, ensure_ascii=False, indent=2)

            return result

    def clear_session(self, session_id: str) -> bool:
        """清除会话内容：删除该会话下所有消息与当前文章草稿（session_dir），会话记录保留。"""
        with self._session_messages_lock(session_id):
            session_dir = self._get_session_dir(session_id)
            if session_dir.exists():
                shutil.rmtree(session_dir)
            if session_id in self.sessions:
                self.sessions[session_id].updated_at = datetime.now()
                self._save_sessions()
        return True

    def delete_session(self, session_id: str) -> bool:
        """删除会话：移除会话目录并从会话列表中移除记录。"""
        with self._session_messages_lock(session_id):
            session_dir = self._get_session_dir(session_id)
            dir_existed = session_dir.exists()
            if dir_existed:
                shutil.rmtree(session_dir)
            if session_id in self.sessions:
                del self.sessions[session_id]
                self._save_sessions()
                ok = True
            else:
                ok = dir_existed
        # 须在释放会话消息锁之后再 pop，否则其它线程可能在仍持锁时拿到新 Lock 对象造成混乱
        self._drop_session_messages_lock(session_id)
        return ok

    def create_session(self, session: Session) -> bool:
        """创建会话"""
        self.sessions[session.session_id] = session
        self._save_sessions()
        return True
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.sessions.get(session_id)

    def update_session_metadata(self, session_id: str, updates: dict) -> bool:
        """更新会话元数据（如 title）；updates 会合并进现有 metadata。"""
        if session_id not in self.sessions:
            return False
        session = self.sessions[session_id]
        session.metadata.update(updates)
        session.updated_at = datetime.now()
        self._save_sessions()
        return True

    def list_sessions(
        self,
        limit: Optional[int] = None,
        sort: str = "updated_at",
        order: str = "desc",
        offset: int = 0,
    ) -> List[Session]:
        """列出会话；sort=updated_at|created_at，order=asc|desc，offset/limit 分页。"""
        sessions = list(self.sessions.values())
        key_attr = sort if sort in ("updated_at", "created_at") else "updated_at"
        reverse = (order or "desc").lower() != "asc"
        sessions.sort(key=lambda s: getattr(s, key_attr, s.updated_at), reverse=reverse)
        if offset > 0:
            sessions = sessions[offset:]
        if limit is not None:
            sessions = sessions[:limit]
        return sessions

