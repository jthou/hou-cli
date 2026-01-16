# 使用 LLM 验证工具描述测试指南

## 概述

这个测试框架使用 LLM（大语言模型）来自动验证工具描述的准确性、清晰度和完整性。LLM 会分析每个工具的描述和参数定义，检查是否存在：

1. **错误信息**：描述中提到的功能或参数实际上不存在
2. **歧义**：描述模糊不清，可能产生多种理解
3. **信息不准确**：描述与实际功能不符
4. **信息不足**：缺少关键信息，导致用户无法正确使用工具
5. **参数描述问题**：参数描述与参数定义不一致

## 配置要求

### 1. 环境变量配置

在 `.env` 文件中配置 LLM 服务（参考 `env.example` 文件）：

```bash
# 必需配置：DeepSeek API 密钥（基础 LLM 服务必需）
# 获取方式：访问 https://platform.deepseek.com/ 注册并获取 API Key
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选：LLM 提供商选择（如果不设置，系统会根据模型名称自动检测）
# 可选值：deepseek, bailian, theturbogateway
# 默认值：deepseek
LLM_PROVIDER=deepseek

# 可选：百炼平台配置（如果使用百炼平台模型）
# 获取方式：访问 https://bailian.console.aliyun.com/ 注册并获取 API Key
BAILIAN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选：TheTurbo.ai 网关配置（如果使用 TheTurbo.ai 网关模型）
# 获取方式：访问 TheTurbo.ai 获取 API Key
TURBOGATEWAY_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选：模型配置（如果不设置，使用默认模型）
# 对话模型（用于一般对话任务）
CHAT_MODEL=deepseek-chat
# 编码模型（用于代码相关任务）
CODE_MODEL=deepseek-coder
# 推理模型（用于复杂推理任务）
REASONING_MODEL=deepseek-reasoner
```

**重要说明：**
- `DEEPSEEK_API_KEY` 是**必需配置**，这是基础 LLM 服务的必需配置
- `LLM_PROVIDER` 是**可选配置**，如果不设置，系统会根据模型名称自动检测提供商
- 支持使用 "平台-模型" 格式明确指定平台，例如：
  - `bailian-deepseek-chat`（使用百炼平台的 deepseek-chat）
  - `theturbogateway-gpt-5`（使用 TheTurbo.ai 网关的 GPT-5）
- 详细配置说明请参考项目根目录下的 `env.example` 文件

### 2. 安装依赖

确保已安装所有依赖：

```bash
pip install -r requirements-dev.txt
```

## 运行测试

### 测试所有工具

```bash
# 运行所有工具的验证测试
pytest backend/core/agent/tools/tests/test_tool_descriptions_with_llm.py::test_all_tool_descriptions -v -s

# 或者使用环境变量控制
LLM_PROVIDER=deepseek DEEPSEEK_API_KEY=xxx pytest backend/core/agent/tools/tests/test_tool_descriptions_with_llm.py -v -s
```

### 测试特定工具

```bash
# 测试特定工具（例如 whisper）
pytest backend/core/agent/tools/tests/test_tool_descriptions_with_llm.py::test_specific_tool_description -v -s --tool-name=whisper
```

### 跳过测试（如果未配置 LLM）

如果未配置 LLM API Key，测试会自动跳过：

```bash
pytest backend/core/agent/tools/tests/test_tool_descriptions_with_llm.py -v
# 会显示: SKIPPED [1] 需要配置 LLM API Key 和 Provider
```

## 测试输出

### 控制台输出

测试运行时会实时显示每个工具的验证状态：

```
正在验证工具: whisper...
  ❌ 发现问题: 2 个
正在验证工具: ffmpeg...
  ✅ 通过验证 (评分: 95)
...
```

### 生成的报告

测试完成后会生成详细的验证报告，保存在：

```
docs/tool-description-validation-report.md
```

报告包含：

1. **总体统计**：总工具数、有问题工具数、问题分类
2. **平均质量评分**：所有工具的平均评分
3. **详细问题列表**：按严重程度分类的问题
4. **按工具分组**：每个工具的具体问题和建议

## 报告示例

```markdown
# 工具描述验证报告

## 总体统计

- 总工具数: 15
- 有问题的工具: 3
- 总问题数: 5
  - 严重: 1
  - 中等: 2
  - 轻微: 2

## 平均质量评分

平均分: 87.5/100

## 详细问题列表

### 严重问题

**whisper** - 错误信息
- 位置: 描述中
- 描述: 描述中提到"除非明确指定了时间范围"，但工具没有时间范围参数
- 建议: 移除关于时间范围的描述，或说明当前版本不支持时间范围限制

...
```

## 测试原理

### 1. 工具信息提取

测试框架会：
- 从 `ToolRegistry` 获取所有已注册的工具
- 提取每个工具的名称、描述、参数列表
- 构建完整的工具信息结构

### 2. LLM 分析

对每个工具，构建详细的验证提示，包括：
- 工具描述
- 所有参数的名称、类型、描述、是否必需、默认值、可选值

LLM 会从以下角度分析：
- **准确性**：描述是否准确
- **歧义**：是否存在多种理解
- **完整性**：信息是否充分
- **一致性**：参数描述与定义是否一致

### 3. 结果解析

LLM 返回 JSON 格式的分析结果：
```json
{
    "has_issues": true,
    "issues": [
        {
            "type": "错误信息",
            "severity": "严重",
            "description": "问题描述",
            "location": "具体位置",
            "suggestion": "改进建议"
        }
    ],
    "score": 75,
    "summary": "总体评价"
}
```

### 4. 报告生成

根据所有工具的分析结果：
- 统计总体情况
- 按严重程度分类问题
- 生成详细的改进建议

## 最佳实践

### 1. 定期运行

建议在以下情况运行测试：
- 添加新工具后
- 修改工具描述后
- 发布新版本前
- 定期（如每周）检查

### 2. 修复严重问题

如果发现严重问题（severity: "严重"），测试会失败，需要立即修复。

### 3. 持续改进

根据 LLM 的建议持续改进工具描述：
- 消除歧义
- 补充缺失信息
- 修正错误描述
- 优化参数说明

### 4. 人工审查

虽然 LLM 可以自动发现问题，但建议：
- 人工审查 LLM 的建议
- 结合实际使用场景判断
- 考虑用户的实际需求

## 扩展测试

### 添加自定义检查

可以在 `ToolDescriptionValidator` 中添加自定义检查逻辑：

```python
def custom_check(self, tool_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """自定义检查逻辑"""
    issues = []
    # 添加你的检查逻辑
    return issues
```

### 调整 LLM 提示

可以修改 `_build_validation_prompt` 方法，调整验证的角度和重点。

### 添加更多测试用例

可以添加针对特定场景的测试：
- 测试特定类型的工具
- 测试参数组合
- 测试边界情况

## 注意事项

1. **API 成本**：每次运行会调用 LLM API，注意成本控制
2. **结果一致性**：LLM 的结果可能有一定随机性，建议多次运行对比
3. **误报**：LLM 可能产生误报，需要人工审查
4. **环境依赖**：需要配置正确的 `DEEPSEEK_API_KEY`（必需，参考 `env.example` 文件）

## 故障排除

### 测试被跳过

检查环境变量（在 `.env` 文件中配置）：
```bash
# 检查必需的环境变量
echo $DEEPSEEK_API_KEY  # 必需配置

# 检查可选的环境变量
echo $LLM_PROVIDER  # 可选，系统会自动检测
echo $BAILIAN_API_KEY  # 可选，如果使用百炼平台
echo $TURBOGATEWAY_API_KEY  # 可选，如果使用 TheTurbo.ai 网关
```

**注意：** 配置应该在 `.env` 文件中，不是 shell 环境变量。确保 `.env` 文件存在且包含 `DEEPSEEK_API_KEY`。

### LLM 调用失败

检查：
- API Key 是否正确
- 网络连接是否正常
- API 配额是否充足

### 无法解析响应

LLM 可能返回非 JSON 格式的响应，测试会标记为 `parse_error`，可以查看 `raw_response` 字段。

