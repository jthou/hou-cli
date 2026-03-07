"""解析 .env 中的模型配置，提取所有 *_MODEL 变量及注释中的模型名"""
import re
from pathlib import Path
from typing import List, Dict, Tuple

# 已知的模型相关 key 及 label（与 model_config_routes 一致）
MODEL_KEY_LABELS: Dict[str, str] = {
    "CHAT_MODEL": "对话模型",
    "CODE_MODEL": "编码模型",
    "REASONING_MODEL": "推理模型",
    "DEEPSEEK_MODEL": "DeepSeek 模型",
    "BAILIAN_MODEL": "百炼平台模型",
    "TURBOGATEWAY_MODEL": "TheTurbo.ai 网关模型",
    "BROWSER_TOOL_VISION_MODEL": "Browser 视觉模型",
    "BROWSER_TOOL_REASONING_MODEL": "Browser 推理模型",
    "BROWSER_TOOL_CHAT_MODEL": "Browser 对话模型",
}

# 排除的非模型值
EXCLUDE_VALUES = frozenset({
    "deepseek", "bailian", "theturbogateway", "true", "false",
    "yes", "no", "none", "null", "default", "auto",
    "browser_navigate", "browser_click", "browser_fill", "browser_snapshot",
    "https", "http", "edit", "development", "openai", "anthropic", "google",
    "perplexity", "info", "warning", "error", "debug",
})

# 模型名常见前缀（无连字符的短名如 o3 也视为有效）
MODEL_PREFIXES = (
    "gpt", "claude", "qwen", "deepseek", "gemini", "sonar",
    "o1", "o3", "o4", "o5", "wan", "baichuan", "chatglm", "llama",
)


def _is_valid_model(value: str) -> bool:
    """过滤明显非模型的值（ID、主机名、配置值等）"""
    raw = (value or "").strip()
    v = raw.lower()
    if not v or len(v) < 3:
        return False
    if v in EXCLUDE_VALUES:
        return False
    if "api_key" in v or v.endswith("_key"):
        return False
    if v.isdigit():
        return False
    # 模型名通常包含字母、数字、连字符、点、下划线
    if not re.match(r"^[a-zA-Z0-9\-\._]+$", v):
        return False
    # 排除 ID 类：全大写无连字符（如 K8GYPEQ99J、ABCDE23456）
    if raw == raw.upper() and "-" not in raw and len(raw) >= 6:
        return False
    # 排除主机名/URL 片段
    if any(x in v for x in (".com", ".re.", "qweatherapi", "127.0.0.1")):
        return False
    # 模型名通常含连字符，或为已知前缀开头
    if "-" in v:
        return True
    if v.startswith(MODEL_PREFIXES):
        return True
    # 排除纯版本号（如 v3.2、3.2）
    if re.match(r"^v?\d+(\.\d+)*$", v):
        return False
    # 纯数字+字母无连字符且较长，多为 ID
    if len(v) >= 8 and re.match(r"^[a-z0-9]+$", v):
        return False
    return True


def _extract_from_config_line(line: str) -> List[Tuple[str, str, str]]:
    """从配置行提取 key, model, source=config"""
    m = re.match(r"^([A-Z_]+_MODEL)\s*=\s*(.+)$", line.strip())
    if not m:
        return []
    key, value = m.group(1), m.group(2).strip()
    # 去除引号
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1].strip()
    if value.startswith("'") and value.endswith("'"):
        value = value[1:-1].strip()
    if not _is_valid_model(value):
        return []
    return [(key, value, "config")]


def _extract_from_comment_line(line: str) -> List[str]:
    """从注释行提取模型名"""
    models = []
    # 示例：CHAT_MODEL=deepseek-chat 或 示例：deepseek-chat
    for m in re.finditer(
        r"(?:示例|可选值|默认值)[：:]\s*(?:[A-Z_]+_MODEL=)?([a-zA-Z0-9\-\._]+)",
        line,
    ):
        models.append(m.group(1).strip())

    # 列表项：- model：
    for m in re.finditer(r"-\s+([a-zA-Z0-9\-\._]+)[：:]", line):
        models.append(m.group(1).strip())

    # 引号内模型名
    for m in re.finditer(r'"([a-zA-Z0-9\-\._]+)"', line):
        models.append(m.group(1).strip())

    # 逗号分隔的模型列表（如 qwen-turbo, qwen-plus）
    for m in re.finditer(r"([a-zA-Z0-9\-\._]+)\s*,\s*", line):
        models.append(m.group(1).strip())

    # KEY=model 格式（注释中）
    for m in re.finditer(r"[A-Z_]+_MODEL=([a-zA-Z0-9\-\._]+)", line):
        models.append(m.group(1).strip())

    return [x for x in models if _is_valid_model(x)]


def parse_env_models(
    project_root: Path | None = None,
) -> Tuple[List[Dict], List[str]]:
    """
    解析 .env（或 env.example）中的模型配置。

    Args:
        project_root: 项目根目录，默认从当前文件推断

    Returns:
        (models, unique_models)
        - models: 每项含 key, label, model, source ("config" | "comment")
        - unique_models: 去重后的模型名列表
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    env_path = project_root / ".env"
    if not env_path.exists():
        env_path = project_root / "env.example"

    if not env_path.exists():
        return [], []

    text = env_path.read_text(encoding="utf-8", errors="replace")
    models: List[Dict] = []
    seen_models: set = set()
    unique_models: List[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # 配置行
        if not stripped.startswith("#"):
            items = _extract_from_config_line(stripped)
            for key, model, source in items:
                models.append({
                    "key": key,
                    "label": MODEL_KEY_LABELS.get(key, key),
                    "model": model,
                    "source": source,
                })
                if model not in seen_models:
                    seen_models.add(model)
                    unique_models.append(model)
            continue

        # 注释行
        for model in _extract_from_comment_line(stripped):
            models.append({
                "key": None,
                "label": None,
                "model": model,
                "source": "comment",
            })
            if model not in seen_models:
                seen_models.add(model)
                unique_models.append(model)

    return models, unique_models
