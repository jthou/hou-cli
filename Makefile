.PHONY: help install install-dev test lint format clean run-backend run-backend-bg run-frontend run start stop-backend status-backend restart-backend install-browser-deps

help: ## 显示帮助信息
	@echo "可用命令："
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装生产依赖
	pip install -r requirements.txt
	pip install -e .

install-dev: ## 安装开发依赖
	pip install -r requirements-dev.txt
	pip install -e ".[dev]"

test: ## 运行测试
	pytest

lint: ## 代码检查
	flake8 backend frontend shared
	mypy backend frontend shared

format: ## 格式化代码
	black backend frontend shared
	isort backend frontend shared

format-check: ## 检查代码格式（不修改）
	black --check backend frontend shared
	isort --check backend frontend shared

clean: ## 清理构建文件
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

run-backend: ## 启动后端服务（前台运行，用于调试）
	@bash -c "source venv/bin/activate && bash scripts/check_browser_deps.sh && python -m backend.main"

run-backend-bg: ## 启动后端服务（后台运行）
	@bash -c "source venv/bin/activate && bash scripts/check_browser_deps.sh && python cli.py start"

run-frontend: ## 启动前端 CLI
	@bash -c "source venv/bin/activate && python -m frontend.main chat"

stop-backend: ## 停止后端服务
	@bash -c "source venv/bin/activate && python cli.py stop"

status-backend: ## 查看后端状态
	@bash -c "source venv/bin/activate && python cli.py status"

restart-backend: ## 重启后端服务
	@bash -c "source venv/bin/activate && python cli.py restart"

start: ## 一键启动（后端+前端，推荐）
	@bash -c "source venv/bin/activate && bash scripts/check_browser_deps.sh && python cli.py start --wait && python -m frontend.main chat"

run: ## 启动后端（后台）+ 前端（交互式，推荐）
	@make start

install-browser-deps: ## 安装 browser-use 相关依赖（可选功能）
	@bash -c "source venv/bin/activate && bash scripts/check_browser_deps.sh true"

