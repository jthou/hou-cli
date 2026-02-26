"""管道：从上游 result 按 input_bindings 路径解析出 metadata 片段，供 Worker 与 API 共用。"""
import json
from typing import Dict, Any, Optional


def resolve_input_bindings_from_result(
    upstream_result: Any,
    input_bindings: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    """
    从上游 result 对象和 input_bindings 映射解析出本任务会用到的 metadata 片段。

    Args:
        upstream_result: 上游任务的 result（可为 dict 或已解析的 object）
        input_bindings: 如 {"input_file": "result.data.output_file"}

    Returns:
        解析出的键值对，仅包含成功解析的字段。
    """
    if not input_bindings or not isinstance(input_bindings, dict):
        return {}
    root = upstream_result
    if isinstance(root, str):
        try:
            root = json.loads(root)
        except (TypeError, ValueError):
            return {}
    if not isinstance(root, dict):
        return {}
    out = {}
    for key, path in input_bindings.items():
        if not path or not isinstance(path, str):
            continue
        path = path.strip()
        if path.startswith("result."):
            path = path[7:]
        if not path:
            continue
        value = root
        for p in path.split("."):
            if value is None:
                break
            value = value.get(p) if isinstance(value, dict) else None
        if value is not None:
            out[key] = value
    return out
