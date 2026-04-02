"""PPT 助手：长文 → ppt_elements → slide_deck（与 API / CLI 共用逻辑）。"""

from backend.services.ppt_assistant.service import (
    extract_ppt_elements,
    generate_slide_deck,
    run_ppt_pipeline,
)
from backend.services.ppt_assistant.markdown import slide_deck_to_markdown

__all__ = [
    "extract_ppt_elements",
    "generate_slide_deck",
    "run_ppt_pipeline",
    "slide_deck_to_markdown",
]
