.PHONY: help install install-prod install-dev test test-cov lint lint-fix format format-check clean clean-deps clean-all run-backend stop-backend run-frontend run-web start start-cli start-web run run-cli run-web status check-env setup-venv

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
COLOR_RESET := \033[0m
COLOR_BOLD := \033[1m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_RED := \033[31m

# 虚拟环境路径
VENV := venv
VENV_BIN := $(VENV)/bin
VENV_ACTIVATE := $(VENV_BIN)/activate
PYTHON := $(VENV_BIN)/python
PIP := $(VENV_BIN)/pip

help: ## 显示帮助信息
	@echo "$(COLOR_BOLD)可用命令：$(COLOR_RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(COLOR_GREEN)%-20s$(COLOR_RESET) %s\n", $$1, $$2}'

check-env: ## 检查虚拟环境是否存在
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "$(COLOR_YELLOW)⚠️  虚拟环境不存在，请先运行: make setup-venv$(COLOR_RESET)"; \
		exit 1; \
	fi

setup-venv: ## 创建虚拟环境
	@echo "$(COLOR_GREEN)📦 创建虚拟环境...$(COLOR_RESET)"
	@python3 -m venv $(VENV)
	@echo "$(COLOR_GREEN)✅ 虚拟环境创建完成$(COLOR_RESET)"
	@echo "$(COLOR_YELLOW)💡 提示: 运行 'source $(VENV_ACTIVATE)' 激活虚拟环境$(COLOR_RESET)"

install: check-env ## 安装依赖（包含所有工具和测试框架）
	@echo "$(COLOR_GREEN)🔄 更新外部依赖（git submodules）...$(COLOR_RESET)"
	@bash scripts/update_externals.sh
	@echo "$(COLOR_GREEN)📦 安装 Python 依赖...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && $(PIP) install --upgrade pip setuptools wheel"
	@bash -c "source $(VENV_ACTIVATE) && $(PIP) install -r requirements.txt"
	@bash -c "source $(VENV_ACTIVATE) && $(PIP) install -e \".[dev]\""
	@echo "$(COLOR_GREEN)🔨 编译 FFmpeg...$(COLOR_RESET)"
	@bash scripts/install_ffmpeg.sh || echo "$(COLOR_YELLOW)⚠️  FFmpeg 编译失败，某些功能可能不可用$(COLOR_RESET)"
	@echo "$(COLOR_GREEN)🌐 检查浏览器依赖...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && bash scripts/check_browser_deps.sh true"
	@echo "$(COLOR_GREEN)🎤 安装 Whisper...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && bash scripts/install_whisper.sh --download-models"
	@echo "$(COLOR_GREEN)📓 注册 Jupyter kernel...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && $(PYTHON) -m ipykernel install --user --name python3 --display-name \"Python 3\" 2>&1 | grep -v \"ERROR:\" || true"
	@echo "$(COLOR_GREEN)📹 安装视频下载工具...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && bash scripts/install_video_downloaders.sh"
	@echo "$(COLOR_GREEN)🌐 安装 browser-use...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && bash scripts/install_browser_use.sh"
	@echo "$(COLOR_GREEN)📄 安装 PDF 解析器...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && PDF_PARSERS=all bash scripts/install_pdf_parsers.sh"
	@echo "$(COLOR_GREEN)✅ 安装完成！$(COLOR_RESET)"

install-prod: install ## 安装依赖（install 的别名，向后兼容）

install-dev: install ## 安装依赖（install 的别名，向后兼容）

test: check-env ## 运行测试并保存结果到数据库
	@echo "$(COLOR_GREEN)🧪 运行测试并保存结果到数据库...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && python -c \"import sys; sys.path.insert(0, '.'); from backend.api.test_routes import run_pytest; from backend.infrastructure.storage.test_results_db import get_test_results_db; result = run_pytest(verbose=True, coverage=False); test_db = get_test_results_db(); run_id = test_db.save_test_run(result=result); print(f'✓ 测试完成: {result.get(\\\"total_tests\\\", 0)} 个测试, {result.get(\\\"passed\\\", 0)} 通过, {result.get(\\\"failed\\\", 0)} 失败, 运行 ID: {run_id}')\""

test-cov: check-env ## 运行测试并生成覆盖率报告
	@echo "$(COLOR_GREEN)🧪 运行测试并生成覆盖率报告...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && pytest --cov=backend --cov=frontend --cov=shared --cov-report=term-missing --cov-report=html"

lint: check-env ## 代码检查
	@echo "$(COLOR_GREEN)🔍 运行代码检查...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && flake8 backend frontend shared" || echo "$(COLOR_YELLOW)⚠️  flake8 检查发现问题$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && mypy backend frontend shared" || echo "$(COLOR_YELLOW)⚠️  mypy 检查发现问题$(COLOR_RESET)"

lint-fix: check-env ## 自动修复部分代码问题
	@echo "$(COLOR_GREEN)🔧 自动修复代码问题...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && flake8 --select=E9,F63,F7,F82 --show-source --statistics backend frontend shared" || true
	@echo "$(COLOR_YELLOW)💡 提示: flake8 只能检查问题，需要手动修复$(COLOR_RESET)"

format: check-env ## 格式化代码
	@echo "$(COLOR_GREEN)✨ 格式化代码...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && black backend frontend shared"
	@bash -c "source $(VENV_ACTIVATE) && isort backend frontend shared"

format-check: check-env ## 检查代码格式（不修改）
	@echo "$(COLOR_GREEN)🔍 检查代码格式...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && black --check backend frontend shared" || echo "$(COLOR_YELLOW)⚠️  代码格式不符合 black 规范$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && isort --check backend frontend shared" || echo "$(COLOR_YELLOW)⚠️  代码格式不符合 isort 规范$(COLOR_RESET)"

clean: ## 清理构建文件（不删除依赖）
	@echo "$(COLOR_GREEN)🧹 清理构建文件...$(COLOR_RESET)"
	@rm -rf build dist *.egg-info
	@find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	@echo "$(COLOR_GREEN)✅ 清理完成$(COLOR_RESET)"

clean-deps: ## 清理所有安装的依赖（虚拟环境、FFmpeg、Whisper 模型等）
	@echo "$(COLOR_YELLOW)⚠️  这将删除虚拟环境和所有依赖，确定要继续吗？$(COLOR_RESET)"
	@read -p "输入 'yes' 继续: " confirm && [ "$$confirm" = "yes" ] || exit 1
	@bash scripts/clean_deps.sh

clean-all: clean clean-deps ## 清理所有文件（构建文件 + 依赖）

run-backend: check-env ## 启动后端服务（绝对重启：先停止并清除环境，再启动）
	@echo "$(COLOR_GREEN)🚀 启动后端服务...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && $(PYTHON) cli.py restart --foreground"

stop-backend: check-env ## 停止后端服务并清除运行环境
	@echo "$(COLOR_GREEN)🛑 停止后端服务...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && $(PYTHON) cli.py stop --cleanup"

status: check-env ## 查看后端服务状态
	@bash -c "source $(VENV_ACTIVATE) && $(PYTHON) cli.py status"

run-frontend: check-env ## 启动前端 CLI
	@echo "$(COLOR_GREEN)🖥️  启动前端 CLI...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && $(PYTHON) -m frontend.main chat"

run-web: check-env ## 启动 Web 前端服务
	@echo "$(COLOR_GREEN)🌐 启动 Web 前端服务...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && $(PYTHON) -m frontend.web.main"

start: check-env ## 一键启动（后端+CLI前端+Web前端，推荐）
	@echo "$(COLOR_GREEN)🚀 一键启动（后端+CLI前端+Web前端）...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && bash scripts/check_browser_deps.sh && $(PYTHON) cli.py restart --wait && $(PYTHON) -m frontend.start_all"

start-cli: check-env ## 一键启动（后端+CLI前端）
	@echo "$(COLOR_GREEN)🚀 一键启动（后端+CLI前端）...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && bash scripts/check_browser_deps.sh && $(PYTHON) cli.py restart --wait && $(PYTHON) -m frontend.main chat"

start-web: check-env ## 一键启动（后端+Web前端）
	@echo "$(COLOR_GREEN)🚀 一键启动（后端+Web前端）...$(COLOR_RESET)"
	@bash -c "source $(VENV_ACTIVATE) && bash scripts/check_browser_deps.sh && $(PYTHON) cli.py restart --wait && $(PYTHON) -m frontend.web.main"

run: start ## 启动后端（后台）+ CLI前端（交互式）+ Web前端（后台，推荐）

run-cli: start-cli ## 启动后端（后台）+ CLI前端（交互式）

run-web: start-web ## 启动后端（后台）+ Web前端
