"""视频字幕提取技能实现"""
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from backend.core.agent.skills.base import Skill, SkillResult, SkillParameter
from backend.core.agent.skills.executor import SkillExecutor

logger = logging.getLogger(__name__)


class VideoExtractSrtSkill(Skill):
    """视频字幕提取技能 - 下载视频、提取音频、生成字幕文件（SRT格式）"""
    
    def __init__(self, executor: SkillExecutor):
        """
        初始化视频字幕提取技能
        
        Args:
            executor: 技能执行器
        """
        # 从技能目录中的 YAML 文件加载配置
        skill_dir = Path(__file__).parent
        config_path = skill_dir / "skill.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"技能配置文件未找到: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 解析参数
        parameters = []
        for param_config in config.get('parameters', []):
            parameters.append(SkillParameter(
                name=param_config['name'],
                type=param_config.get('type', 'string'),
                description=param_config.get('description', ''),
                required=param_config.get('required', True),
                default=param_config.get('default'),
                enum=param_config.get('enum')
            ))
        
        # 解析依赖
        dependencies = {
            'tools': [tool['name'] for tool in config.get('dependencies', {}).get('tools', [])],
            'skills': config.get('dependencies', {}).get('skills', [])
        }
        
        super().__init__(
            name=config['name'],
            description=config['description'],
            version=config.get('version', '1.0.0'),
            category=config.get('category', 'general'),
            priority=config.get('priority', 'P1'),
            parameters=parameters,
            dependencies=dependencies
        )
        
        self.executor = executor
        self.workflow = config.get('workflow', {})
        self.config = config.get('config', {})
    
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> SkillResult:
        """
        执行视频字幕提取技能
        
        Args:
            parameters: 技能参数
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        # 验证参数
        is_valid, error_msg = self.validate_parameters(parameters)
        if not is_valid:
            return SkillResult(success=False, error=error_msg)
        
        # 获取任务管理器（如果提供）
        task_manager = context.get('task_manager') if context else None
        task_id = context.get('task_id') if context else None
        
        # 设置进度回调（用于更新任务进度）
        def progress_callback(progress_or_message, message: str = ""):
            """进度回调函数，适配不同的调用方式"""
            if task_manager and task_id:
                # 如果第一个参数是字符串，说明是 executor.report_progress 的调用方式
                if isinstance(progress_or_message, str):
                    # 只传递消息，保持当前进度百分比不变
                    current_task = task_manager._tasks.get(task_id)
                    if current_task:
                        current_progress = current_task.progress if hasattr(current_task, 'progress') else 0
                        task_manager.update_task_progress(task_id, current_progress, progress_or_message)
                else:
                    # 第一个参数是进度值（整数）
                    task_manager.update_task_progress(task_id, progress_or_message, message)
        
        if context:
            context['progress_callback'] = progress_callback
        
        # 设置进度回调
        if context and 'progress_callback' in context:
            self.executor.set_progress_callback(context['progress_callback'])
            self.set_progress_callback(context['progress_callback'])
        
        # 合并配置
        skill_config = {**self.config}
        if context and 'config' in context:
            skill_config.update(context['config'])
        
        # 执行工作流
        result = await self.executor.execute_workflow(
            workflow=self.workflow,
            parameters=parameters,
            config=skill_config,
            external_context=context
        )
        
        return result

