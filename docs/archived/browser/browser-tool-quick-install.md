# 浏览器工具快速安装指南

## 当前状态

✅ **工具已注册**：`browser` 工具已成功注册到系统中，会出现在工具列表中（共 8 个工具）

❌ **依赖未安装**：需要安装 `browser-use` 和相关依赖才能使用

## 快速安装

### 方法 1: 使用开发依赖（推荐）

```bash
# 安装所有开发依赖（包含 browser-use 和所需的新版本 LangChain）
pip install -r requirements.txt

# 安装浏览器驱动
playwright install chromium
```

### 方法 2: 单独安装

```bash
# 安装 browser-use 和相关依赖
pip install browser-use>=0.2.7 langchain-openai>=0.3.21 playwright>=1.40.0

# 升级 LangChain 到兼容版本
pip install langchain>=0.3.25 langchain-core>=0.3.64 langchain-ollama>=0.3.3

# 安装其他依赖
pip install anyio>=4.9.0 python-dotenv>=1.0.1

# 安装浏览器驱动
playwright install chromium
```

## 验证安装

安装完成后，重启系统，然后尝试执行浏览器任务：

```
打开网页 www.baidu.com
```

如果安装成功，浏览器会自动打开并执行任务。

如果仍有错误，检查：
1. 是否安装了浏览器驱动：`playwright install chromium`
2. 版本是否正确：`pip list | grep -E "browser-use|langchain"`
3. 查看日志中的错误信息

## 常见问题

### Q: 安装后仍有依赖冲突？

**A:** 尝试强制重新安装：
```bash
pip install -r requirements.txt --force-reinstall --no-cache-dir
```

### Q: 浏览器启动失败？

**A:** 确保已安装浏览器驱动：
```bash
playwright install --force chromium
```

### Q: LangChain 版本冲突？

**A:** `browser-use` 需要 LangChain 0.3.x，如果项目其他部分需要旧版本，可能需要：
- 使用虚拟环境隔离
- 或者等待项目整体升级到 LangChain 0.3.x

## 下一步

安装完成后：
1. 重启系统
2. 尝试执行浏览器任务
3. 查看浏览器窗口是否正常打开
4. 检查任务执行结果


