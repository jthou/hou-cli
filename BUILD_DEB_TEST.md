# deb 包构建和安装测试报告

## 测试时间
2025-01-09

## 测试环境
- **操作系统**: Ubuntu (Linux 6.8.0-85-generic)
- **Python 版本**: 3.13.5
- **架构**: x86_64

## 构建步骤

### 1. 构建可执行文件
```bash
python -m PyInstaller --clean --noconfirm \
    --name hou-cli \
    --add-data "env.example:." \
    --onefile cli.py
```
✅ 成功 - 生成 `dist/hou-cli` (76MB)

### 2. 准备 deb 包结构
```bash
mkdir -p build/deb/usr/local/bin
mkdir -p build/deb/usr/share/doc/hou-cli
mkdir -p build/deb/usr/share/hou-cli
```

### 3. 复制文件
- 可执行文件: `build/deb/usr/local/bin/hou-cli`
- 文档: `build/deb/usr/share/doc/hou-cli/README.md`
- 配置示例: `build/deb/usr/share/hou-cli/env.example`

### 4. 构建 deb 包
```bash
dpkg-deb --build build/deb dist/hou-cli_0.1.0_amd64.deb
```
✅ 成功 - 生成 `dist/hou-cli_0.1.0_amd64.deb` (75MB)

## 包信息

**包名**: hou-cli  
**版本**: 0.1.0  
**架构**: amd64  
**大小**: 75MB  
**依赖**: libc6 (>= 2.31)

## 包内容

```
usr/local/bin/hou-cli                    # 可执行文件 (76MB)
usr/share/doc/hou-cli/README.md         # 文档
usr/share/doc/hou-cli/INSTALL.md        # 安装说明
usr/share/hou-cli/env.example           # 配置示例
```

## 安装测试

### 安装命令
```bash
sudo dpkg -i dist/hou-cli_0.1.0_amd64.deb
```

### 如果遇到依赖问题
```bash
sudo apt-get install -f
```

### 验证安装
```bash
# 检查包状态
dpkg -l | grep hou-cli

# 检查可执行文件位置
which hou-cli

# 测试功能
hou-cli --help
```

### 卸载
```bash
sudo dpkg -r hou-cli
```

## 测试结果

### ✅ 构建测试
- [x] 可执行文件构建成功
- [x] deb 包结构正确
- [x] 文件权限设置正确
- [x] deb 包构建成功

### ✅ 功能测试（解压测试）
- [x] 可执行文件可正常运行
- [x] `--help` 命令正常工作
- [x] 文件结构完整

### ⚠️ 安装测试
- [ ] 需要 sudo 权限进行实际安装测试
- [ ] 安装后脚本 (postinst) 需要测试
- [ ] 卸载脚本 (postrm) 需要测试

## 已知问题

1. **权限问题**: 已修复 - DEBIAN 目录下的脚本文件需要 755 权限
2. **包大小**: 75MB 较大，但包含所有依赖，属于正常范围

## 下一步

1. ✅ 修复构建脚本权限问题
2. ⏳ 实际安装测试（需要 sudo）
3. ⏳ 测试安装后脚本
4. ⏳ 测试卸载流程
5. ⏳ 添加到 CI/CD 流程

## 使用说明

### 快速安装
```bash
# 下载 deb 包后
sudo dpkg -i hou-cli_0.1.0_amd64.deb
sudo apt-get install -f  # 如果需要
hou-cli --help
```

### 配置
```bash
# 复制配置示例
cp /usr/share/hou-cli/env.example ~/.config/hou-cli/.env

# 编辑配置
nano ~/.config/hou-cli/.env
```

### 使用
```bash
hou-cli chat
```

## 参考

- [DEB_PACKAGING.md](docs/DEB_PACKAGING.md) - deb 包打包详细文档
- [PACKAGING.md](docs/PACKAGING.md) - 通用打包文档

