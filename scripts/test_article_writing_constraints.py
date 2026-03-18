#!/usr/bin/env python3
"""
写作助手约束测试：验证「按用户思路改写」时输出遵循结构、不擅自扩展。
时间：2025-03-17；理由：用户反馈 LLM 过度发挥；方法：调用 stream_process 检查输出。

环境变量：
- ARTICLE_WRITING_TEST_MODEL: 模型名，默认 qwen-max
- ARTICLE_WRITING_STRICT: 1/true/yes 时使用严格约束（字数限制）

示例：
  python scripts/test_article_writing_constraints.py
  ARTICLE_WRITING_STRICT=1 python scripts/test_article_writing_constraints.py
  ARTICLE_WRITING_TEST_MODEL=qwen3-max python scripts/test_article_writing_constraints.py
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.agent.prompts import WRITING_CONSTRAINT_VIOLATION_PATTERNS

# ---------------------------------------------------------------------------
# 测试用例：项目密级三分法
# ---------------------------------------------------------------------------

# 用户给出的原始思路（待改写的内容）
USER_TOPIC = """基于公司现有的项目密级设定，可以将项目分为高密级项目、常规研发项目和普通项目。对于高涉密项目（必须置于物理与逻辑双重隔离的环境），常规研发项目目前已采用企业专属云网络（VPC）方案，而对于普通项目，只受公司制度和国家法律约束。"""

# 改写指令（约束 LLM 行为）
REWRITE_INSTRUCTION = "按照我这个思路改写。别瞎发挥。"

# 可选的强化约束（ARTICLE_WRITING_STRICT=1 时使用）
REWRITE_INSTRUCTION_STRICT = "按照我这个思路改写。每类只写一段，总字数 500 字以内，不要加总结小节。别瞎发挥。"

# 参考信息（本用例无参考）
REFERENCE_INFO = "（无）"

# 任务模板：写作助手接收的格式
TASK_TEMPLATE = """【参考信息】
{reference_info}

【用户提问】
{user_question}
"""

# ---------------------------------------------------------------------------
# 断言条件：期望输出满足的检查项
# ---------------------------------------------------------------------------

# 用户给出的三类，输出中必须包含（至少作为子串）
REQUIRED_STRUCTURE = ["高密级", "常规研发", "普通项目"]

# 技术方案/术语，输出中应包含至少 2 个
REQUIRED_TERMS = ["VPC", "物理", "逻辑", "隔离"]

# 不期望出现的过度发挥：与 prompts.WRITING_CONSTRAINTS 语义对应，后端与测试共用
UNWANTED_PATTERNS = WRITING_CONSTRAINT_VIOLATION_PATTERNS

# 输出长度上限（字）；None 表示不限制。测试以约束遵循为主，不因字数判失败
MAX_OUTPUT_LENGTH = None


def _extract_content(chunks):
    skip = ("__DEBUG__", "__TOOL__", "__STATUS__", "__PROGRESS__", "__EVALUATION__")
    return "".join(c for c in chunks if not any(c.startswith(p) for p in skip))


async def run_test() -> tuple[bool, str, str]:
    from backend.core.agent.orchestrator import Orchestrator

    model = os.getenv("ARTICLE_WRITING_TEST_MODEL", "qwen-max")
    use_strict = os.getenv("ARTICLE_WRITING_STRICT", "").lower() in ("1", "true", "yes")
    instruction = REWRITE_INSTRUCTION_STRICT if use_strict else REWRITE_INSTRUCTION
    user_question = f"{USER_TOPIC}\n{instruction}"

    print(f"使用模型: {model}")
    print(f"约束模式: {'严格（字数限制）' if use_strict else '默认'}")
    print(f"用户思路: {USER_TOPIC[:60]}...")
    print(f"改写指令: {instruction}")
    print()

    o = Orchestrator()
    content_chunks = []

    task = TASK_TEMPLATE.format(
        reference_info=REFERENCE_INFO,
        user_question=user_question,
    )

    context = {"context_type": "article_writing", "model": model}

    try:
        async for chunk in o.stream_process(task, context=context):
            if not any(
                chunk.startswith(p)
                for p in ("__DEBUG__", "__TOOL__", "__STATUS__", "__PROGRESS__", "__EVALUATION__")
            ):
                content_chunks.append(chunk)

        content = _extract_content(content_chunks)
        if len(content) < 100:
            return False, f"输出过短: {len(content)} 字", content

        if MAX_OUTPUT_LENGTH is not None and len(content) > MAX_OUTPUT_LENGTH:
            return False, f"输出过长: {len(content)} 字，上限 {MAX_OUTPUT_LENGTH}", content

        # 检查必需结构
        missing = [s for s in REQUIRED_STRUCTURE if s not in content]
        if missing:
            return False, f"缺少用户要求的结构: {missing}", content

        # 检查关键术语
        found_terms = [t for t in REQUIRED_TERMS if t in content]
        if len(found_terms) < 2:
            return False, f"关键术语不足，仅含: {found_terms}", content

        # 检查过度发挥（出现则判失败）
        unwanted_found = [p for p in UNWANTED_PATTERNS if p in content]
        if unwanted_found:
            return False, f"检测到过度发挥: {unwanted_found}", content

        return True, f"通过 (len={len(content)}, 含结构={REQUIRED_STRUCTURE}, 术语={found_terms})", content
    except Exception as e:
        return False, f"异常: {e}", ""


async def main():
    print("=" * 60)
    print("写作助手约束测试：按用户思路改写、不擅自扩展")
    print("=" * 60)
    ok, msg, content = await run_test()
    status = "✅" if ok else "❌"
    print(f"  {status} {msg}")
    print()
    print("--- 完整输出 ---")
    print(content)
    print("--- 结束 ---")
    return 0 if ok else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
