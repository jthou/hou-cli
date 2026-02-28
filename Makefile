.PHONY: stop test restart start start-web build-web test-task-weather migrate pre-check install-deps create-venv help

# 默认目标：在项目根执行 make 时显示可用命令
# 前端说明：源码在 frontend/react-app，构建产物在 frontend/web/dist。
#   make start = 先 pre-check 再构建前端再启动后端，8081 提供最新 UI。
#   make build-web = 仅构建前端（供单独使用或 CI）。
#   make start-web = 起 Vite 开发服务器（热更新），API 走代理到 8081，需后端已起。
help:
	@echo "用法: make <目标>"
	@echo "目标: stop | test | restart | start | start-web | build-web | test-task-weather | migrate | pre-check | create-venv"
	@echo "  make stop             - 停止后端 (端口 $(WEB_PORT))"
	@echo "  make test             - 运行全部测试"
	@echo "  make restart          - 停止并重新启动后端"
	@echo "  make start            - 预检查依赖 + 构建前端并启动后端（8081 提供最新 UI）"
	@echo "  make pre-check        - 验证第三方依赖（ffmpeg、yt-dlp、you-get、whisper，Python 包见 requirements.txt）"
	@echo "  make install-deps     - 安装系统依赖（FFmpeg + pip install + npm install）"
	@echo "  make build-web        - 仅构建前端到 frontend/web/dist"
	@echo "  make start-web        - 启动前端开发服务器 Vite（热更新，API 代理到 8081）"
	@echo "  make test-task-weather - 运行天气相关 live 测试"
	@echo "  make migrate          - 执行任务队列 DB 迁移（alembic upgrade head，部署时手动跑）"
	@echo "  make create-venv      - 用 Python 3.12 创建 venv（需 python3.12，如 brew install python@3.12）"
	@echo "请在项目根目录执行 make。"

VENV := venv
VENV_ACTIVATE := $(VENV)/bin/activate
# 使用絕對路徑，避免 conda/base 與 venv 混用時 python 指向錯誤
PROJECT_ROOT := $(shell pwd)
PYTHON := $(PROJECT_ROOT)/$(VENV)/bin/python
WEB_PORT ?= 8081

stop:
	@-lsof -ti :$(WEB_PORT) | xargs kill -TERM 2>/dev/null || true
	@echo "已停止"

test:
	@test -f "$(VENV_ACTIVATE)" || (echo "请先创建虚拟环境: python3 -m venv venv && make test"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && pytest -v --tb=short"

test-task-weather:
	@test -f "$(VENV_ACTIVATE)" || (echo "请先创建虚拟环境: python3 -m venv venv"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && pytest backend/core/agent/tools/tests/test_weather_tool_integration.py::TestWeatherToolLiveEnv backend/infrastructure/execution/tests/test_task_handlers.py::TestWeatherQueryLiveEnv -v --tb=short"

migrate:
	@test -f "$(VENV_ACTIVATE)" || (echo "请先创建虚拟环境: python3 -m venv venv"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && alembic upgrade head"
	@echo "迁移完成"

# 用 Python 3.12 创建 venv（mineru 等依赖需 3.10+，conda 的 python3 可能是 3.9）
create-venv:
	@command -v python3.12 >/dev/null 2>&1 || (echo "错误: 未找到 python3.12，请执行 brew install python@3.12"; exit 1)
	@rm -rf venv && python3.12 -m venv venv
	@echo "venv 已创建（Python 3.12），请执行 make install-deps"

# 安装系统级第三方依赖（FFmpeg + requirements.txt 中的 Python 包 + 前端 npm 包）
# 若曾以 editable 安裝於 backend/externals/（目錄已刪），需先卸載再從 PyPI 重裝
install-deps:
	@test -f "$(VENV_ACTIVATE)" || (echo "错误: 未找到虚拟环境，请先执行 python3 -m venv venv"; exit 1)
	@echo "安装系统依赖（FFmpeg + Python 包 + 前端 npm 包）..."
	@bash scripts/install_ffmpeg.sh
	@for pkg in yt-dlp you-get openai-whisper; do \
	  ($(PYTHON) -m pip show $$pkg 2>/dev/null | grep -q "externals") && $(PYTHON) -m pip uninstall -y $$pkg || true; \
	done
	@$(PYTHON) -m pip install -r requirements.txt -q
	@test -d "frontend/react-app" && (cd frontend/react-app && npm install) || true
	@echo "系统依赖安装完成"

# 验证第三方依赖（ffmpeg 在 PATH；yt-dlp/you-get/whisper 来自 requirements.txt）
pre-check:
	@test -f "$(VENV_ACTIVATE)" || (echo "错误: 未找到虚拟环境，请先执行 python3 -m venv venv"; exit 1)
	@echo "验证第三方依赖..."
	@command -v ffmpeg >/dev/null 2>&1 || (echo "错误: ffmpeg 未就绪，请手动执行 scripts/install_ffmpeg.sh 或 brew install ffmpeg"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && python -c 'import yt_dlp'" || (echo "错误: yt-dlp 未就绪，请确认已执行 pip install -r requirements.txt 且使用本项目的 venv"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && python -c 'import you_get'" || (echo "错误: you-get 未就绪，请确认已执行 pip install -r requirements.txt 且使用本项目的 venv"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && python -c 'import whisper'" || (echo "错误: whisper 未就绪，请确认已执行 pip install -r requirements.txt 且使用本项目的 venv"; exit 1)
	@echo "第三方依赖检查通过"

restart: stop
	@echo "等待端口 $(WEB_PORT) 释放..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do lsof -ti :$(WEB_PORT) >/dev/null 2>&1 || break; sleep 1; done
	@$(MAKE) start

start: install-deps build-web
	@test -f "$(VENV_ACTIVATE)" || (echo "请先创建虚拟环境: python3 -m venv venv"; exit 1)
	@echo "停止旧后端（若存在）..."
	@-lsof -ti :$(WEB_PORT) | xargs kill -TERM 2>/dev/null || true
	@echo "等待端口 $(WEB_PORT) 释放（最多 25 秒）..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25; do lsof -ti :$(WEB_PORT) >/dev/null 2>&1 || break; sleep 1; done
	@lsof -ti :$(WEB_PORT) >/dev/null 2>&1 && (echo "错误: 端口 $(WEB_PORT) 仍被占用，请手动执行 make stop 或 lsof -ti :$(WEB_PORT) | xargs kill -9"; exit 1) || true
	@$(MAKE) pre-check
	@echo "启动后端..."
	@bash -c "source $(VENV_ACTIVATE) && (nohup $(PYTHON) -m backend.main >> backend.log 2>&1 &) && sleep 3"
	@PORT=$(WEB_PORT); for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do sleep 2; if curl -sf --connect-timeout 2 --max-time 3 "http://127.0.0.1:$$PORT/health" >/dev/null; then echo "后端已就绪 http://127.0.0.1:$$PORT"; exit 0; fi; done; echo "连接失败（约 60 秒内未就绪），请查看 backend.log"; exit 1

build-web:
	@test -d "frontend/react-app" || (echo "frontend/react-app 不存在"; exit 1)
	@echo "构建前端 -> frontend/web/dist ..."
	@cd frontend/react-app && npm run build

start-web:
	@test -d "frontend/react-app" || (echo "frontend/react-app 不存在"; exit 1)
	@echo "启动前端 (Vite)..."
	@cd frontend/react-app && npm run dev
