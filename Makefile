.PHONY: stop test restart start start-backend build-web test-task-weather test-mediawiki migrate pre-check install-deps create-venv clean audit disk-scan disk-scan-user help

# 默认目标：在项目根执行 make 时显示可用命令
# 前端说明：源码在 frontend/react-app，构建产物在 frontend/web/dist。
#   make start = 先 pre-check 再构建前端再启动后端，8081 提供最新 UI。
#   make build-web = 仅构建前端（供单独使用或 CI）。
help:
	@echo "用法: make <目标>"
	@echo "目标: stop | start | restart | build-web | test | migrate | pre-check | install-deps | create-venv | clean | disk-scan"
	@echo "  make stop             - 停止后端 (端口 $(WEB_PORT))"
	@echo "  make start            - 预检查依赖 + 构建前端并启动后端（8081 提供最新 UI）"
	@echo "  make restart          - 停止并重新启动后端（不重建前端，快速）"
	@echo "  make build-web        - 仅构建前端到 frontend/web/dist"
	@echo "  make test             - 运行全部测试"
	@echo "  make pre-check        - 验证第三方依赖（ffmpeg、yt-dlp、you-get、whisper，Python 包见 requirements.txt）"
	@echo "  make install-deps     - 安装系统依赖（FFmpeg + pip install + npm install）"
	@echo "  make test-task-weather - 运行天气相关 live 测试"
	@echo "  make test-mediawiki    - MediaWiki search-read 诊断（.env、连接、搜索）"
	@echo "  make migrate          - 执行任务队列 DB 迁移（在 backend 下执行 alembic upgrade head，部署时手动跑）"
	@echo "  make create-venv      - 用 Python 3.12 创建 venv（需 python3.12，如 brew install python@3.12）"
	@echo "  make audit            - 生成开发审计报告（代码统计、提交行数、API 审计）"
	@echo "  make disk-scan        - 全盘磁盘扫描（需 sudo，输出到 docs/disk_report.txt，耗时较长）"
	@echo "  make disk-scan-user   - 仅扫描用户主目录（无需 sudo，输出到 docs/disk_report.txt）"
	@echo "  make clean           - 清理缓存与构建产物（__pycache__、.pytest_cache、.backend.pid 等）"
	@echo "请在项目根目录执行 make。"

audit:
	@test -f "$(VENV_ACTIVATE)" || (echo "错误: 未找到虚拟环境，请先执行 python3 -m venv venv"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && python scripts/run_audit.py"

# MediaWiki search-read 诊断（验证 .env 加载、连接、搜索）
test-mediawiki:
	@cd $(PROJECT_ROOT) && (test -f "$(VENV_ACTIVATE)" && . $(VENV_ACTIVATE) && python scripts/test_mediawiki_search_read.py || python3 scripts/test_mediawiki_search_read.py)

clean:
	@echo "清理缓存与构建产物..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -f $(PID_FILE) 2>/dev/null || true
	@echo "清理完成"

VENV := venv
VENV_ACTIVATE := $(VENV)/bin/activate
# 使用 Makefile 所在目录作为项目根，避免从其他目录执行 make 时 .backend.pid、.env 等路径错乱
# 2026-03-13：原用 pwd，在多个源码目录或子目录执行时会导致 stop 找不到 start 写入的 pid
MAKEFILE_DIR := $(dir $(abspath $(firstword $(MAKEFILE_LIST))))
PROJECT_ROOT := $(patsubst %/,%,$(MAKEFILE_DIR))
PYTHON := $(PROJECT_ROOT)/$(VENV)/bin/python
PID_FILE := $(PROJECT_ROOT)/.backend.pid

# 端口：与 backend 一致，优先 .env 的 WEB_PORT，其次 BACKEND_PORT，默认 8081
WEB_PORT := $(shell grep -E '^WEB_PORT=' $(PROJECT_ROOT)/.env 2>/dev/null | cut -d= -f2 | tr -d ' \r')
ifeq ($(WEB_PORT),)
    WEB_PORT := $(shell grep -E '^BACKEND_PORT=' $(PROJECT_ROOT)/.env 2>/dev/null | cut -d= -f2 | tr -d ' \r')
endif
ifeq ($(WEB_PORT),)
    WEB_PORT := 8081
endif

# stop 与 start 严格对应：停止 start 启动的后端进程
# 1. 若有 .backend.pid（由 start 写入），按 PID 停止
# 2. 否则按端口停止（兼容手动启动或 pid 文件丢失）
stop:
	@echo "1. 检查 .backend.pid..."; \
	if [ -f "$(PID_FILE)" ]; then \
		pid=$$(cat "$(PID_FILE)"); \
		echo "2. 读取 PID: $$pid"; \
		if kill -0 $$pid 2>/dev/null; then \
			echo "3. 发送 SIGTERM 到 PID $$pid"; \
			kill -TERM $$pid 2>/dev/null || true; \
			echo "4. 已停止后端 (PID $$pid)"; \
		else \
			echo "3. 进程 $$pid 已不存在（可能已退出）"; \
			echo "4. 清理 .backend.pid"; \
		fi; \
		rm -f "$(PID_FILE)"; \
		echo "5. 完成"; \
	else \
		echo "2. 未找到 .backend.pid，按端口 $(WEB_PORT) 停止"; \
		echo "3. 查找占用端口 $(WEB_PORT) 的进程..."; \
		pids=$$(lsof -ti :$(WEB_PORT) 2>/dev/null); \
		if [ -n "$$pids" ]; then \
			echo "4. 发送 SIGTERM 到 PID: $$pids"; \
			lsof -ti :$(WEB_PORT) | xargs kill -TERM 2>/dev/null || true; \
			echo "5. 已停止"; \
		else \
			echo "4. 端口 $(WEB_PORT) 无进程占用"; \
			echo "5. 完成"; \
		fi; \
	fi

test:
	@test -f "$(VENV_ACTIVATE)" || (echo "请先创建虚拟环境: python3 -m venv venv && make test"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && pytest -v --tb=short"

test-task-weather:
	@test -f "$(VENV_ACTIVATE)" || (echo "请先创建虚拟环境: python3 -m venv venv"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && pytest backend/core/agent/tools/tests/test_weather_tool_integration.py::TestWeatherToolLiveEnv backend/infrastructure/execution/tests/test_task_handlers.py::TestWeatherQueryLiveEnv -v --tb=short"

migrate:
	@test -f "$(VENV_ACTIVATE)" || (echo "请先创建虚拟环境: python3 -m venv venv"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && cd backend && alembic upgrade head"
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
	@$(PYTHON) -m pip install -U yt-dlp -q
	@test -d "frontend/react-app" && (cd frontend/react-app && npm install) || true
	@echo "系统依赖安装完成"

# 验证第三方依赖（ffmpeg 在 PATH；yt-dlp/you-get/whisper 来自 requirements.txt；google_search 用 DuckDuckGo）
pre-check:
	@test -f "$(VENV_ACTIVATE)" || (echo "错误: 未找到虚拟环境，请先执行 python3 -m venv venv"; exit 1)
	@echo "验证第三方依赖..."
	@command -v ffmpeg >/dev/null 2>&1 || (echo "错误: ffmpeg 未就绪，请手动执行 scripts/install_ffmpeg.sh 或 brew install ffmpeg"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && python -c 'import yt_dlp'" || (echo "错误: yt-dlp 未就绪，请确认已执行 pip install -r requirements.txt 且使用本项目的 venv"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && python -c 'import you_get'" || (echo "错误: you-get 未就绪，请确认已执行 pip install -r requirements.txt 且使用本项目的 venv"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && python -c 'import whisper'" || (echo "错误: whisper 未就绪，请确认已执行 pip install -r requirements.txt 且使用本项目的 venv"; exit 1)
	@bash -c "source $(VENV_ACTIVATE) && python -c 'from backend.core.agent.tools.builtin.google_search_tool import GoogleSearchTool; GoogleSearchTool()'" || (echo "错误: google_search 未就绪，请确认已执行 pip install -r requirements.txt 且使用本项目的 venv"; exit 1)
	@echo "第三方依赖检查通过"

# restart = stop + start-backend（不重建前端，快速重启）
restart: stop
	@echo "--- make restart 步骤 ---"
	@echo "1. 等待端口 $(WEB_PORT) 释放..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do lsof -ti :$(WEB_PORT) >/dev/null 2>&1 || break; sleep 1; done
	@echo "2. 启动后端..."
	@$(MAKE) start-backend

# start-backend：仅启动后端（stop + wait + pre-check + 启动进程 + 等待就绪）
# 被 start 和 restart 复用
start-backend:
	@echo "1. 停止旧后端（若存在）..."
	@$(MAKE) stop
	@echo "2. 等待端口 $(WEB_PORT) 释放（最多 25 秒）..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25; do lsof -ti :$(WEB_PORT) >/dev/null 2>&1 || break; sleep 1; done
	@lsof -ti :$(WEB_PORT) >/dev/null 2>&1 && (echo "错误: 端口 $(WEB_PORT) 仍被占用，请手动执行 make stop 或 lsof -ti :$(WEB_PORT) | xargs kill -9"; exit 1) || true
	@echo "3. 验证第三方依赖..."
	@$(MAKE) pre-check
	@echo "4. 启动后端 (端口 $(WEB_PORT))..."
	@bash -c "cd $(PROJECT_ROOT) && source $(VENV_ACTIVATE) && export WEB_PORT='$(WEB_PORT)' && nohup $(PYTHON) -m backend.main >> $(PROJECT_ROOT)/backend.log 2>&1 & echo \$$! > $(PID_FILE) && sleep 3"
	@echo "5. 等待后端就绪..."
	@PORT=$(WEB_PORT); for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do sleep 2; if curl -sf --connect-timeout 2 --max-time 3 "http://127.0.0.1:$$PORT/health" >/dev/null; then echo "6. 后端已就绪 http://127.0.0.1:$$PORT"; exit 0; fi; done; echo "错误: 连接失败（约 60 秒内未就绪），请查看 backend.log"; exit 1

start: install-deps build-web
	@echo "--- make start 步骤 ---"
	@echo "1. 检查虚拟环境..."
	@test -f "$(VENV_ACTIVATE)" || (echo "错误: 请先创建虚拟环境: python3 -m venv venv"; exit 1)
	@echo "2. 运行开发审计..."
	@bash -c "source $(VENV_ACTIVATE) && python scripts/run_audit.py" || true
	@echo "3. 启动后端..."
	@$(MAKE) start-backend

build-web:
	@test -d "frontend/react-app" || (echo "frontend/react-app 不存在"; exit 1)
	@echo "构建前端 -> frontend/web/dist ..."
	@cd frontend/react-app && npm run build

# 全盘磁盘扫描（需 sudo，可访问 /System、/Library 等，输出到 docs/disk_report.txt）
disk-scan:
	@echo "全盘磁盘扫描（需 sudo，耗时可能较长）..."
	@sudo python3 scripts/disk_system_data_breakdown.py -o docs/disk_report.txt
	@echo "报告已保存到 docs/disk_report.txt"

# 仅扫描用户主目录（无需 sudo，快速）
disk-scan-user:
	@test -f "$(VENV_ACTIVATE)" || (echo "请先创建虚拟环境: python3 -m venv venv"; exit 1)
	@echo "扫描用户主目录..."
	@$(PYTHON) scripts/disk_system_data_breakdown.py --user-only -o docs/disk_report.txt
	@echo "报告已保存到 docs/disk_report.txt"
