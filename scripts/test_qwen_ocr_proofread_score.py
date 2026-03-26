#!/usr/bin/env python3
"""
用百炼 Qwen 对「OCR 拼接噪稿」做校对，再让同一模型对照人工参考稿打分。

依赖：已配置 BAILIAN_API_KEY；在项目根目录执行：
  python scripts/test_qwen_ocr_proofread_score.py

可选环境变量：
  OCR_PROOFREAD_MODEL   默认 qwen-max（与 backend 百炼文本模型一致即可）
  OCR_PROOFREAD_JUDGE_MODEL  默认与 OCR_PROOFREAD_MODEL 相同
  OCR_PROOFREAD_TIMEOUT_SEC  单次 API 超时秒数，默认 300（长文 LaTeX 校对可能较慢）

说明：fixtures 仅约 6～7KB，远低于 qwen-max 常见 32k 上下文；若「卡住」多为网络/代理/Key
或运行环境杀进程，而非「模型吃不下」。本脚本用 asyncio.wait_for 包一层，超时会给明确报错。

注意：LLMService 底层 httpx 默认 LLM_READ_TIMEOUT=60s，会先触发 ReadTimeout；
本脚本会在创建 LLMService 前将 LLM_READ_TIMEOUT 设为 max(原值, OCR_PROOFREAD_TIMEOUT_SEC)。

输入：scripts/fixtures/imu_ocr_sloppy.md
参考：scripts/fixtures/imu_ocr_reference_human.md
输出：scripts/output/qwen_proofread_result.md + 控制台打印评分 JSON
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.load_env import load_env

load_env()

FIXTURES = ROOT / "scripts" / "fixtures"
OUT_DIR = ROOT / "scripts" / "output"
SLOPPY = FIXTURES / "imu_ocr_sloppy.md"
REFERENCE = FIXTURES / "imu_ocr_reference_human.md"

PROOFREAD_SYSTEM = """你是专业技术编辑。用户正文来自电子书分屏 OCR，常有：
- 分段拼接造成的重复段落、重复图注、多余分隔线 ---；
- 标题层级不统一（如 (3) 应为 ##### (3)）；
- 少量错字、漏字、标点与半角全角混乱；
- 公式与 LaTeX 需尽量保留，勿随意改符号；明显 OCR 毁版可略作排版性整理并加简短编者注。

请输出**仅一份校对后的完整 Markdown 正文**，不要前言后记。禁止编造书中没有的定理、数据或段落；可删重复、可改明显笔误，不要扩写新观点。"""

JUDGE_SYSTEM = """你是评测员。给定三份文本（JSON 字段）：
- original：OCR 噪稿
- candidate：模型校对稿
- reference：人工参考稿（金标准，仅用于打分参照）

请只输出**一个 JSON 对象**（不要 markdown 代码围栏），键为：
{
  "scores": {
    "deduplication": <1-10 整数，去重与合并重复段落是否接近参考稿>,
    "structure": <1-10，标题层级与图注位置是否清晰合理>,
    "formula_preservation": <1-10，公式/LaTeX 是否保持且未乱改>,
    "fidelity": <1-10，是否未胡编内容、未大段臆测>,
    "overall": <1-10，综合质量>
  },
  "brief_zh": "<一两句中文简评 candidate 相对 reference 的主要差距>"
}
分数越高越好。若 candidate 与 reference 在要点上等价，overall 可给 8-10。"""


def _strip_json_fence(s: str) -> str:
    t = (s or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```\s*$", "", t)
    return t.strip()


async def _chat(llm, messages: list, temperature: float, timeout_sec: float) -> str:
    prev = llm.temperature
    llm.temperature = temperature
    try:
        return (
            await asyncio.wait_for(llm.chat(messages=messages), timeout=timeout_sec) or ""
        )
    finally:
        llm.temperature = prev


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sloppy = SLOPPY.read_text(encoding="utf-8")
    reference = REFERENCE.read_text(encoding="utf-8")
    print(
        f"输入噪稿 {len(sloppy)} 字符、参考稿 {len(reference)} 字符（远小于 qwen-max 级上下文，非体积问题）",
        flush=True,
    )

    model = (os.getenv("OCR_PROOFREAD_MODEL") or "qwen-max").strip()
    judge_model = (os.getenv("OCR_PROOFREAD_JUDGE_MODEL") or model).strip()
    timeout_sec = float((os.getenv("OCR_PROOFREAD_TIMEOUT_SEC") or "300").strip() or "300")
    prev_llm_read = os.environ.get("LLM_READ_TIMEOUT")
    llm_read = float((prev_llm_read or "60").strip() or "60")
    os.environ["LLM_READ_TIMEOUT"] = str(max(llm_read, timeout_sec))

    from backend.services.llm.llm_service import LLMService

    llm = LLMService(model=model, temperature=0.2)
    print(f"=== 1/2 校对：model={model}，超时 {timeout_sec}s ===", flush=True)
    proof_messages = [
        {"role": "system", "content": PROOFREAD_SYSTEM},
        {
            "role": "user",
            "content": "以下是需要校对的 Markdown 正文：\n\n" + sloppy,
        },
    ]
    try:
        proofread = (await _chat(llm, proof_messages, 0.2, timeout_sec)).strip()
    except asyncio.TimeoutError:
        print(f"❌ 校对阶段超时（>{timeout_sec}s）。检查网络、BAILIAN_API_KEY、或增大 OCR_PROOFREAD_TIMEOUT_SEC", flush=True)
        raise
    out_md = OUT_DIR / "qwen_proofread_result.md"
    out_md.write_text(proofread, encoding="utf-8")
    print(f"已写入 {out_md.relative_to(ROOT)} ，长度 {len(proofread)} 字符\n", flush=True)

    llm_judge = LLMService(model=judge_model, temperature=0.1)
    print(f"=== 2/2 打分：model={judge_model}，超时 {timeout_sec}s ===", flush=True)
    payload = {
        "original": sloppy[:120_000],
        "candidate": proofread[:120_000],
        "reference": reference[:120_000],
    }
    judge_messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {
            "role": "user",
            "content": "请按 system 要求只输出 JSON：\n"
            + json.dumps(payload, ensure_ascii=False),
        },
    ]
    try:
        raw_judge = (await _chat(llm_judge, judge_messages, 0.1, timeout_sec)).strip()
    except asyncio.TimeoutError:
        print(f"❌ 打分阶段超时（>{timeout_sec}s）", flush=True)
        raise
    parsed = None
    try:
        parsed = json.loads(_strip_json_fence(raw_judge))
    except json.JSONDecodeError:
        print("评委返回非 JSON，原文如下：\n", raw_judge[:4000])
        (OUT_DIR / "qwen_judge_raw.txt").write_text(raw_judge, encoding="utf-8")
        sys.exit(1)

    (OUT_DIR / "qwen_judge_scores.json").write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(parsed, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
