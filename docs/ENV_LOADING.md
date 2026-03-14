# .env 加载逻辑梳理

> 梳理时间：2025-03-13  
> 梳理理由：统一 .env 加载行为，避免空占位覆盖凭据、脚本与主程序行为不一致  
> 梳理方法：全项目 grep load_dotenv/.env，逐文件分析加载顺序与 override 行为  
> 统一实现：2025-03-13，已封装为 shared/load_env.py，所有入口统一调用

---

## 一、标准加载逻辑（shared/load_env.py）

**顺序**：项目根 → 用户配置目录 → 当前目录  
**override**：全部 True，后续文件覆盖前面的，确保用户凭据（config_dir）覆盖项目根空占位

```python
# shared/load_env.py
from shared.load_env import load_env
load_env(project_root)  # 或 load_env_for_file(__file__)
```

**设计意图**：
- 项目根 .env 通常用于开发、CI，可能含空占位
- 用户配置 `~/.config/hou-cli/.env` 含真实凭据
- 后加载 override=True，用户凭据覆盖项目根空占位

---

## 二、各入口/模块加载情况

### 2.1 后端入口

| 文件 | 加载顺序 | override | 说明 |
|------|----------|----------|------|
| `backend/main.py` | 项目根 → config_dir → cwd | True, False, False | 主入口，标准逻辑 |
| `backend/api/routes.py` | 同上 | 同上 | 被 main 导入时执行，与 main 一致 |

**执行顺序**：`main.py` 先执行 load_dotenv，再 `import routes`，routes 再次 load_dotenv（结果一致）。

---

### 2.2 前端 CLI 入口

| 文件 | 加载顺序 | override | 说明 |
|------|----------|----------|------|
| `frontend/main.py` | config_dir → 项目根 → cwd（非打包） | 默认 False | **只加载第一个存在的文件**（break） |
| `frontend/main.py` check_config() | user_env 或 project_env | override=True | 配置检查时清除 DEEPSEEK_API_KEY 后重载 |

**差异**：
- 前端 CLI 按「第一个存在」加载，与后端「全部加载、后不覆盖」不同
- 打包环境仅考虑 config_dir

---

### 2.3 编排器（被路由导入时执行）

| 文件 | 加载顺序 | override | 说明 |
|------|----------|----------|------|
| `backend/core/agent/orchestrator.py` | 仅项目根 | 默认 False | **不加载 config_dir**，在导入 LLMService 前执行 |

**影响**：若 orchestrator 被独立导入（如单测），可能缺少 `~/.config/hou-cli/.env` 的凭据。

---

### 2.4 脚本

| 文件 | 加载顺序 | override | 说明 |
|------|----------|----------|------|
| `scripts/test_mediawiki_search_read.py` | 项目根 → config_dir → cwd | True, False, False | ✅ 与 main 一致 |
| `scripts/diagnose_weather_timeout.py` | config_dir → 项目根 → cwd | 默认 False | ⚠️ **只加载第一个存在的**，顺序与 main 相反 |
| `scripts/test_wechat_mp_api.py` | 仅项目根 | 默认 False | 存在则加载，否则 load_dotenv() |
| `scripts/verify_google_search_in_llm.py` | 仅项目根 | 默认 False | 同上 |
| `scripts/test_autonomous_executor.py` | 仅项目根 | 默认 False | 同上 |
| `scripts/test_work_assistant_prompt.py` | 仅项目根 | override 未显式指定 | load_dotenv(project_root / ".env") |

---

### 2.5 测试文件

| 文件 | 加载逻辑 | 说明 |
|------|----------|------|
| `backend/services/llm/tests/__init__.py` | 项目根 → cwd，**无 config_dir** | override=True，只加载第一个 |
| `backend/core/agent/tools/tests/test_weather_tool_integration.py` | config_dir → 项目根 → cwd | override=True 逐个加载 |
| `backend/infrastructure/execution/tests/test_task_handlers.py` | config_dir → 项目根 → cwd | override=True 逐个加载 |
| `backend/core/agent/skills/video_editing/scripts/test_video_editing.py` | 项目根 → 用户 config | 存在则加载 |
| 多数 `test_*.py` | `load_dotenv()` 无路径 | 依赖 pytest 运行目录或已加载的 env |

---

### 2.6 直接读取 .env 文件（非 load_dotenv）

| 文件 | 用途 |
|------|------|
| `backend/utils/env_models_parser.py` | 解析 .env 中 `*_MODEL` 变量，供 model_availability 等使用 |
| `frontend/react-app/vite.config.js` | 读取 `WEB_PORT` / `BACKEND_PORT` 配置代理端口 |

---

## 三、导入链与执行顺序

```
python -m backend.main
  → main.py load_dotenv (项目根→config_dir→cwd)
  → import backend.api.routes
    → routes.py load_dotenv (同上)
    → import mediawiki_routes, chat_routes, ...
      → 可能 import orchestrator
        → orchestrator load_dotenv (仅项目根，override 默认 False)
```

结论：正常启动时 main/routes 已加载完整 env，orchestrator 的加载不会覆盖已有值。

---

## 四、不一致点汇总

1. **diagnose_weather_timeout.py**：config_dir 优先且只加载一个，与 main 相反。
2. **frontend/main.py**：只加载第一个存在的文件，与后端「全部加载、后不覆盖」不同。
3. **orchestrator.py**：不加载 config_dir，独立运行时可能缺凭据。
4. **多数脚本**：仅加载项目根，未考虑 config_dir。
5. **LLM tests __init__.py**：无 config_dir，且 override=True 只加载第一个。

---

## 五、建议

1. **新增 `shared/load_env.py`**：统一封装标准加载逻辑，供 main、routes、脚本、测试复用。
2. **统一脚本**：`diagnose_weather_timeout.py`、`test_wechat_mp_api.py` 等改为使用 shared 逻辑。
3. **orchestrator**：改为调用 shared 加载，或依赖 main/routes 已加载，移除自身 load_dotenv。
4. **文档**：在 env.example 或 README 中注明「修改 .env 后需重启后端」。
