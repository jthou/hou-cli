"""
写作画像：用户喜好、表述习惯、范文。
供写文章 Agent 读取，在生成时遵循并模仿。
"""
import json
import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class SampleArticle:
    """范文：标题 + 正文（或路径，由调用方读取）"""
    title: str
    content: Optional[str] = None  # 正文；空则用 path
    path: Optional[str] = None     # 本地 .md / .txt 路径


@dataclass
class WritingProfile:
    """写作画像：记住用户喜好、表述方式与范文"""
    preferences: List[str] = field(default_factory=list)
    style_notes: str = ""
    sample_articles: List[SampleArticle] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "WritingProfile":
        if not d:
            return cls()
        samples = []
        for s in d.get("sample_articles") or []:
            if isinstance(s, dict):
                samples.append(SampleArticle(
                    title=s.get("title", ""),
                    content=s.get("content"),
                    path=s.get("path"),
                ))
        return cls(
            preferences=list(d.get("preferences") or []),
            style_notes=str(d.get("style_notes") or ""),
            sample_articles=samples,
            extra=dict(d.get("extra") or {}),
        )

    def get_sample_contents(self, max_chars_per_sample: int = 4000) -> List[str]:
        """返回范文正文列表（从 content 或 path 读取），单条截断到 max_chars_per_sample。"""
        out = []
        for s in self.sample_articles:
            text = s.content
            if not text and s.path:
                path = Path(s.path).expanduser()
                if path.is_file():
                    try:
                        text = path.read_text(
                        encoding="utf-8", errors="replace"
                    )
                    except Exception:
                        text = ""
            if text:
                if len(text) > max_chars_per_sample:
                    text = text[:max_chars_per_sample] + "\n…（已截断）"
                out.append(f"【范文】{s.title}\n\n{text}")
        return out


def get_profile_path() -> Path:
    """写作画像文件路径：WRITING_PROFILE_PATH 或项目 config/writing_profile.json"""
    env_path = os.getenv("WRITING_PROFILE_PATH", "").strip()
    if env_path:
        return Path(env_path).expanduser()
    # 项目根或 config 目录
    for base in [Path.cwd(), Path(__file__).resolve().parents[3]]:
        for name in ["config/writing_profile.json", "writing_profile.json"]:
            p = base / name
            if p.exists():
                return p
    return Path.cwd() / "config" / "writing_profile.json"


def load_writing_profile(path: Optional[Path] = None) -> WritingProfile:
    """从 JSON 加载写作画像；文件不存在则返回空画像"""
    p = path or get_profile_path()
    if not p.exists():
        return WritingProfile()
    try:
        with open(p, "r", encoding="utf-8") as f:
            return WritingProfile.from_dict(json.load(f))
    except Exception:
        return WritingProfile()


def save_writing_profile(profile: WritingProfile, path: Optional[Path] = None) -> Path:
    """保存写作画像到 JSON"""
    p = path or get_profile_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(
            profile.to_dict(), f, ensure_ascii=False, indent=2
        )
    return p
