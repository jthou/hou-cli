.PHONY: help install install-dev test lint format clean run-backend run-frontend run

help: ## 显示帮助信息
	@echo "可用命令："
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装生产依赖
	pip install -e .

install-dev: ## 安装开发依赖
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
	@bash -c "source venv/bin/activate && python -m backend.main"

run-backend-bg: ## 启动后端服务（后台运行）
	@bash -c "source venv/bin/activate && python cli.py start"

run-frontend: ## 启动前端 CLI
	@bash -c "source venv/bin/activate && python -m frontend.main chat"

stop-backend: ## 停止后端服务
	@bash -c "source venv/bin/activate && python cli.py stop"

status-backend: ## 查看后端状态
	@bash -c "source venv/bin/activate && python cli.py status"

restart-backend: ## 重启后端服务
	@bash -c "source venv/bin/activate && python cli.py restart"

start: ## 一键启动后端（后台运行，推荐）
	@bash -c "source venv/bin/activate && python cli.py start"
	@echo ""
	@echo "💡 提示:"
	@echo "   - 启动前端: make run-frontend 或 ./start-frontend.sh"
	@echo "   - 停止后端: make stop-backend 或 ./stop.sh"
	@echo "   - 查看状态: make status-backend"

run: ## 启动后端（后台）+ 前端（交互式，推荐）
	@bash -c "source venv/bin/activate && python cli.py start"
	@echo ""
	@bash -c "source venv/bin/activate && python -m frontend.main chat"

