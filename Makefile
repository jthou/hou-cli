.PHONY: help install install-prod install-dev test lint format clean clean-deps run-backend run-frontend run start stop-backend

help: ## 显示帮助信息
	@echo "可用命令："
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装开发依赖（默认，包含所有工具和测试框架）
	@echo "🔄 更新外部依赖（git submodules）..."
	@bash scripts/update_externals.sh
	@bash -c "source venv/bin/activate && pip install -r requirements-dev.txt"
	@bash -c "source venv/bin/activate && pip install -e \".[dev]\""
	@bash scripts/install_ffmpeg.sh
	@bash -c "source venv/bin/activate && bash scripts/check_browser_deps.sh true"
	@bash -c "source venv/bin/activate && bash scripts/install_whisper.sh --download-models"
	# Jupyter 依赖已在 requirements-dev.txt 中，但需要注册 kernel
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

test: ## 运行测试
	@bash -c "source venv/bin/activate && pytest"

lint: ## 代码检查
	@bash -c "source venv/bin/activate && flake8 backend frontend shared"
	@bash -c "source venv/bin/activate && mypy backend frontend shared"

format: ## 格式化代码
	@bash -c "source venv/bin/activate && black backend frontend shared"
	@bash -c "source venv/bin/activate && isort backend frontend shared"

format-check: ## 检查代码格式（不修改）
	@bash -c "source venv/bin/activate && black --check backend frontend shared"
	@bash -c "source venv/bin/activate && isort --check backend frontend shared"

clean: ## 清理构建文件（不删除依赖）
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

clean-deps: ## 清理所有安装的依赖（虚拟环境、FFmpeg、Whisper 模型等）
	@bash scripts/clean_deps.sh

run-backend: ## 启动后端服务（绝对重启：先停止并清除环境，再启动）
	@bash -c "source venv/bin/activate && python cli.py restart --foreground"

stop-backend: ## 停止后端服务并清除运行环境
	@bash -c "source venv/bin/activate && python cli.py stop --cleanup"

run-frontend: ## 启动前端 CLI
	@bash -c "source venv/bin/activate && python -m frontend.main chat"

start: ## 一键启动（后端+前端，推荐）
	@bash -c "source venv/bin/activate && bash scripts/check_browser_deps.sh && python cli.py restart --wait && python -m frontend.main chat"

run: ## 启动后端（后台）+ 前端（交互式，推荐）
	@make start


