# Local-File-Organizer 工具安装指南

## 概述

Local-File-Organizer 是一个 AI 驱动的本地文件整理工具，可以自动扫描、分类和重命名文件。本工具已集成到项目中，支持多种安装方式。

## 安装方式

### 方式 1：从 GitHub 安装（推荐，如果网络可用）

如果 Local-File-Organizer 的 GitHub 仓库包含 `setup.py` 或 `pyproject.toml`，可以直接从 GitHub 安装：

```bash
# 激活虚拟环境
source venv/bin/activate

# 从 GitHub 安装
pip install git+https://github.com/QiuYannnn/Local-File-Organizer.git
```

### 方式 2：作为 Git 子模块添加

```bash
# 在项目根目录执行
git submodule add https://github.com/QiuYannnn/Local-File-Organizer.git backend/externals/local-file-organizer

# 初始化子模块
git submodule update --init --recursive backend/externals/local-file-organizer
```

### 方式 3：直接克隆到本地

```bash
# 克隆到 externals 目录
git clone https://github.com/QiuYannnn/Local-File-Organizer.git backend/externals/local-file-organizer
```

## 依赖要求

Local-File-Organizer 需要 Nexa SDK，根据您的硬件选择：

### CPU 版本
```bash
pip install nexaai --prefer-binary --index-url https://nexaai.github.io/nexa-sdk/whl/cpu --extra-index-url https://pypi.org/simple --no-cache-dir
```

### GPU 版本（macOS Metal）
```bash
CMAKE_ARGS="-DGGML_METAL=ON -DSD_METAL=ON" pip install nexaai --prefer-binary --index-url https://nexaai.github.io/nexa-sdk/whl/metal --extra-index-url https://pypi.org/simple --no-cache-dir
```

### 其他依赖

安装 Local-File-Organizer 后，还需要安装其 `requirements.txt` 中的依赖：

```bash
cd backend/externals/local-file-organizer
pip install -r requirements.txt
```

## 验证安装

安装完成后，工具会自动检测 Local-File-Organizer 的可用性。您可以通过以下方式验证：

### 1. 检查工具注册

启动应用后，查看日志中是否有：
```
File organizer tool registered successfully
```

如果看到：
```
Local-File-Organizer not installed: ...
File organizer tool will not be available.
```

说明安装未成功，请检查上述安装步骤。

### 2. 运行测试

```bash
pytest backend/core/agent/tools/tests/test_file_organizer_tool.py -v
```

### 3. 测试工具功能

在应用中尝试使用文件整理功能：

```
用户：整理我的 Downloads 文件夹
```

## 使用说明

### 工具参数

- `source_path`（必需）：需要整理的源文件夹路径
- `target_path`（可选）：整理后文件的存放路径，默认在源路径下创建 `organized` 文件夹
- `organize_mode`（可选）：整理模式，`move`（移动）或 `copy`（复制），默认 `move`
- `dry_run`（可选）：是否仅预览整理结果而不实际执行，默认 `false`

### 使用示例

1. **基本整理**：
   ```
   整理 Downloads 文件夹
   ```
   工具会自动调用：`source_path='/Users/username/Downloads'`

2. **整理到指定位置**：
   ```
   整理 Downloads 文件夹到 /Users/username/Organized
   ```
   工具会自动调用：`source_path='/Users/username/Downloads', target_path='/Users/username/Organized'`

3. **预览整理计划**：
   ```
   预览整理 Downloads 文件夹的计划
   ```
   工具会自动调用：`source_path='/Users/username/Downloads', dry_run=true`

4. **复制模式整理**：
   ```
   复制整理 Downloads 文件夹
   ```
   工具会自动调用：`source_path='/Users/username/Downloads', organize_mode='copy'`

## 故障排查

### 问题 1：工具未注册

**症状**：日志显示 "Local-File-Organizer not installed"

**解决方案**：
1. 检查是否已安装 Local-File-Organizer
2. 检查 Python 路径中是否包含 Local-File-Organizer
3. 如果使用子模块方式，检查 `backend/externals/local-file-organizer` 是否存在

### 问题 2：导入错误

**症状**：运行时出现 `ImportError` 或 `ModuleNotFoundError`

**解决方案**：
1. 确认已安装所有依赖（包括 Nexa SDK）
2. 检查 Python 版本（需要 Python 3.10+）
3. 尝试重新安装依赖

### 问题 3：执行失败

**症状**：工具执行时返回错误

**解决方案**：
1. 检查源路径是否存在且可读
2. 检查目标路径是否有写入权限
3. 查看详细错误日志
4. 尝试使用 `dry_run=true` 预览模式

## 参考链接

- Local-File-Organizer GitHub: https://github.com/QiuYannnn/Local-File-Organizer
- Nexa SDK 文档: https://nexaai.github.io/nexa-sdk/

