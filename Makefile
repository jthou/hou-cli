.PHONY: stop test restart start test-task-weather help

# 默认目标：在项目根执行 make 时显示可用命令
help:
	@echo "用法: make <目标>"
	@echo "目标: stop | test | restart | start | test-task-weather"
	@echo "  make stop             - 停止后端 (端口 $(WEB_PORT))"
	@echo "  make test             - 运行全部测试"
	@echo "  make restart          - 停止并重新启动后端"
	@echo "  make start            - 启动后端"
	@echo "  make test-task-weather - 运行天气相关 live 测试"
	@echo "请在项目根目录执行 make。"

VENV := venv
VENV_ACTIVATE := $(VENV)/bin/activate
PYTHON := $(VENV)/bin/python
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

restart: stop
	@echo "等待端口 $(WEB_PORT) 释放..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do lsof -ti :$(WEB_PORT) >/dev/null 2>&1 || break; sleep 1; done
	@$(MAKE) start

start:
	@test -f "$(VENV_ACTIVATE)" || (echo "请先创建虚拟环境: python3 -m venv venv"; exit 1)
	@echo "启动后端..."
	@bash -c "source $(VENV_ACTIVATE) && (nohup $(PYTHON) -m backend.main >> backend.log 2>&1 &) && sleep 1"
	@PORT=$(WEB_PORT); for i in 1 2 3 4 5 6 7 8 9 10; do sleep 2; if curl -sf --connect-timeout 2 --max-time 3 "http://127.0.0.1:$$PORT/health" >/dev/null; then echo "后端已就绪 http://127.0.0.1:$$PORT"; exit 0; fi; done; echo "连接失败，请查看 backend.log"; exit 1
