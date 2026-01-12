# deb 包安装指南

## 安装方法

### 方法 1: 使用 dpkg（推荐）

```bash
# 安装
sudo dpkg -i dist/hou-cli_0.1.0_amd64.deb

# 如果遇到依赖问题，运行：
sudo apt-get install -f
```

### 方法 2: 使用 apt（如果已配置仓库）

```bash
sudo apt install ./dist/hou-cli_0.1.0_amd64.deb
```

## 验证安装

```bash
# 检查包状态
dpkg -l | grep hou-cli

# 检查可执行文件位置
which hou-cli

# 测试功能
hou-cli --help
```

## 安装后的文件位置

- **可执行文件**: `/usr/local/bin/hou-cli`
- **文档**: `/usr/share/doc/hou-cli/`
- **配置示例**: `/usr/share/hou-cli/env.example`

## 配置

安装后，需要配置 API 密钥：

```bash
# 创建配置目录
mkdir -p ~/.config/hou-cli

# 复制配置示例
cp /usr/share/hou-cli/env.example ~/.config/hou-cli/.env

# 编辑配置
nano ~/.config/hou-cli/.env
```

在 `.env` 文件中填入：
```
DEEPSEEK_API_KEY=your_api_key_here
OLLAMA_MODEL=deepseek-r1:14b
LOG_LEVEL=INFO
```

## 使用

```bash
# 启动聊天
hou-cli chat

# 查看帮助
hou-cli --help
```

## 卸载

```bash
sudo dpkg -r hou-cli
```

## 故障排除

### 问题 1: 依赖错误

如果安装时提示依赖错误：
```bash
sudo apt-get install -f
```

### 问题 2: 权限错误

确保使用 sudo 权限：
```bash
sudo dpkg -i dist/hou-cli_0.1.0_amd64.deb
```

### 问题 3: 找不到命令

安装后如果找不到 `hou-cli` 命令：
```bash
# 检查是否安装
dpkg -l | grep hou-cli

# 检查文件是否存在
ls -lh /usr/local/bin/hou-cli

# 检查 PATH
echo $PATH | grep -q "/usr/local/bin" || export PATH="$PATH:/usr/local/bin"
```

## 测试安装（无需 sudo）

如果无法使用 sudo，可以解压测试：

```bash
# 解压到临时目录
mkdir -p /tmp/test-hou-cli
dpkg-deb -x dist/hou-cli_0.1.0_amd64.deb /tmp/test-hou-cli

# 测试可执行文件
/tmp/test-hou-cli/usr/local/bin/hou-cli --help
```

## 更新

如果有新版本：

```bash
# 直接安装新版本（会自动替换旧版本）
sudo dpkg -i dist/hou-cli_0.2.0_amd64.deb
```

