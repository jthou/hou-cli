# 漫画生成功能设置指南

## 背景说明

漫画生成功能需要图像生成能力，目前系统支持两种模型提供商：

1. **TheTurbo.ai** - 仅支持文本处理（**不支持漫画生成**）
2. **百炼平台** - 支持图像生成（**推荐用于漫画生成**）

## 设置步骤

### 1. 配置百炼平台 API 密钥

在 `.env` 文件中添加：

```bash
# 百炼或 DashScope API 密钥（需要图像生成权限）
BAILIAN_API_KEY=your_bailian_api_key
# 或者
DASHSCOPE_API_KEY=your_dashscope_api_key

# 漫画生成默认模型
COMIC_DEFAULT_MODEL=qwen3-max
```

### 2. 启动 LiteLLM 代理

漫画生成需要通过 LiteLLM 将 Anthropic API 请求转换为 DashScope 格式：

```bash
# 启动漫画生成专用的 LiteLLM 代理
python scripts/start_litellm_comic_proxy.py
```

保持此代理在后台运行。

### 3. 验证安装

确保必要的技能已安装：

```bash
# 安装漫画生成技能
npx skills add JimLiu/baoyu-skills --skill baoyu-comic -a cursor -y

# 创建必要的符号链接
mkdir -p .claude/skills
ln -sf $(pwd)/.agents/skills/baoyu-comic $(pwd)/.claude/skills/baoyu-comic
```

### 4. 运行测试

使用以下代码验证配置：

```python
from backend.core.agent.skills.comic.skill import ComicSkill
import asyncio

async def test_comic():
    skill = ComicSkill()
    result = await skill.execute({
        "source": "# 测试\n\n这是一个测试漫画。",
        "art": "ligne-claire",
        "tone": "neutral",
        "llm_model": "qwen3-max"  # 使用百炼模型
    })
    print(f"成功: {result.success}")
    if not result.success:
        print(f"错误: {result.error}")

asyncio.run(test_comic())
```

## 常见问题

### Q: 为什么 TheTurbo.ai 模型无法生成漫画？
A: TheTurbo.ai 主要代理 Anthropic Claude 模型，这些模型通常只支持文本对话，不支持图像生成功能。

### Q: 使用百炼模型仍无法生成漫画怎么办？
A: 检查以下几点：
1. API 密钥是否具备图像生成权限
2. LiteLLM 代理是否正在运行（端口 4000）
3. 模型名称是否正确（如 `qwen3-max`）
4. 网络连接是否正常

## 架构说明

漫画生成流程：
1. ComicSkill 接收输入内容
2. 调用 baoyu-comic Agent
3. 通过 Anthropic SDK 发送请求
4. LiteLLM 代理将请求转换为 DashScope 格式
5. 百炼平台生成漫画内容
6. 返回 PDF 格式的漫画

这种设计允许系统同时支持多种模型提供商，但漫画生成功能依赖于图像生成能力。