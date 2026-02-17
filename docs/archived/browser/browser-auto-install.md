# Browser-use 自动安装功能

## 功能说明

系统已集成自动安装功能，在启动后端时会自动检查并安装 `browser-use` 相关依赖。

## 自动安装触发

以下命令会自动检查并安装依赖：

```bash
# 启动后端（前台）
make run-backend

# 启动后端（后台）
make run-backend-bg

# 一键启动（后端+前端）
make start
# 或
make run

# 使用脚本启动
./scripts/start_backend.sh
```

## 安装逻辑

1. **检查依赖**：自动检查以下依赖是否已安装
   - `browser-use`
   - `playwright`
   - `langchain-openai`

2. **自动安装**：如果依赖未安装，会自动从 `requirements.txt` 安装

3. **检查浏览器**：检查 Playwright 浏览器驱动是否已安装

4. **安装浏览器**：如果浏览器驱动未安装，会自动安装 Chromium

## 手动安装

如果需要手动安装依赖：

```bash
# 使用 Makefile 命令
make install-browser-deps

# 或直接运行脚本
bash scripts/check_browser_deps.sh true
```

## 安装过程

### 正常情况（依赖已安装）

```
✅ browser-use 相关依赖已安装
✅ Playwright 浏览器已安装
```

### 需要安装时

```
📦 检测到 browser-use 相关依赖未安装，正在自动安装...

📥 从 requirements.txt 安装依赖...
✅ 依赖安装完成

🌐 检测到 playwright 浏览器未安装，正在安装...
✅ Playwright 浏览器安装完成
```

## 注意事项

1. **首次安装**：首次安装可能需要几分钟时间，特别是安装 Playwright 浏览器驱动

2. **依赖冲突**：安装过程中可能会看到依赖冲突警告，这些通常不会影响功能

3. **网络要求**：需要网络连接来下载依赖和浏览器驱动

4. **权限要求**：安装 Playwright 浏览器可能需要系统权限

## 故障排查

### 问题：自动安装失败

**解决方案：**
```bash
# 手动安装
make install-browser-deps

# 或强制重新安装
pip install -r requirements.txt --force-reinstall
playwright install --force chromium
```

### 问题：浏览器驱动安装失败

**解决方案：**
```bash
# 手动安装浏览器驱动
playwright install chromium

# 如果失败，尝试强制安装
playwright install --force chromium
```

### 问题：依赖冲突

**解决方案：**
依赖冲突警告通常不会影响功能。如果确实有问题：
```bash
# 查看具体冲突
pip check

# 根据提示解决冲突
```

## 禁用自动安装

如果不想自动安装，可以：

1. **修改脚本**：编辑 `scripts/check_browser_deps.sh`，在开头添加 `exit 0`

2. **修改 Makefile**：移除 `run-backend` 等目标中的 `bash scripts/check_browser_deps.sh &&` 部分

## 验证安装

安装完成后，可以验证：

```bash
# 检查 Python 包
python3 -c "import browser_use; import playwright; import langchain_openai; print('✅ 所有依赖已安装')"

# 检查浏览器驱动
python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch(headless=True).close(); p.stop(); print('✅ 浏览器驱动已安装')"
```

## 相关文件

- `scripts/check_browser_deps.sh` - 自动安装脚本
- `Makefile` - Makefile 配置
- `requirements.txt` - 开发依赖配置
- `docs/browser-tool-setup.md` - 详细设置指南






