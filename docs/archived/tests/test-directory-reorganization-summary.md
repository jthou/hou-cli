# 测试目录重构总结

## 重构完成情况

### ✅ 已完成

1. **创建标准测试文件**
   - ✅ `backend/core/agent/tools/tests/test_whisper_tool.py` - WhisperTool 单元测试和集成测试
   - ✅ `backend/core/agent/tools/tests/test_ffmpeg_tool.py` - FFmpegTool 单元测试和集成测试

2. **移动测试脚本到 scripts/**
   - ✅ 所有 Browser 相关测试脚本 → `tests/scripts/`
   - ✅ 所有 Whisper 相关测试脚本 → `tests/scripts/`
   - ✅ 所有 FFmpeg 相关测试脚本 → `tests/scripts/`
   - ✅ `test_context_manager_quick.py` → `tests/scripts/`

3. **清理目录结构**
   - ✅ 删除 `tests/browser/` 目录
   - ✅ 删除 `tests/whisper/` 目录
   - ✅ 删除 `tests/ffmpeg/` 目录

4. **创建文档**
   - ✅ `tests/scripts/README.md` - 说明 scripts 目录的用途

## 当前目录结构

```
tests/
├── integration/              # 集成测试（真实后端）
│   ├── test_code_execution.py
│   ├── test_e2e_chat.py
│   ├── test_multi_turn_chat.py
│   ├── test_api_planning_integration.py
│   └── test_orchestrator_planning_task_integration.py
│
├── scripts/                  # 快速验证脚本（手动测试）
│   ├── README.md
│   ├── test_browser_*.py
│   ├── test_whisper_*.py
│   ├── test_ffmpeg_*.py
│   └── ...
│
└── test_*.py                 # 根目录下的其他测试（待整理）

backend/
└── core/
    └── agent/
        └── tools/
            └── tests/        # Tools 标准测试
                ├── test_browser_tool.py
                ├── test_whisper_tool.py
                ├── test_ffmpeg_tool.py
                └── ...
```

## 待完成工作

### 1. 整理根目录测试文件

根目录下还有以下测试文件需要整理：

- `test_basic.py` - 需要检查内容，决定移到 integration/ 或 scripts/
- `test_integration.py` - 应该移到 `tests/integration/`
- `test_integration_deepseek.py` - 应该移到 `tests/integration/`
- `test_planning_integration_simple.py` - 应该移到 `tests/integration/`
- `test_weather_stream.py` - 需要检查内容，决定移到 integration/ 或删除

### 2. 规范化集成测试

确保 `tests/integration/` 只包含真正的集成测试：
- 验证测试是否使用真实后端
- 验证测试是否使用 pytest
- 移除或转换不符合标准的测试

### 3. 更新测试文档

- 更新 `tests/README.md`（如果存在）
- 更新 `backend/core/agent/tools/tests/README.md`（如果存在）
- 更新项目主 README 中的测试说明

## 重构原则

1. **测试应该靠近被测试的代码**
   - Tools 测试在 `backend/core/agent/tools/tests/`
   - Services 测试在各自的 service 目录下

2. **根目录 `tests/` 只用于跨模块的集成测试**
   - `tests/integration/` - 集成测试
   - `tests/scripts/` - 快速验证脚本

3. **避免重复和混乱**
   - 删除重复的测试文件
   - 统一测试命名规范

## 下一步行动

1. 检查并整理根目录下的剩余测试文件
2. 规范化 `tests/integration/` 目录
3. 更新测试文档
4. 验证所有测试仍然可以正常运行

