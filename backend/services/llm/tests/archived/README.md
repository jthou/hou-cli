# 归档的测试文件

本目录包含已归档的测试相关文件，这些文件功能已被其他文件替代或不再需要。

## 归档的文件

### 1. pytest 相关文件（功能重复）

- `pytest_plugin_filter.py` - pytest 插件过滤器（用于过滤 ROS 插件）
- `pytest_wrapper.py` - pytest 包装器（用于避免 ROS 插件冲突）
- `run_pytest.sh` - bash 脚本运行 pytest
- `run_tests.sh` - bash 脚本运行 pytest（功能与 run_pytest.sh 重复）
- `run_tests_simple.py` - 简单的 pytest 运行器（功能与 pytest_wrapper.py 重复）

**替代方案**：推荐使用 `run_tests_direct.py`，它不依赖 pytest，避免了所有插件冲突问题。

### 2. 测试脚本（功能重复）

- `test_manual.py` - 手动测试脚本（功能与 `run_tests_direct.py` 重复）
- `test_runner.py` - 测试文件验证器（用于验证测试文件语法和结构）

**替代方案**：
- 使用 `run_tests_direct.py` 运行测试
- 使用 `pytest` 直接运行测试文件（如果环境支持）

## 当前推荐的文件

### 必要的文件

1. **`conftest.py`** - pytest 配置文件，自动加载 .env 文件
2. **`run_tests_direct.py`** - 推荐使用的测试运行器（不依赖 pytest）
3. **`test_*.py`** - 实际的测试文件：
   - `test_deepseek.py` - DeepSeek 平台测试
   - `test_bailian.py` - 百炼平台文本模型测试
   - `test_bailian_vision.py` - 百炼平台视觉模型测试
   - `test_turbogateway_*.py` - TheTurbo.ai 网关各服务测试
4. **`README.md`** - 测试说明文档

### 运行测试

```bash
# 推荐方式（不依赖 pytest）
python3 backend/services/llm/tests/run_tests_direct.py

# 或使用 pytest（如果环境支持）
pytest backend/services/llm/tests/ -v
```

## 为什么归档这些文件？

1. **功能重复**：多个文件实现相同的功能（运行 pytest 测试）
2. **维护成本**：维护多个功能重复的文件增加了维护成本
3. **用户困惑**：多个选择会让用户困惑，不知道应该使用哪个
4. **推荐方案**：`run_tests_direct.py` 是最简单、最可靠的方案，不依赖 pytest，避免了所有插件冲突问题

## 如果需要恢复

如果将来需要这些文件的功能，可以从归档目录中恢复。但建议优先使用 `run_tests_direct.py`。

