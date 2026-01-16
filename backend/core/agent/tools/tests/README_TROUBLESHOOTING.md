# Tools 测试故障排除

## ROS 插件冲突问题

### 问题描述

如果运行 `pytest backend/core/agent/tools/tests/ -v` 时遇到以下错误：

```
pluggy._manager.PluginValidationError: unknown hook 'pytest_launch_collect_makemodule' in plugin <module 'launch_testing_ros_pytest_entrypoint' from '/opt/ros/jazzy/lib/python3.12/site-packages/launch_testing_ros_pytest_entrypoint.py'>
```

这是因为 ROS (Robot Operating System) 的 pytest 插件与当前 pytest 版本不兼容。

### 解决方案

#### 方法 1：使用测试脚本（推荐）

```bash
# 使用专门的测试脚本，自动处理 ROS 插件冲突
bash backend/core/agent/tools/tests/run_tests.sh

# 或运行特定测试
bash backend/core/agent/tools/tests/run_tests.sh -k "test_tool_initialization"
```

#### 方法 2：手动禁用插件

```bash
# 在命令行中明确禁用 ROS 插件
pytest backend/core/agent/tools/tests/ -v \
    -p no:launch_testing \
    -p no:launch_testing_ros_pytest_entrypoint \
    -p no:colcon_core \
    -p no:ament_lint \
    -p no:ament_xmllint \
    -p no:ament_pep257 \
    -p no:ament_copyright \
    -p no:ament_flake8 \
    --ignore-glob="**/launch_testing_ros_pytest_entrypoint.py"
```

#### 方法 3：修改 PYTHONPATH

```bash
# 从 PYTHONPATH 中移除 ROS 路径
export PYTHONPATH=$(echo "$PYTHONPATH" | tr ':' '\n' | grep -v ros | tr '\n' ':' | sed 's/:$//')

# 然后运行 pytest
pytest backend/core/agent/tools/tests/ -v
```

#### 方法 4：使用虚拟环境（最彻底）

```bash
# 创建新的虚拟环境（不包含 ROS）
python3 -m venv venv_clean
source venv_clean/bin/activate

# 安装项目依赖
pip install -r requirements.txt
pip install pytest pytest-asyncio

# 运行测试
pytest backend/core/agent/tools/tests/ -v
```

## 其他常见问题

### 问题 1: ModuleNotFoundError: No module named 'httpx'

**解决方法**：
```bash
pip install httpx
```

### 问题 2: ModuleNotFoundError: No module named 'dotenv'

**解决方法**：
```bash
pip install python-dotenv
```

### 问题 3: 测试被跳过

这是**正常的**！测试会根据环境自动跳过：
- 缺少 API Key → 跳过需要 API Key 的测试
- 依赖未安装 → 跳过需要依赖的测试

**解决方法**：配置相应的环境变量或安装依赖

### 问题 4: pytest 版本冲突

如果遇到 pytest 版本问题：

```bash
# 检查 pytest 版本
pytest --version

# 升级到最新版本
pip install --upgrade pytest

# 或安装特定版本
pip install pytest==7.4.4
```

## 推荐工作流程

1. **首先尝试使用测试脚本**：
   ```bash
   bash backend/core/agent/tools/tests/run_tests.sh
   ```

2. **如果脚本不工作，手动禁用插件**：
   ```bash
   pytest backend/core/agent/tools/tests/ -v -p no:launch_testing_ros_pytest_entrypoint
   ```

3. **如果仍然有问题，使用干净的虚拟环境**：
   ```bash
   python3 -m venv venv_clean
   source venv_clean/bin/activate
   pip install -r requirements.txt
   pytest backend/core/agent/tools/tests/ -v
   ```

## 更多帮助

- 详细测试指南：`docs/testing-guide.md`
- 快速开始：`docs/TESTING_QUICK_START.md`
- 如何测试：`docs/how-to-test-tools.md`

