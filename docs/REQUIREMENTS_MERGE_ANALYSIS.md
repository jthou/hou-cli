# Requirements 文件合并分析

## 当前状态

### requirements.txt
- 生产依赖（核心功能）
- 约 20 个包

### requirements.txt
- 包含所有生产依赖（通过 `-r requirements.txt`）
- 额外添加开发依赖（测试、代码质量、调试工具等）
- 约 30+ 个包

### Makefile 命令差异

**`make install`**:
- 安装 `requirements.txt`（生产依赖）
- 安装 `mineru`（基础 PDF 解析器）
- 不下载 Whisper 模型
- 不注册 Jupyter kernel

**`make install-dev`**:
- 安装 `requirements.txt`（包含所有生产依赖 + 开发依赖）
- 安装所有 PDF 解析器（mineru[all], camelot-py[cv]）
- 下载 Whisper 模型
- 注册 Jupyter kernel

## 合并方案

### 方案 1: 保持现状（推荐）✅

**优点**:
- 符合 Python 项目标准实践
- 生产环境不需要安装测试工具、代码检查工具等
- 依赖清晰，易于维护

**缺点**:
- 需要记住两个命令
- 新开发者可能不知道用哪个

### 方案 2: 简化但保留选项（折中）✅

**思路**:
- `make install` 默认安装开发依赖（更常用）
- `make install-prod` 用于生产环境（只安装生产依赖）

**优点**:
- 简化日常开发流程
- 保留生产环境选项
- 向后兼容（可以保留 install-dev 作为别名）

### 方案 3: 完全合并（不推荐）❌

**思路**:
- 合并为一个 requirements.txt
- 只保留一个 `make install` 命令

**缺点**:
- 生产环境会安装不必要的开发工具
- 增加部署包大小
- 不符合 Python 项目最佳实践

## 推荐方案：方案 2

### 实施步骤

1. **保持 requirements.txt 和 requirements.txt 分离**（标准做法）
2. **修改 Makefile**：
   - `make install` → 安装开发依赖（当前 install-dev 的行为）
   - `make install-prod` → 安装生产依赖（当前 install 的行为）
   - `make install-dev` → 作为 `install` 的别名（向后兼容）

3. **更新文档**：
   - README 中说明 `make install` 安装开发依赖
   - 生产部署使用 `make install-prod`

## 实施建议

如果选择方案 2，可以这样修改：

```makefile
install: ## 安装开发依赖（默认，包含所有工具和测试框架）
	@echo "🔄 更新外部依赖（git submodules）..."
	@bash scripts/update_externals.sh
	@bash -c "source venv/bin/activate && pip install -r requirements.txt"
	@bash -c "source venv/bin/activate && pip install -e \".[dev]\""
	@bash scripts/install_ffmpeg.sh
	@bash -c "source venv/bin/activate && bash scripts/check_browser_deps.sh true"
	@bash -c "source venv/bin/activate && bash scripts/install_whisper.sh --download-models"
	@bash -c "source venv/bin/activate && python -m ipykernel install --user --name python3 --display-name \"Python 3\" 2>&1 | grep -v \"ERROR:\" || true"
	@bash -c "source venv/bin/activate && bash scripts/install_video_downloaders.sh"
	@bash -c "source venv/bin/activate && bash scripts/install_browser_use.sh"
	@bash -c "source venv/bin/activate && PDF_PARSERS=all bash scripts/install_pdf_parsers.sh"

install-prod: ## 安装生产依赖（仅核心功能，用于生产部署）
	@echo "🔄 更新外部依赖（git submodules）..."
	@bash scripts/update_externals.sh
	@bash -c "source venv/bin/activate && pip install -r requirements.txt"
	@bash -c "source venv/bin/activate && pip install -e ."
	@bash scripts/install_ffmpeg.sh
	@bash -c "source venv/bin/activate && bash scripts/check_browser_deps.sh true"
	@bash -c "source venv/bin/activate && bash scripts/install_whisper.sh"
	@bash -c "source venv/bin/activate && bash scripts/install_jupyter.sh"
	@bash -c "source venv/bin/activate && bash scripts/install_video_downloaders.sh"
	@bash -c "source venv/bin/activate && bash scripts/install_browser_use.sh"
	@bash -c "source venv/bin/activate && PDF_PARSERS=mineru bash scripts/install_pdf_parsers.sh"

install-dev: install ## 安装开发依赖（install 的别名，向后兼容）
```

## 总结

- **requirements 文件**：保持分离（标准做法）
- **Makefile 命令**：可以简化，让 `install` 默认安装开发依赖
- **向后兼容**：保留 `install-dev` 作为别名



