#!/usr/bin/env python3
# 时间：2026-04-11；理由：在 Cursor 内通过 MCP 调用与 replay_article_writing_cli 一致的 article_writing 编排，默认 qwen3-max；方法：FastMCP stdio + Orchestrator.stream_process
# 时间：2026-04-11；理由：承接 ai-hot-news-summary 产出再按 wechat-mp-article-writing 成稿；方法：专用参考块 + 短约束后缀注入 user task（不整本贴 Skill）
"""
百炼 / 仓库 LLM 配置下的「写作助手同款」MCP（stdio）。

依赖：已配置 .env（如 BAILIAN_API_KEY），且已安装 `mcp`（见 requirements.txt）。

Cursor 配置示例（用户级 `~/.cursor/mcp.json` 或项目 `.cursor/mcp.json`）：

  {
    "mcpServers": {
      "hou-bailian-article": {
        "command": "python3",
        "args": ["/ABS/PATH/TO/hou-cli/scripts/mcp_bailian_article_writing_server.py"],
        "cwd": "/ABS/PATH/TO/hou-cli"
      }
    }
  }

将 `/ABS/PATH/TO/hou-cli` 换为本机仓库根目录；`command` 指向该环境下的 Python（有依赖即可）。

工具名：`hou_article_writing`
- `question`（必填）、`model`（默认 qwen3-max）、`references`（可选）、`current_article_markdown`（可选改稿）。
- **热点摘要 → 公众号**：把 `ai_hot_news_digest` / Skill「今日 AI 热点」生成的 Markdown 全文传入 **`hot_news_digest_markdown`**；会自动作为首条参考并追加与 `.agents/skills/wechat-mp-article-writing` 对齐的成稿硬约束。
- 若摘要已自行放进 `references` 但仍要公众号约束：设 **`wechat_mp_article_mode=true`**。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 与 replay_article_writing_cli 一致，避免写作场景被技能预匹配抢答
os.environ.setdefault("DISABLE_SKILL_PREMATCH_FOR_ASSISTANTS", "true")

_META_PREFIXES = (
    "__DEBUG__",
    "__TOOL__",
    "__STATUS__",
    "__PROGRESS__",
    "__EVALUATION__",
    "__ORCH_TRACE__",
    "__CONFIRM__",
    "__CTX_META__",  # 时间：2026-04-11；理由：编排器下发的 JSON 元块不应进入 MCP 工具返回；方法：与 quiet_meta 过滤一致
)


def _is_meta_chunk(chunk: str) -> bool:
    return any(chunk.startswith(p) for p in _META_PREFIXES)


# 与 wechat-mp-article-writing 要点对齐的短注入（整 Skill 过长；仅保留与「由摘要改长文」强相关的硬约束）
_WECHAT_MP_FROM_DIGEST_SUFFIX = """【成稿形态·微信公众号长文】
素材含「今日 AI 热点」类深度摘要。请**新写一篇**可直接排版的 Markdown 长文：**第一行**即为 `# 标题` 或正文首句。
禁止整段/成章输出：「检索说明」「检索基准」「交叉观察」独立节、「参考资料」大段罗列；禁止开篇「本文基于…整理」「面向…读者」及正文内「摘要/检索/交叉验证」等元叙事用语。
信源在正文里用自然句**嵌入 Markdown 链接**；`##` 宜 **2～4 个**，小标题写**具体事实或判断**，忌「一节一条新闻」目录体。在事实与链接边界内**改写为原创叙述**，禁大段照抄摘要原文。
**中文术语**：泛指 AI agents 时写 **「智能体」**，勿在叙述句中单独使用英文 Agent；产品官方名（如 Microsoft Agent Framework）保留英文，可首次括注（智能体…）。"""


def _compose_user_question(
    question: str,
    *,
    wechat_mp_article_mode: bool,
    hot_news_digest_non_empty: bool,
) -> str:
    q = (question or "").strip()
    inject = wechat_mp_article_mode or hot_news_digest_non_empty
    if not inject:
        return q
    if q:
        return f"{q}\n\n{_WECHAT_MP_FROM_DIGEST_SUFFIX}"
    return _WECHAT_MP_FROM_DIGEST_SUFFIX


def _build_reference_blocks(
    *,
    hot_news_digest_markdown: str | None,
    references: list[str] | None,
) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    digest = (hot_news_digest_markdown or "").strip()
    if digest:
        blocks.append({"title": "【参考·今日 AI 热点深度摘要】", "content": digest})
    for j, raw in enumerate(references or []):
        text = (raw or "").strip()
        if text:
            blocks.append({"title": f"参考{j + 1}", "content": text})
    return blocks


async def _stream_article_writing(
    task: str,
    *,
    model: str,
    quiet_meta: bool,
    extra_context: dict | None = None,
) -> str:
    """与 scripts/replay_article_writing_cli.run_stream 对齐。"""
    from backend.core.agent.orchestrator import Orchestrator

    o = Orchestrator()
    parts: list[str] = []
    context: dict = {"context_type": "article_writing", "model": model}
    if extra_context:
        context.update(extra_context)
    async for chunk in o.stream_process(task, context=context):
        if quiet_meta and _is_meta_chunk(chunk):
            continue
        parts.append(chunk)
    return "".join(parts)


def _build_mcp() -> "FastMCP":
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "hou_bailian_article",
        instructions=(
            "hou-cli article_writing 编排，默认 qwen3-max。可将 ai-hot-news-summary / ai_hot_news_digest "
            "产出的 Markdown 传入 hot_news_digest_markdown，一键按微信公众号成稿约束写作。"
        ),
    )

    @mcp.tool()
    async def hou_article_writing(
        question: str,
        model: str = "qwen3-max",
        references: list[str] | None = None,
        current_article_markdown: str | None = None,
        hot_news_digest_markdown: str | None = None,
        wechat_mp_article_mode: bool = False,
    ) -> str:
        """公众号长文新写或改稿（与 Web 写作助手同源编排）。
        hot_news_digest_markdown：今日 AI 热点任务或 Skill 产出的摘要全文，将作为首条参考并自动启用公众号成稿约束。
        wechat_mp_article_mode：无 digest 时若仍要公众号约束（例如摘要已自行放入 references），设为 true。
        """
        from backend.core.agent.article_writing_message_contract import (
            build_message_for_model,
        )

        digest_nonempty = bool((hot_news_digest_markdown or "").strip())
        q = _compose_user_question(
            question,
            wechat_mp_article_mode=wechat_mp_article_mode,
            hot_news_digest_non_empty=digest_nonempty,
        )
        if not q.strip():
            return "错误：question 不能为空；若只传摘要，请在 question 中写明篇幅/受众/角度等至少一条指令。"

        blocks = _build_reference_blocks(
            hot_news_digest_markdown=hot_news_digest_markdown,
            references=references,
        )

        base_task = build_message_for_model(blocks, q)
        extra: dict | None = None
        art = (current_article_markdown or "").strip()
        if art:
            extra = {"replay_current_article": art}

        m = (model or "").strip() or "qwen3-max"
        return await _stream_article_writing(
            base_task,
            model=m,
            quiet_meta=True,
            extra_context=extra,
        )

    return mcp


def main() -> None:
    mcp = _build_mcp()
    mcp.run()


if __name__ == "__main__":
    main()
