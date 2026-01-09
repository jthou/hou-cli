# Debian/Ubuntu deb 包打包指南（独立虚拟环境版本）

## 概述

此版本将整个虚拟环境打包到 deb 包中，实现完全的环境隔离。

## 优势

1. **完全隔离**: 不依赖系统 Python 环境
2. **不影响主机**: 不会修改系统 Python 包
3. **版本固定**: 所有依赖版本固定，避免冲突
4. **易于卸载**: 卸载时完全清理，不留痕迹

## 打包结构

```
hou-cli_0.1.0_amd64.deb
├── DEBIAN/
│   ├── control      # 包元数据
│   ├── postinst     # 安装后脚本
│   ├── postrm       # 卸载后脚本
│   └── prerm        # 卸载前脚本
├── opt/
│   └── hou-cli/
│       └── venv/     # 完整的虚拟环境
│           ├── bin/
│           ├── lib/
│           └── ...
├── usr/
│   ├── local/
│   │   └── bin/
│   │       ├── hou-cli          # 启动脚本（使用 venv）
│   │       └── hou-cli-backend  # 后端启动脚本
│   └── share/
│       ├── doc/
│       │   └── hou-cli/
│       │       ├── README.md
│       │       └── INSTALL.md
│       └── hou-cli/
│           └── env.example
```

## 构建方法

### 使用构建脚本（推荐）

```bash
./build/build-deb-with-venv.sh
```

### 手动构建

```bash
# 1. 创建 deb 目录结构
mkdir -p build/deb/opt/hou-cli
mkdir -p build/deb/usr/local/bin
mkdir -p build/deb/usr/share/doc/hou-cli
mkdir -p build/deb/usr/share/hou-cli

# 2. 创建虚拟环境
python3 -m venv build/deb/opt/hou-cli/venv

# 3. 安装依赖
source build/deb/opt/hou-cli/venv/bin/activate
pip install -r requirements.txt
pip install -e .

# 4. 创建启动脚本
cat > build/deb/usr/local/bin/hou-cli << 'EOF'
#!/bin/bash
exec /opt/hou-cli/venv/bin/python -m frontend.main "$@"
EOF
chmod 755 build/deb/usr/local/bin/hou-cli

# 5. 构建 deb 包
dpkg-deb --build build/deb dist/hou-cli_0.1.0_amd64.deb
```

## 安装

```bash
sudo dpkg -i dist/hou-cli_0.1.0_amd64.deb
sudo apt-get install -f  # 如果需要
```

## 工作原理

### 启动脚本

`/usr/local/bin/hou-cli` 是一个包装脚本，它：
1. 检查虚拟环境是否存在
2. 使用虚拟环境中的 Python 运行应用
3. 传递所有参数给应用

### 虚拟环境

- **位置**: `/opt/hou-cli/venv`
- **Python 版本**: 与构建时相同
- **依赖**: 所有依赖都安装在虚拟环境中
- **隔离**: 完全独立于系统 Python

## 依赖要求

### 系统依赖

- `python3` (>= 3.10)
- `python3-venv`

### 应用依赖

所有应用依赖都打包在虚拟环境中，不需要系统安装。

## 配置

```bash
# 复制配置示例
cp /usr/share/hou-cli/env.example ~/.config/hou-cli/.env

# 编辑配置
nano ~/.config/hou-cli/.env
```

## 使用

```bash
# 启动聊天
hou-cli chat

# 查看帮助
hou-cli --help
```

## 验证虚拟环境

```bash
# 检查虚拟环境
ls -la /opt/hou-cli/venv/

# 检查 Python 版本
/opt/hou-cli/venv/bin/python --version

# 检查已安装的包
/opt/hou-cli/venv/bin/pip list
```

## 卸载

```bash
sudo dpkg -r hou-cli
```

卸载会完全删除：
- `/opt/hou-cli/venv` - 虚拟环境
- `/usr/local/bin/hou-cli` - 启动脚本
- `/usr/share/doc/hou-cli` - 文档
- `/usr/share/hou-cli` - 配置示例

**注意**: 用户数据目录 `~/.local/share/hou-cli` 不会被删除。

## 更新

```bash
# 卸载旧版本
sudo dpkg -r hou-cli

# 安装新版本
sudo dpkg -i dist/hou-cli_0.2.0_amd64.deb
```

## 包大小

由于包含完整的虚拟环境，包大小会比较大（通常 200-500MB），但提供了完全的隔离性。

## 与 PyInstaller 版本对比

| 特性 | 虚拟环境版本 | PyInstaller 版本 |
|------|------------|-----------------|
| 包大小 | 较大 (200-500MB) | 较小 (75MB) |
| 启动速度 | 较快 | 较慢（需要解压） |
| 隔离性 | 完全隔离 | 完全隔离 |
| 依赖管理 | 标准 pip | 打包所有依赖 |
| 调试 | 容易（标准 Python） | 困难 |
| 更新 | 需要重新打包 | 需要重新打包 |

## 故障排除

### 问题 1: 虚拟环境权限错误

```bash
sudo chmod -R 755 /opt/hou-cli/venv
```

### 问题 2: Python 版本不匹配

确保构建时使用的 Python 版本与目标系统兼容。

### 问题 3: 依赖缺失

检查虚拟环境中的依赖：
```bash
/opt/hou-cli/venv/bin/pip list
```

## 参考

- [DEB_PACKAGING.md](DEB_PACKAGING.md) - PyInstaller 版本打包指南
- [Python venv 文档](https://docs.python.org/3/library/venv.html)

