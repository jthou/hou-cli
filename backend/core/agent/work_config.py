"""
工作配置：工作规则、工作上下文、术语表。
供工作助手读取，在回答时遵循规则、了解工作内容、提示工作建议。
"""
import json
import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class WorkConfig:
    """工作配置：规则、上下文、术语"""
    rules: List[str] = field(default_factory=list)      # 工作规则（必须遵守的规范）
    work_context: str = ""                              # 工作上下文（当前项目/任务、目标、时间线）
    terms: List[str] = field(default_factory=list)     # 术语表（团队/公司专用术语、缩写）
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "WorkConfig":
        if not d:
            return cls()
        return cls(
            rules=list(d.get("rules") or []),
            work_context=str(d.get("work_context") or ""),
            terms=list(d.get("terms") or []),
            extra=dict(d.get("extra") or {}),
        )


def get_config_path() -> Path:
    """工作配置文件路径：WORK_CONFIG_PATH 或项目 config/work_config.json"""
    env_path = os.getenv("WORK_CONFIG_PATH", "").strip()
    if env_path:
        return Path(env_path).expanduser()
    for base in [Path.cwd(), Path(__file__).resolve().parents[3]]:
        for name in ["config/work_config.json", "work_config.json"]:
            p = base / name
            if p.exists():
                return p
    return Path.cwd() / "config" / "work_config.json"


def get_config_block_for_prompt(path: Optional[Path] = None) -> str:
    """返回工作配置的 prompt 片段，供 orchestrator 注入到 user 消息。无配置时返回空。"""
    config = load_work_config(path)
    parts = []
    if config.rules:
        parts.append("【工作规则（必须遵守）】\n" + "\n".join(f"- {r}" for r in config.rules))
    if config.work_context and config.work_context.strip():
        parts.append("【工作上下文】\n" + config.work_context.strip())
    if config.terms:
        parts.append("【术语表】\n" + "\n".join(f"- {t}" for t in config.terms))
    if not parts:
        return ""
    intro = "\n\n以下为工作配置，请严格遵循规则并基于工作上下文作答，必要时提示工作建议：\n\n"
    return intro + "\n\n".join(parts)


def load_work_config(path: Optional[Path] = None) -> WorkConfig:
    """从 JSON 加载工作配置；文件不存在则返回空配置"""
    p = path or get_config_path()
    if not p.exists():
        return WorkConfig()
    try:
        with open(p, "r", encoding="utf-8") as f:
            return WorkConfig.from_dict(json.load(f))
    except Exception:
        return WorkConfig()


def save_work_config(config: WorkConfig, path: Optional[Path] = None) -> Path:
    """保存工作配置到 JSON"""
    p = path or get_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
    return p
