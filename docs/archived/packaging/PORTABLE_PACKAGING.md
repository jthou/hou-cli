# 便携式打包方案

## 概述

便携式打包方案将所有运行依赖都打包到 `dist` 目录，创建一个自包含的可移植版本。这个方案介于 PyInstaller 打包和 deb 包之间，提供了更好的灵活性和可移植性。

## 特点

- ✅ **自包含**：所有 Python 依赖都已打包到虚拟环境中
- ✅ **便携**：可以复制到任何位置使用
- ✅ **隔离**：不影响系统 Python 环境
- ✅ **简单**：无需 pip install，解压即用
- ✅ **灵活**：可以修改代码和配置

## 构建方法

### 方法 1: 使用 Shell 脚本（推荐）

```bash
cd /path/to/hou-cli
./build/build-portable.sh
```

### 方法 2: 使用 Python 构建脚本

```bash
cd /path/to/hou-cli
python build/build.py --type portable
```

## 输出结构

构建完成后，会在 `dist/` 目录下创建 `hou-cli-portable/` 目录：

```
dist/hou-cli-portable/
├── venv/              # Python 虚拟环境（包含所有依赖）
│   ├── bin/           # 可执行文件
│   ├── lib/           # Python 库
│   └── ...
├── app/               # 应用代码
│   ├── backend/       # 后端代码
│   ├── frontend/      # 前端代码
│   ├── shared/        # 共享代码
│   ├── cli.py         # 启动脚本
│   └── env.example    # 配置示例
├── hou-cli            # Linux/macOS 启动脚本
├── hou-cli.bat        # Windows 启动脚本
├── README.md          # 使用说明
└── VERSION.txt        # 版本信息
```

## 使用方法

### Linux/macOS

```bash
# 1. 进入便携式目录
cd dist/hou-cli-portable

# 2. 直接运行
./hou-cli start --wait

# 3. 或者添加到 PATH
export PATH="$PATH:$(pwd)"
hou-cli start --wait
```

### Windows

```cmd
REM 1. 进入便携式目录
cd dist\hou-cli-portable

REM 2. 直接运行
hou-cli.bat start --wait

REM 3. 或者添加到 PATH
set PATH=%PATH%;%CD%
hou-cli.bat start --wait
```

## 配置

1. 复制 `app/env.example` 为配置文件：
   - Linux/macOS: `~/.config/hou-cli/.env`
   - Windows: `%APPDATA%\hou-cli\.env`

2. 编辑 `.env` 文件，填入你的 API 密钥：

```env
DEEPSEEK_API_KEY=your_api_key_here
OLLAMA_MODEL=deepseek-r1:14b
LOG_LEVEL=INFO
```

## 系统要求

- **Linux/macOS**: 需要系统已安装 Python 3.10+（仅用于运行虚拟环境）
- **Windows**: 需要系统已安装 Python 3.10+（仅用于运行虚拟环境）

注意：虚拟环境中的 Python 解释器需要与系统 Python 版本兼容。

## 分发

### 创建压缩包

构建脚本会自动询问是否创建压缩包，也可以手动创建：

```bash
cd dist
tar -czf hou-cli-portable-linux-amd64.tar.gz hou-cli-portable
```

### 分发步骤

1. 构建便携式版本
2. 创建压缩包（可选）
3. 将压缩包或目录分发给用户
4. 用户解压后配置 `.env` 文件即可使用

## 优势对比

| 特性 | PyInstaller | 便携式打包 | deb 包 |
|------|------------|-----------|--------|
| 自包含 | ✅ | ✅ | ✅ |
| 可修改代码 | ❌ | ✅ | ❌ |
| 体积 | 大 | 中等 | 中等 |
| 启动速度 | 快 | 中等 | 快 |
| 系统集成 | ❌ | ❌ | ✅ |
| 依赖管理 | ❌ | ✅ | ✅ |

## 适用场景

- ✅ 需要快速分发和测试
- ✅ 需要修改代码或配置
- ✅ 不需要系统级安装
- ✅ 跨平台分发
- ❌ 需要系统级服务（使用 deb 包）
- ❌ 需要单文件可执行（使用 PyInstaller）

## 故障排除

### 问题 1: 虚拟环境无法运行

**原因**: 系统 Python 版本与虚拟环境不兼容

**解决**: 确保系统 Python 版本为 3.10+

```bash
python3 --version  # 检查版本
```

### 问题 2: 启动脚本找不到 Python

**原因**: 虚拟环境路径不正确

**解决**: 检查 `venv/bin/python` 是否存在

```bash
ls -la dist/hou-cli-portable/venv/bin/python
```

### 问题 3: 依赖缺失

**原因**: 构建时依赖安装不完整

**解决**: 重新构建，确保网络连接正常

```bash
rm -rf dist/hou-cli-portable
./build/build-portable.sh
```

## 注意事项

1. **Python 版本兼容性**: 虚拟环境需要与系统 Python 版本兼容
2. **平台特定**: 在不同平台构建的便携式版本不能跨平台使用
3. **文件权限**: 确保启动脚本有执行权限
4. **配置路径**: 配置文件路径是用户目录，不是便携式目录

## 与 deb 包的区别

- **deb 包**: 系统级安装，需要 root 权限，更好的系统集成
- **便携式打包**: 用户级使用，无需 root 权限，更灵活

## 相关文档

- [deb 包打包指南](DEB_PACKAGING.md)
- [PyInstaller 打包指南](PACKAGING.md)
- [项目 README](../README.md)

