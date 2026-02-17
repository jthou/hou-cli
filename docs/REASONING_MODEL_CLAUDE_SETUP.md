# 将推理模型切换为 Claude 配置指南

## 概述

本指南说明如何将系统的推理模型从默认的 `deepseek-reasoner` 切换为 Claude 模型（通过 TheTurbo.ai 网关）。

## 为什么使用 Claude 作为推理模型？

Claude 模型（特别是 Opus 4.5 系列）在以下方面表现优秀：
- **复杂推理**：擅长多步骤推理和问题解决
- **工具选择**：能够更准确地选择和使用工具
- **任务分解**：能够将复杂任务分解为可执行的子任务
- **策略制定**：能够制定更有效的执行策略

## 配置步骤

### 步骤 1: 获取 TheTurbo.ai 网关 API Key

1. 访问 [TheTurbo.ai](https://theturbo.ai) 注册并登录
2. 在控制台中创建 API Key
3. 复制 API Key（格式类似：`sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`）

### 步骤 2: 配置环境变量

在 `.env` 文件中添加或修改以下配置：

```bash
# TheTurbo.ai 网关 API 密钥（必需）
TURBOGATEWAY_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 推理模型配置（切换到 Claude）
REASONING_MODEL=claude-opus-4-5-20251101
```

### 步骤 3: 验证配置

运行以下命令验证配置：

```bash
python -c "
from backend.services.llm.model_config import get_model_config_manager
config_manager = get_model_config_manager()

# 检查推理模型配置
reasoning_model = config_manager.get_reasoning_model()
print(f'推理模型: {reasoning_model}')

# 检查模型配置
try:
    config = config_manager.get_model_config(reasoning_model)
    print(f'提供商: {config.provider}')
    print(f'API Key 环境变量: {config.api_key_env}')
    print(f'Base URL: {config.default_base_url}')
    
    # 检查 API Key 是否设置
    api_key = config_manager.get_api_key(reasoning_model)
    print(f'✅ API Key 已设置（长度: {len(api_key)}）')
except Exception as e:
    print(f'❌ 配置错误: {e}')
"
```

## 推荐的 Claude 模型

### 推理任务推荐模型

| 模型名称 | 特点 | 适用场景 |
|---------|------|---------|
| `claude-opus-4-5-20251101` | **最强推理能力**，支持 reasoning_effort 参数 | 复杂推理、工具选择、任务分解（**推荐**） |
| `claude-sonnet-4-5-20250929` | 平衡性能和成本，支持 reasoning_effort 参数 | 一般推理任务 |
| `claude-3-5-haiku-20241022` | 快速响应，成本较低 | 简单推理任务 |

### 配置示例

**推荐配置（最强推理能力）**：
```bash
REASONING_MODEL=claude-opus-4-5-20251101
```

**平衡配置（性能和成本平衡）**：
```bash
REASONING_MODEL=claude-sonnet-4-5-20250929
```

**快速配置（快速响应）**：
```bash
REASONING_MODEL=claude-3-5-haiku-20241022
```

## 支持的 Claude 模型列表

通过 TheTurbo.ai 网关支持的 Claude 模型：

### Claude Opus 4 系列（推荐用于推理）
- `claude-opus-4-20250514` - Opus 4 基础版
- `claude-opus-4-1-20250805` - Opus 4.1
- `claude-opus-4-5-20251101` - **Opus 4.5（推荐）**

### Claude Sonnet 4 系列
- `claude-sonnet-4-20250514` - Sonnet 4 基础版
- `claude-sonnet-4-5-20250929` - Sonnet 4.5

### Claude Haiku 4 系列
- `claude-haiku-4-5-20251001` - Haiku 4.5

### Claude 3.5 系列
- `claude-3-5-haiku-20241022` - Haiku 3.5
- `claude-3-5-sonnet-20241022` - Sonnet 3.5

### Claude 3.7 系列
- `claude-3-7-sonnet-20250219` - Sonnet 3.7（支持 reasoning_effort）

## 模型特性说明

### reasoning_effort 参数支持

部分 Claude 模型支持 `reasoning_effort` 参数，可以控制推理的深度：

- **支持的模型**：
  - `claude-opus-4-5-20251101`
  - `claude-sonnet-4-5-20250929`
  - `claude-3-7-sonnet-20250219`
  - 其他 Opus 4 和 Sonnet 4 系列模型

- **参数值**：
  - `low`：快速推理（默认）
  - `medium`：平衡推理
  - `high`：深度推理（更准确但更慢）

- **使用方式**：
  系统会自动根据任务复杂度调整 `reasoning_effort` 参数，无需手动配置。

## 测试配置

### 运行模型选择测试

```bash
# 测试模型选择逻辑
pytest backend/core/agent/tests/orchestration/test_model_selection.py -v

# 测试模型切换功能
pytest backend/core/agent/tests/orchestration/test_model_switcher.py -v
```

### 运行 Claude 模型测试

```bash
# 测试 TheTurbo.ai 网关的 Anthropic 模型
pytest backend/services/llm/tests/test_turbogateway_anthropic.py -v
```

### 手动测试推理模型

```python
from backend.services.llm.model_config import get_model_config_manager
from backend.services.llm.llm_service import LLMService

# 获取配置管理器
config_manager = get_model_config_manager()

# 获取推理模型
reasoning_model = config_manager.get_reasoning_model()
print(f"推理模型: {reasoning_model}")

# 创建 LLM 服务
llm_service = LLMService()

# 切换到推理模型
llm_service.set_model(reasoning_model)

# 测试推理任务
response = await llm_service.chat(
    user_prompt="分析这个任务需要哪些工具：下载视频并提取字幕"
)
print(f"响应: {response}")
```

## 配置验证清单

- [ ] `TURBOGATEWAY_API_KEY` 已设置
- [ ] `REASONING_MODEL` 已设置为 Claude 模型
- [ ] 运行配置验证脚本，确认配置正确
- [ ] 运行模型选择测试，确认模型选择逻辑正常
- [ ] 运行 Claude 模型测试，确认 API 调用正常
- [ ] 测试实际推理任务，确认模型工作正常

## 常见问题

### Q1: 如何确认使用的是 Claude 模型？

**A**: 运行配置验证脚本，检查：
- `provider` 应该是 `theturbogateway`
- `model_name` 应该是你配置的 Claude 模型名称

### Q2: 为什么推理任务还是使用 deepseek-reasoner？

**A**: 检查：
1. `.env` 文件中的 `REASONING_MODEL` 是否已更新
2. 是否重启了后端服务（环境变量需要重启才能生效）
3. 运行配置验证脚本确认配置

### Q3: Claude 模型调用失败怎么办？

**A**: 检查：
1. `TURBOGATEWAY_API_KEY` 是否正确
2. API Key 是否有效（访问 TheTurbo.ai 控制台检查）
3. 网络连接是否正常
4. 查看错误日志获取详细信息

### Q4: 可以同时使用多个 Claude 模型吗？

**A**: 可以！你可以为不同用途配置不同的模型：
```bash
# 对话模型使用 Claude
CHAT_MODEL=claude-3-5-sonnet-20241022

# 编码模型使用 DeepSeek
CODE_MODEL=deepseek-coder

# 推理模型使用 Claude Opus
REASONING_MODEL=claude-opus-4-5-20251101
```

### Q5: Claude 模型支持思考过程输出吗？

**A**: 部分 Claude 模型支持 `reasoning_effort` 参数，可以控制推理深度。系统会自动根据任务复杂度调整。

## 性能对比

| 模型 | 推理能力 | 响应速度 | 成本 | 推荐场景 |
|------|---------|---------|------|---------|
| `deepseek-reasoner` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 快速推理、简单任务 |
| `claude-3-5-haiku-20241022` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 一般推理任务 |
| `claude-sonnet-4-5-20250929` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 复杂推理任务 |
| `claude-opus-4-5-20251101` | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | **最复杂推理任务（推荐）** |

## 相关文档

- [多模型支持与模型切换技术实现](./design/multi-model-support-and-switching.md)
- [编排逻辑改进方案](./ORCHESTRATION_IMPROVEMENT_PLAN.md)
- [环境变量配置说明](./design/env-configuration.md)

---

**最后更新**: 2026-01-20  
**维护者**: 项目团队



