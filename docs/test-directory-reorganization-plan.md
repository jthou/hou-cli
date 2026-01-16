# 测试目录重组计划

## 当前问题分析

### 根目录 `tests/` 的问题

**当前结构**：
```
tests/
├── browser/              # ❌ 应该移到 backend/core/agent/tools/tests/
│   ├── test_browser_automation.py
│   └── test_browser_headless.py
├── whisper/              # ❌ 应该移到 backend/core/agent/tools/tests/
│   ├── test_whisper_tool.py
│   ├── test_word_timestamps.py
│   └── test_decoder_manual.py
├── ffmpeg/               # ❌ 应该移到 backend/core/agent/tools/tests/
│   ├── extract_full_audio.py
│   ├── show_transcription_stats.py
│   └── transcribe_full_video.py
├── integration/          # ✅ 可以保留，但需要规范化
│   ├── test_code_execution.py
│   ├── test_e2e_chat.py
│   └── ...
└── 大量独立测试脚本      # ❌ 需要分类和重组
    ├── test_browser_tool_simple.py
    ├── test_browser_qwen_vision.py
    ├── test_whisper_tool.py (重复)
    └── ...
```

### 问题总结

1. **工具测试分散**：
   - BrowserTool 测试在 `tests/browser/` 和 `tests/test_browser_*.py`
   - WhisperTool 测试在 `tests/whisper/` 和 `tests/test_whisper_*.py`
   - 但正确的测试在 `backend/core/agent/tools/tests/test_browser_tool.py`
   - **导致重复和混乱**

2. **不符合架构设计**：
   - 根据架构分析，Tools 测试应该在 `backend/core/agent/tools/tests/`
   - Services 测试应该在各自的 service 目录下
   - 根目录 `tests/` 应该只用于**集成测试**和**端到端测试**

3. **测试类型混乱**：
   - 混合了单元测试、集成测试、手动测试脚本
   - 难以区分测试类型和用途

## 推荐的重组方案

### 目标结构

```
hou-cli/
├── tests/                          # 根目录测试（仅集成/端到端）
│   ├── integration/                # 集成测试（真实后端）
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_code_execution.py
│   │   ├── test_e2e_chat.py
│   │   ├── test_multi_turn_chat.py
│   │   ├── test_api_planning_integration.py
│   │   └── test_orchestrator_planning_task_integration.py
│   │
│   └── scripts/                    # 快速验证脚本（可选保留）
│       ├── test_browser_quick.py
│       └── test_whisper_quick.py
│
└── backend/
    ├── core/
    │   └── agent/
    │       └── tools/
    │           └── tests/          # ✅ Tools 单元测试（集中管理）
    │               ├── test_browser_tool.py
    │               ├── test_whisper_tool.py
    │               ├── test_ffmpeg_tool.py
    │               ├── test_browser_tool_integration.py
    │               ├── test_whisper_tool_integration.py
    │               └── ...
    │
    └── services/
        ├── llm/
        │   └── tests/              # ✅ LLM Service 测试
        │       ├── test_bailian.py
        │       ├── test_deepseek.py
        │       └── ...
        │
        └── file_search_service/
            └── tests/              # ✅ FileSearchService 测试
                └── ...
```

## 重组步骤

### 第一步：移动工具测试到正确位置

#### 1.1 BrowserTool 测试

**当前位置**：
- `tests/browser/test_browser_automation.py`
- `tests/browser/test_browser_headless.py`
- `tests/test_browser_tool_simple.py`
- `tests/test_browser_tool_manual.py`
- `tests/test_browser_tool_headless_modes.py`
- `tests/test_browser_qwen_vision.py`
- `tests/test_browser_vision_simple.py`

**目标位置**：
- `backend/core/agent/tools/tests/test_browser_tool.py`（已有，需要合并）
- `backend/core/agent/tools/tests/test_browser_tool_integration.py`（新建）

**操作**：
1. 检查 `backend/core/agent/tools/tests/test_browser_tool.py` 是否已包含这些测试
2. 如果未包含，合并相关测试到该文件
3. 创建 `test_browser_tool_integration.py` 用于集成测试
4. 删除 `tests/browser/` 目录
5. 删除根目录下的 `test_browser_*.py` 文件

#### 1.2 WhisperTool 测试

**当前位置**：
- `tests/whisper/test_whisper_tool.py`
- `tests/whisper/test_word_timestamps.py`
- `tests/whisper/test_decoder_manual.py`

**目标位置**：
- `backend/core/agent/tools/tests/test_whisper_tool.py`（新建）
- `backend/core/agent/tools/tests/test_whisper_tool_integration.py`（新建）

**操作**：
1. 创建 `backend/core/agent/tools/tests/test_whisper_tool.py`
2. 移动并转换测试到该文件
3. 创建 `test_whisper_tool_integration.py` 用于集成测试
4. 删除 `tests/whisper/` 目录

#### 1.3 FFmpegTool 测试

**当前位置**：
- `tests/ffmpeg/extract_full_audio.py`
- `tests/ffmpeg/show_transcription_stats.py`
- `tests/ffmpeg/transcribe_full_video.py`

**目标位置**：
- `backend/core/agent/tools/tests/test_ffmpeg_tool.py`（新建）
- `backend/core/agent/tools/tests/test_ffmpeg_tool_integration.py`（新建）

**操作**：
1. 检查是否存在 FFmpegTool
2. 如果存在，创建相应的测试文件
3. 如果不存在，这些可能是工具脚本，移到 `tests/scripts/`
4. 删除 `tests/ffmpeg/` 目录

### 第二步：清理根目录测试文件

#### 2.1 移动到集成测试目录

**需要移动的文件**：
- `tests/test_integration.py` → `tests/integration/test_backend_health.py`
- `tests/test_integration_deepseek.py` → `tests/integration/test_deepseek_api.py`
- `tests/test_planning_integration_simple.py` → `tests/integration/test_planning_simple.py`

#### 2.2 移动到脚本目录（可选保留）

**需要移动的文件**：
- `tests/test_context_manager_quick.py` → `tests/scripts/test_context_manager_quick.py`
- `tests/open_browser_baidu.py` → `tests/scripts/open_browser_baidu.py`
- `tests/run_browser_*.py` → `tests/scripts/run_browser_*.py`

#### 2.3 删除或归档

**需要删除的文件**（已移动到正确位置）：
- `tests/test_browser_*.py`（已合并到工具测试）
- `tests/test_whisper_*.py`（已合并到工具测试）
- `tests/test_basic.py`（如果已过时）

### 第三步：规范化集成测试

#### 3.1 集成测试分类

**当前 `tests/integration/` 内容**：
- `test_code_execution.py` - ✅ 保留
- `test_e2e_chat.py` - ✅ 保留
- `test_multi_turn_chat.py` - ✅ 保留
- `test_api_planning_integration.py` - ✅ 保留
- `test_orchestrator_planning_task_integration.py` - ✅ 保留

**需要添加**：
- `test_tool_service_integration.py` - Tools 与 Services 集成测试
- `test_tool_externals_integration.py` - Tools 与 Externals 集成测试
- `test_function_calling_flow.py` - Function Calling 完整流程测试

## 重组后的测试运行

### 运行所有工具测试

```bash
# 运行所有 Tools 单元测试
pytest backend/core/agent/tools/tests/ -v

# 运行特定工具测试
pytest backend/core/agent/tools/tests/test_browser_tool.py -v
pytest backend/core/agent/tools/tests/test_whisper_tool.py -v
```

### 运行所有集成测试

```bash
# 运行所有集成测试
pytest tests/integration/ -v

# 运行特定集成测试
pytest tests/integration/test_code_execution.py -v
```

### 运行所有测试

```bash
# 运行所有测试（单元 + 集成）
pytest backend/ tests/integration/ -v
```

## 需要重写的测试

### 优先级 1：工具测试合并

1. **BrowserTool 测试**
   - 合并 `tests/browser/` 和 `tests/test_browser_*.py` 到 `backend/core/agent/tools/tests/test_browser_tool.py`
   - 创建 `test_browser_tool_integration.py` 用于集成测试

2. **WhisperTool 测试**
   - 创建 `backend/core/agent/tools/tests/test_whisper_tool.py`
   - 移动并转换 `tests/whisper/` 中的测试

3. **FFmpegTool 测试**
   - 检查是否存在 FFmpegTool
   - 如果存在，创建相应的测试文件

### 优先级 2：集成测试规范化

4. **Services 集成测试**
   - 创建 `tests/integration/test_tool_service_integration.py`
   - 测试 Tools 使用 Services 的集成

5. **Externals 集成测试**
   - 创建 `tests/integration/test_tool_externals_integration.py`
   - 测试 Tools 使用 Externals 的集成

6. **Function Calling 流程测试**
   - 创建 `tests/integration/test_function_calling_flow.py`
   - 测试完整的 Function Calling 流程

### 优先级 3：清理和归档

7. **删除重复测试**
   - 删除 `tests/browser/` 目录
   - 删除 `tests/whisper/` 目录
   - 删除 `tests/ffmpeg/` 目录（或移到 scripts）
   - 删除根目录下的重复测试文件

8. **归档旧测试**
   - 将过时的测试移到 `tests/archived/`
   - 更新测试文档

## 实施计划

### 阶段 1：分析和准备（1-2 天）

1. 检查现有测试文件内容
2. 识别重复和过时的测试
3. 确定需要合并的测试
4. 创建重组计划

### 阶段 2：工具测试重组（2-3 天）

1. 合并 BrowserTool 测试
2. 创建 WhisperTool 测试
3. 处理 FFmpegTool 测试
4. 验证测试运行

### 阶段 3：集成测试规范化（1-2 天）

1. 移动集成测试到正确位置
2. 创建新的集成测试
3. 更新测试文档

### 阶段 4：清理和归档（1 天）

1. 删除重复测试
2. 归档过时测试
3. 更新 README 和文档

## 总结

### 当前问题

1. ❌ 工具测试分散在根目录 `tests/` 和工具目录
2. ❌ 不符合架构设计（Tools 测试应该在 `backend/core/agent/tools/tests/`）
3. ❌ 测试类型混乱（单元测试、集成测试、脚本混合）

### 推荐方案

1. ✅ **根目录 `tests/` 只用于集成测试和端到端测试**
2. ✅ **工具测试集中在 `backend/core/agent/tools/tests/`**
3. ✅ **Services 测试在各自的 service 目录下**
4. ✅ **清理重复和过时的测试**

### 关键原则

- **测试应该靠近被测试的代码**
- **根目录 `tests/` 只用于跨模块的集成测试**
- **单元测试应该在各自的模块目录下**
- **避免重复和混乱**

