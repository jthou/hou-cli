"""字幕叠加技能实现"""
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from backend.core.agent.skills.base import Skill, SkillResult, SkillParameter
from backend.core.agent.skills.executor import SkillExecutor

logger = logging.getLogger(__name__)


class VideoSubtitleOverlaySkill(Skill):
    """字幕叠加技能 - 在视频上叠加字幕，支持 SRT 格式，可自定义字幕样式"""
    
    def __init__(self, executor: SkillExecutor):
        """
        初始化字幕叠加技能
        
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
        执行字幕叠加技能
        
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
            config=skill_config
        )
        
        return result

