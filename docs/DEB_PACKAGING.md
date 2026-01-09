# Debian/Ubuntu deb 包打包指南

## 概述

deb 包是 Debian/Ubuntu 系统的标准软件包格式，提供更好的系统集成和依赖管理。

## 优势

相比 tar.gz 压缩包，deb 包具有以下优势：

1. **系统集成**: 自动安装到系统路径 (`/usr/local/bin`)
2. **依赖管理**: 自动检查和安装系统依赖
3. **版本管理**: 系统包管理器可以跟踪版本
4. **卸载清理**: 标准的卸载流程
5. **更新管理**: 支持通过包管理器更新

## 快速开始

### 构建 deb 包

```bash
# 使用构建脚本（推荐）
./build/build-deb.sh

# 输出: dist/hou-cli_0.1.0_amd64.deb
```

### 安装 deb 包

```bash
# 安装
sudo dpkg -i dist/hou-cli_0.1.0_amd64.deb

# 如果遇到依赖问题
sudo apt-get install -f

# 验证安装
hou-cli --help
```

### 卸载

```bash
sudo dpkg -r hou-cli
```

## 包结构

```
hou-cli_0.1.0_amd64.deb
├── DEBIAN/
│   ├── control      # 包元数据
│   ├── postinst     # 安装后脚本
│   ├── postrm       # 卸载后脚本
│   └── prerm        # 卸载前脚本
├── usr/
│   ├── local/
│   │   └── bin/
│   │       └── hou-cli  # 可执行文件
│   └── share/
│       ├── doc/
│       │   └── hou-cli/
│       │       └── README.md
│       └── hou-cli/
│           └── env.example
```

## 配置文件说明

### control 文件

定义包的基本信息：

```control
Package: hou-cli
Version: 0.1.0
Section: utils
Priority: optional
Architecture: amd64
Depends: libc6 (>= 2.31)
Maintainer: Your Name <your.email@example.com>
Description: LLM Agent CLI Tool
```

### postinst 脚本

安装后执行的脚本，用于：
- 创建必要的目录
- 设置权限
- 显示安装完成信息

### postrm 脚本

卸载后执行的脚本，用于：
- 清理临时文件
- （可选）保留用户数据

### prerm 脚本

卸载前执行的脚本，用于：
- 停止运行中的服务
- 清理进程

## 构建流程

1. **构建可执行文件**: 使用 PyInstaller 打包
2. **准备 deb 目录结构**: 创建标准的 deb 包目录
3. **复制文件**: 将可执行文件和文档复制到对应位置
4. **构建 deb 包**: 使用 `dpkg-deb` 构建

## 版本管理

更新版本号：

1. 编辑 `pyproject.toml`:
```toml
[project]
version = "0.1.1"
```

2. 重新构建:
```bash
./build/build-deb.sh
```

## 测试

### 检查包内容

```bash
# 查看包信息
dpkg-deb --info dist/hou-cli_0.1.0_amd64.deb

# 查看包文件列表
dpkg-deb --contents dist/hou-cli_0.1.0_amd64.deb

# 解压测试
dpkg-deb -x dist/hou-cli_0.1.0_amd64.deb /tmp/test-deb
```

### 安装测试

```bash
# 安装
sudo dpkg -i dist/hou-cli_0.1.0_amd64.deb

# 验证
which hou-cli
hou-cli --help

# 卸载
sudo dpkg -r hou-cli
```

## 发布到 PPA（可选）

如果需要发布到 Ubuntu PPA：

1. 创建 Launchpad 账户
2. 设置 GPG 密钥
3. 使用 `dput` 上传包

详细步骤请参考 [Ubuntu PPA 文档](https://help.launchpad.net/Packaging/PPA)

## 常见问题

### Q: 包太大怎么办？

A: 
- 使用 UPX 压缩可执行文件
- 排除不必要的依赖
- 考虑分拆为多个包

### Q: 如何添加更多依赖？

A: 在 `control` 文件的 `Depends` 字段中添加：
```
Depends: libc6 (>= 2.31), libssl3 (>= 3.0)
```

### Q: 如何支持多个架构？

A: 修改 `Architecture` 字段：
```
Architecture: amd64 arm64
```

然后为每个架构分别构建。

## 参考资源

- [Debian 打包指南](https://www.debian.org/doc/manuals/packaging-tutorial/packaging-tutorial.en.pdf)
- [Ubuntu 打包指南](https://packaging.ubuntu.com/html/)
- [dpkg-deb 手册](https://manpages.debian.org/dpkg-deb)

