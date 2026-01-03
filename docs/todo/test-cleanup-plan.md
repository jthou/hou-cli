# 测试程序清理计划

## 当前测试文件分析

### 1. `tests/test_basic.py`
**状态**: ✅ 合理，但可能重复  
**问题**: 
- 测试 Orchestrator 创建 - 已有 `backend/core/agent/tests/test_orchestrator.py`
- 测试 Coordinator 创建 - 可能重复
- 测试平台工具函数 - 合理，但应该移到 `shared/tests/`

**建议**: 
- 保留平台工具函数测试，移到 `shared/tests/`
- 删除 Orchestrator/Coordinator 测试（已有模块测试）

### 2. `tests/test_context_manager_quick.py`
**状态**: ❌ 重复  
**问题**: 
- 已有 `backend/core/agent/tests/test_context_manager.py`
- 独立脚本，不是 pytest

**建议**: 删除

### 3. `tests/test_e2e_chat.py`
**状态**: ⚠️ 需要转换  
**问题**: 
- 独立脚本，使用 Mock
- 应该转成 pytest 单元测试
- 测试内容应该移到 `backend/core/agent/tests/test_orchestrator.py`

**建议**: 
- 将测试逻辑移到 `backend/core/agent/tests/test_orchestrator.py`
- 删除原文件

### 4. `tests/test_multi_turn_chat.py`
**状态**: ⚠️ 需要转换  
**问题**: 
- 独立脚本，使用 Mock
- 应该转成 pytest 单元测试
- 测试内容应该移到 `backend/core/agent/tests/test_orchestrator.py`

**建议**: 
- 将测试逻辑移到 `backend/core/agent/tests/test_orchestrator.py`
- 删除原文件

### 5. `tests/test_integration.py`
**状态**: ✅ 合理  
**问题**: 无

**建议**: 保留，重命名为 `test_backend_integration.py`

### 6. `tests/test_integration_deepseek.py`
**状态**: ❌ 有问题  
**问题**: 
- 有空的测试用例（`pass`）
- 使用 Mock 但叫 "集成测试"
- 测试不完整

**建议**: 
- 删除空的测试用例
- 修正或删除整个文件

---

## 清理步骤

1. 删除重复的测试文件
2. 将独立脚本测试移到 pytest
3. 修正不合理的测试
4. 重新组织测试结构


