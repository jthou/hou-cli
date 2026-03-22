"""首页简报：从任务结果构建事实包并生成叙述型报告（设计见 docs/design/01-home-briefing-report-agent-design.md）。"""

from backend.services.home_briefing.fact_pack import build_fact_pack_from_tasks
from backend.services.home_briefing.report_generate import generate_briefing_markdown

__all__ = ["build_fact_pack_from_tasks", "generate_briefing_markdown"]
