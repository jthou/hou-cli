# Video Summary Skill

视频摘要技能 - 完整的视频内容分析工具

## 目录结构

```
video_summary/
├── __init__.py              # 技能实现
├── skill.yaml               # 技能配置（工作流定义）
├── skill.md                 # 技能文档
├── README.md                # 本文件
├── scripts/                 # 辅助脚本
│   └── (待添加)
├── assets/                  # 资源文件
│   └── (待添加)
└── references/              # 参考资料
    ├── timestamp_extraction.md
    ├── interactive_refinement.md
    └── long_text_handling.md
```

## 快速开始

### 基本使用

```python
from backend.core.agent.skills.video_summary import VideoSummarySkill
from backend.core.agent.skills.executor import SkillExecutor

# 初始化
executor = SkillExecutor(tool_registry, llm_service)
skill = VideoSummarySkill(executor)

# 执行技能
result = await skill.execute({
    "url": "https://www.bilibili.com/video/BV1B5xkzPEhx",
    "summary_length": 200
})
```

### 通过 Orchestrator 使用

```python
from backend.core.agent.orchestrator import Orchestrator

orchestrator = Orchestrator()

# 自动匹配并执行技能
async for chunk in orchestrator.stream_process("帮我分析这个视频并生成摘要 https://www.bilibili.com/video/BV1B5xkzPEhx"):
    print(chunk, end='')
```

## 文档

- [技能文档](skill.md) - 完整的功能说明和使用指南
- [时间戳提取](references/timestamp_extraction.md) - 时间戳提取技术文档
- [交互式摘要调整](references/interactive_refinement.md) - 交互式调整机制
- [长文本处理](references/long_text_handling.md) - 长文本处理策略

## 配置

技能配置在 `skill.yaml` 文件中，包括：
- 参数定义
- 工具依赖
- 工作流定义
- 错误处理策略
- 配置参数

## 开发

### 添加新功能

1. 修改 `skill.yaml` 添加新的工作流步骤
2. 更新 `skill.md` 文档
3. 在 `references/` 中添加技术文档（如需要）

### 测试

```bash
# 运行技能测试
python -m pytest backend/core/agent/skills/video_summary/tests/
```

## 许可证

与主项目相同




