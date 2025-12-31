"""流程识别器"""
from typing import Dict, Any
# from backend.services.llm.llm_service import LLMService

class WorkflowIdentifier:
    """流程识别器，决定使用 SOP 还是动态编排"""
    
    def __init__(self):
        # self.llm_service = LLMService()
        self.workflow_registry = {
            "pdf_analysis": "pdf_analysis_sop.yaml",
            "code_review": "code_review_sop.yaml",
            # ... 其他 SOP
        }
    
    async def identify(self, task: str) -> Dict[str, Any]:
        """识别任务类型，决定执行模式"""
        # TODO: 实现任务识别逻辑
        return {
            "mode": "dynamic",
            "workflow_name": None,
            "confidence": 0.5
        }

