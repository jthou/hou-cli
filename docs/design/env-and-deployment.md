# 开发 / 生产环境分离与部署方式

## 1. 目标

- **dev**：本地开发，可开调试、详细日志、热更新；API/前端可同机或代理。
- **production**：对外或内网使用，关闭调试、INFO 日志、前端为构建后静态资源。
- 配置不写死、不混用（如 dev 不连生产 API Key、生产不打开 DEBUG）。

---

## 2. 当前机制

### 2.1 后端

- **环境标识**：`shared/config.py` 读 `ENV`（默认 `development`），`DEBUG` 为 true 时也视为开发。
- **行为**：
  - `config.is_development` → 日志 DEBUG、uvicorn log_level=debug、控制台输出开发提示。
  - `config.is_production` → 日志 INFO、uvicorn info、无调试提示。
- **配置来源**：`backend/main.py` 依次从 `~/.config/hou-cli/.env`、项目根 `.env`、`Path.cwd()/.env` 加载；先找到先赢。

结论：**后端已按 ENV/DEBUG 区分 dev/prod 行为**，分离依赖「不同环境用不同 .env 或不同 ENV 值」。

### 2.2 前端

- **开发**：`npm run dev` 起 Vite，`vite.config.js` 里 proxy `/api`、`/ws` 到 `http://127.0.0.1:8081`；请求用相对路径 `/api/...`，无跨域。
- **生产**：`npm run build` 产出到 `frontend/web/dist`，由后端 FastAPI 挂载同一域名；页面和 API 同源，仍用相对路径即可。

结论：**前端未读 NODE_ENV/VITE_* 做业务分支**，dev/prod 差异仅来自「谁在提供 /api」（Vite 代理 vs 真实后端）。若要前端也区分环境（例如隐藏调试入口、不同统计 key），再引入 `VITE_APP_ENV` 即可。

---

## 3. 如何做到 product 与 dev 分离（不强制 Docker）

### 3.1 原则

- 环境由**环境变量 + 配置文件**决定，不写死在代码里。
- 同一套代码，通过「加载哪份配置、设哪个 ENV」区分 dev/prod。

### 3.2 后端

| 项     | 做法 |
|--------|------|
| 环境   | 启动前设 `ENV=production` 或 `ENV=development`（或由 .env 提供）。 |
| 配置   | **开发**：用项目根 `.env` 或 `~/.config/hou-cli/.env`（dev 用 API Key、本地端口等）。**生产**：同路径但另一份内容，或单独路径如 `~/.config/hou-cli/.env.production`，需在启动前 `export ENV=production` 且让 dotenv 加载该文件（当前代码只认 `.env`，可扩展为按 ENV 加载 `.env.production`）。 |
| 端口   | 用 `WEB_PORT` / `BACKEND_PORT`，dev 可与 prod 不同。 |
| 日志   | 已按 `config.is_development` 切 DEBUG/INFO，无需改代码。 |

可选代码增强：在 `backend/main.py` 的 env 加载逻辑里，若存在 `ENV` 且存在 `.env.{ENV}`，则优先或追加加载该文件（例如 `ENV=production` 时加载 `.env.production`），便于「同一目录多文件」管理。

### 3.3 前端

| 项     | 做法 |
|--------|------|
| 开发   | `npm run dev`，Vite 代理到后端；无需改代码。 |
| 生产   | `npm run build`，产物给后端挂载；API 同源，相对路径即可。 |
| 可选   | 若需前端逻辑区分环境（如隐藏调试、不同上报）：在 `vite.config.js` 中定义 `define: { 'import.meta.env.VITE_APP_ENV': JSON.stringify(process.env.VITE_APP_ENV || process.env.NODE_ENV || 'development') }`，构建时传 `VITE_APP_ENV=production`；代码里用 `import.meta.env.VITE_APP_ENV === 'production'` 分支。 |

当前架构下，**不设 VITE_APP_ENV 也能完成 dev/prod 分离**，后端和前端都是「谁在跑、用哪份配置」决定环境。

### 3.4 小结（无 Docker）

- **Dev**：本机 `ENV=development`（或默认）、用 `.env`；`make start` 或先起后端再 `npm run dev`；前端走 Vite 代理。
- **Prod**：同一台或另一台机器上 `ENV=production`、用生产用 .env（端口、API Key、日志级别等）；先 `npm run build` 再起后端；只访问后端地址，前端由后端提供。

---

## 4. 是否需要改为 Docker 部署？

### 4.1 Docker 能带来什么

- **一致运行环境**：镜像内系统依赖（Python、Node 构建结果、可选 ffmpeg/Chromium）固定，减少「本机可跑、服务器报错」。
- **部署形态统一**：同一镜像可跑在本地、自建机、云主机、K8s 等；通过环境变量区分 dev/prod。
- **进程与依赖隔离**：不污染本机 Python/Node 版本；可选多阶段构建：先 Node 构建前端，再只保留静态文件 + Python 后端进最终镜像。

### 4.2 Docker 不能替代的

- **环境分离**：dev/prod 仍要靠 **ENV 与配置**（env 文件或 `-e ENV=production`）区分，Docker 只是把「谁在跑」变成「容器内跑」，配置从外部注入。
- **密钥与敏感配置**：不应打进镜像，应通过 env 文件、编排或密钥管理在运行时注入。

### 4.3 建议

- **仅做 dev/prod 分离、本机或单机部署**：**不必**上 Docker；把 ENV、.env 和启动方式说清楚即可（见上节）。
- **需要以下任一再考虑 Docker**：  
  - 希望**同一镜像**在多地、多环境一致运行；  
  - 部署目标为 **K8s/ECS/云函数** 等容器化平台；  
  - 希望把 **ffmpeg、Chromium、系统库** 一起打包，避免在每台机器上手动装依赖；  
  - 多服务编排（后端 + 队列、缓存等）用 **docker-compose** 更清晰。

若采用 Docker，建议：

- **镜像**：多阶段构建，最终镜像只含 Python 运行时 + 后端代码 + `frontend/web/dist` 静态资源；不把 Node 装进生产镜像。
- **环境**：`docker run` 或 compose 中 `environment: ENV=production`，并将 `.env.production` 以 env_file 或 volumes 注入，不把密钥写进 Dockerfile。
- **dev**：可用 `docker-compose.yml` 挂载代码目录、ENV=development，便于本地联调；prod 用另一份 compose 或同一 compose 不同 env 文件。

---

## 5. 实施顺序建议

1. **先落实「配置级」分离**  
   - 约定并文档化：dev 用哪份 .env、prod 用哪份、ENV 如何设。  
   - 可选：后端支持按 ENV 加载 `.env.{ENV}`。  
   - 前端按需增加 `VITE_APP_ENV` 与构建时传参。

2. **再补「运行方式」文档**  
   - 开发：`make start` 或 后端 + `npm run dev` 的步骤。  
   - 生产：构建命令、启动命令、端口、反向代理（若用 Nginx）等。

3. **有明确需求再上 Docker**  
   - 编写 Dockerfile（多阶段）和 docker-compose 示例（dev/prod 各一份或一份两用），并在文档中说明如何用镜像做 dev/prod 分离。

这样可以在**不强制 Docker** 的前提下做到 product 与 dev 环境分离；Docker 作为可选部署形态，在需要一致性与可移植性时再引入。
