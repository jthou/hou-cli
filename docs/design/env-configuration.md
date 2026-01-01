# 环境变量配置指南

## 概述

本项目使用环境变量来管理敏感配置信息（如 API Key）和可选配置参数。支持通过 `.env` 文件或系统环境变量进行配置。

---

## 配置文件

### `.env` 文件

在项目根目录创建 `.env` 文件来存储配置：

```bash
# 复制示例文件
cp env.example .env

# 编辑配置文件
vim .env  # 或使用你喜欢的编辑器
```

**注意**: `.env` 文件已添加到 `.gitignore`，不会被提交到代码仓库。

### `env.example` 文件

`env.example` 是配置模板文件，包含所有可用的配置项和说明，但不包含敏感信息。新成员可以参考此文件创建自己的 `.env` 文件。

---

## 配置项说明

### 必需配置

#### `DEEPSEEK_API_KEY`

DeepSeek API 密钥，用于调用 DeepSeek LLM 服务。

- **获取方式**: 访问 https://platform.deepseek.com/ 注册并获取 API Key
- **格式**: 字符串，长度至少 10 个字符
- **示例**: `DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**如果未设置此配置，服务将无法启动。**

---

### 可选配置

#### `LLM_TEMPERATURE`

控制 LLM 输出的随机性。

- **类型**: 浮点数
- **范围**: 0.0 - 2.0
- **默认值**: 0.7
- **说明**: 
  - 较低值（如 0.2）：输出更保守、确定性更强
  - 较高值（如 0.9）：输出更具创造性、随机性更强
- **示例**: `LLM_TEMPERATURE=0.8`

#### `LLM_MAX_TOKENS`

LLM 响应的最大 token 数。

- **类型**: 整数
- **范围**: > 0
- **默认值**: 2000
- **说明**: 限制响应长度，防止生成过长的回复
- **示例**: `LLM_MAX_TOKENS=1000`

#### `BACKEND_HOST`

后端服务绑定的主机地址。

- **类型**: 字符串
- **默认值**: `127.0.0.1`
- **说明**: 通常使用 `127.0.0.1`（本地）或 `0.0.0.0`（所有接口）
- **示例**: `BACKEND_HOST=127.0.0.1`

#### `BACKEND_PORT`

后端服务绑定的端口号。

- **类型**: 整数
- **默认值**: 自动查找可用端口
- **说明**: 如果未设置，系统会自动查找可用端口
- **示例**: `BACKEND_PORT=8000`

---

## 配置加载顺序

配置按以下顺序加载，后加载的会覆盖先加载的：

1. **系统环境变量** - 优先级最高
2. **`.env` 文件** - 项目根目录的 `.env` 文件
3. **代码默认值** - 如果以上都未设置，使用代码中的默认值

---

## 使用方法

### 方法 1: 使用 `.env` 文件（推荐）

1. 复制示例文件：
   ```bash
   cp env.example .env
   ```

2. 编辑 `.env` 文件，填入你的配置：
   ```bash
   DEEPSEEK_API_KEY=your_actual_api_key_here
   ```

3. 启动服务（`.env` 文件会自动加载）：
   ```bash
   python -m backend.main
   # 或
   python -m frontend.main chat
   ```

### 方法 2: 使用系统环境变量

#### Linux / macOS

```bash
# 临时设置（当前终端会话）
export DEEPSEEK_API_KEY=your_api_key_here

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export DEEPSEEK_API_KEY=your_api_key_here' >> ~/.zshrc
source ~/.zshrc
```

#### Windows

```cmd
# 临时设置（当前命令提示符会话）
set DEEPSEEK_API_KEY=your_api_key_here

# 永久设置（通过系统设置）
# 控制面板 > 系统 > 高级系统设置 > 环境变量
```

---

## 配置验证

服务启动时会自动验证配置：

- ✅ **API Key 存在**: 检查 `DEEPSEEK_API_KEY` 是否设置
- ✅ **API Key 格式**: 检查 API Key 长度是否足够（至少 10 个字符）
- ✅ **参数范围**: 检查 `temperature` 和 `max_tokens` 是否在有效范围内

如果配置无效，服务将无法启动并显示明确的错误信息。

---

## 安全注意事项

⚠️ **重要安全提示**:

1. **不要提交 `.env` 文件到代码仓库**
   - `.env` 文件已添加到 `.gitignore`
   - 如果意外提交，应立即撤销并更换 API Key

2. **不要分享你的 API Key**
   - API Key 是敏感信息，类似于密码
   - 如果泄露，应立即在 DeepSeek 平台撤销并重新生成

3. **使用 `.env.example` 作为模板**
   - 只提交 `.env.example`，不包含真实配置
   - 团队成员可以参考 `.env.example` 创建自己的 `.env` 文件

4. **生产环境配置**
   - 生产环境建议使用系统环境变量或密钥管理服务
   - 不要将 `.env` 文件部署到生产服务器

---

## 故障排查

### 问题 1: "DEEPSEEK_API_KEY 环境变量未设置"

**原因**: API Key 未配置或 `.env` 文件未正确加载。

**解决方案**:
1. 检查 `.env` 文件是否存在
2. 检查 `.env` 文件中是否有 `DEEPSEEK_API_KEY=...`
3. 检查 `.env` 文件是否在项目根目录
4. 尝试使用系统环境变量设置

### 问题 2: "API Key 格式无效"

**原因**: API Key 为空或长度不足。

**解决方案**:
1. 检查 API Key 是否正确复制（没有多余空格）
2. 检查 API Key 长度是否足够（至少 10 个字符）
3. 重新从 DeepSeek 平台获取 API Key

### 问题 3: 配置不生效

**原因**: 配置加载顺序问题或 `.env` 文件格式错误。

**解决方案**:
1. 检查 `.env` 文件格式（每行一个配置，格式：`KEY=VALUE`）
2. 检查是否有语法错误（如引号、空格等）
3. 重启服务（配置在启动时加载）
4. 使用系统环境变量验证配置是否生效

---

## 相关文件

- `.env.example` - 配置模板文件
- `.gitignore` - 忽略 `.env` 文件
- `backend/main.py` - 后端启动时加载 `.env`
- `frontend/main.py` - 前端启动时加载 `.env`
- `backend/services/llm/llm_service.py` - LLM 服务配置读取

---

**最后更新**: 2025-12-31

