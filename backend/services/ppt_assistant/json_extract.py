"""从 LLM 回复中尽力解析单个 JSON object（可测、无网络）。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict


def parse_llm_json_object(text: str) -> Dict[str, Any]:
    """
    抽取第一个可解析的 JSON 对象。支持外层 markdown 代码块。
    失败时抛 ValueError。
    """
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty llm response")

    # 去掉 ```json ... ``` 或 ``` ... ```
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()

    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 找最外层 {...}
    start = raw.find("{")
    if start == -1:
        raise ValueError("no json object in response")
    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(raw[start : i + 1])
                except json.JSONDecodeError as e:
                    raise ValueError(f"invalid json: {e}") from e
    raise ValueError("unbalanced braces in response")
