# 网络状况审计页面设计

## 一、需纳入审计的外部 URL

### 1. 固定/内置 URL（无需配置即可检测）

| 分类 | URL | 用途 | 检测方式 |
|------|-----|------|----------|
| 网页搜索 | `https://html.duckduckgo.com/html/` | DuckDuckGo 搜索 | POST（轻量） |
| 出口 IP | `https://ip.skk.moe/` | 本机出口 IP | GET |
| 出口 IP | `https://api.ipify.org?format=json` | 本机出口 IP（备选） | GET |
| 出口 IP | `https://ifconfig.me/ip` | 本机出口 IP（备选） | GET |
| 出口 IP | `https://icanhazip.com` | 本机出口 IP（备选） | GET |
| 微信公众号 | `https://api.weixin.qq.com` | 公众号 API（token 等） | GET /cgi-bin/token（需 APPID/SECRET） |
| LaTeX | `https://latex.codecogs.com/png.latex` | 公式渲染（可选） | GET |

### 2. 配置型 URL（从环境变量/配置读取）

| 分类 | 环境变量 | 默认值 | 用途 |
|------|----------|--------|------|
| LLM - DeepSeek | `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | 对话/推理 |
| LLM - 百炼 | `BAILIAN_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 对话/图像 |
| LLM - TheTurbo | `TURBOGATEWAY_BASE_URL` | `https://gateway.theturbo.ai/v1` | 多模型网关 |
| 和风天气 | `QWEATHER_API_HOST` | 无默认 | 天气查询（如 `xxx.re.qweatherapi.com`） |
| MediaWiki | `MEDIAWIKI_URL` | `http://www.jthou.com/mediawiki` | Wiki 读写 |
| Google 搜索 | `GOOGLE_SEARCH_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID` | - | 可选，当前主要用 DuckDuckGo |

### 3. 图像生成专用

| 分类 | 来源 | 说明 |
|------|------|------|
| 百炼图像 API | `BAILIAN_BASE_URL` 或 dashscope 域名 | 图像生成用不同 path：`/api/v1/services/aigc/multimodal-generation/generation` |

### 4. 不纳入审计的 URL

- **用户输入 URL**：视频下载、网文抓取等任务中的 URL 由用户提供，无法预先审计
- **内部 API**：`/api/*` 为本机服务，不属于「外部网络」

---

## 二、功能设计方法

### 方案 A：配置驱动 + 按需检测（推荐）

**思路**：维护一份「审计目标清单」配置，前端按需触发检测，后端并发请求各 URL 并汇总结果。

**配置结构**（`backend/config/network_audit_targets.py` 或 JSON）：

```python
AUDIT_TARGETS = [
    {"id": "duckduckgo", "name": "网页搜索 (DuckDuckGo)", "url": "https://html.duckduckgo.com/html/", "method": "GET", "required": True},
    {"id": "wechat_mp", "name": "微信公众号 API", "url": "https://api.weixin.qq.com", "method": "GET", "required": False, "env_required": ["WECHAT_MP_APP_ID"]},
    {"id": "outbound_ip_1", "name": "出口 IP (ip.skk.moe)", "url": "https://ip.skk.moe/", "method": "GET", "required": True},
    {"id": "deepseek", "name": "DeepSeek API", "url_from_env": "DEEPSEEK_BASE_URL", "default": "https://api.deepseek.com", "method": "GET", "required": False},
    {"id": "bailian", "name": "百炼 API", "url_from_env": "BAILIAN_BASE_URL", "default": "https://dashscope.aliyuncs.com", "method": "GET", "required": False},
    {"id": "qweather", "name": "和风天气", "url_from_env": "QWEATHER_API_HOST", "suffix": "/geo/v2/city/lookup?location=北京", "method": "GET", "required": False},
    {"id": "mediawiki", "name": "MediaWiki", "url_from_env": "MEDIAWIKI_URL", "default": "http://www.jthou.com/mediawiki", "path": "/api.php", "method": "GET", "required": False},
]
```

**检测逻辑**：

1. 解析配置，`url_from_env` 的从环境变量取，缺省用 `default`
2. 若 `env_required` 未配置，标记为「未配置」跳过检测
3. 使用 `requests.get(url, timeout=5)` 或 `HEAD`，捕获状态码、耗时、异常（含 SSL）
4. 返回 `{ id, name, status: "ok"|"fail"|"skip", latency_ms, error? }`

### 方案 B：从现有调用点自动发现

**思路**：通过静态分析或运行时埋点，收集实际发起过的外部请求，再对这批 URL 做审计。

- **优点**：与真实调用一致
- **缺点**：实现复杂，需改 httpx/requests 封装或中间件

**适用**：作为后续增强，首版建议用方案 A。

### 方案 C：健康检查聚合

**思路**：复用现有 `/api/heartbeat/status` 等健康检查，扩展为「外部依赖健康」子项。

- 在 heartbeat 中增加对 DuckDuckGo、出口 IP 等的快速探测
- 审计页面调用 heartbeat 或独立 `/api/network/audit` 展示

---

## 三、推荐实现步骤

### 1. 后端 API

- **`GET /api/network/audit/targets`**：返回审计目标列表（含是否已配置、当前 URL）
- **`POST /api/network/audit/run`**：触发一次检测，返回各目标结果

### 2. 检测实现

- 使用 `requests`（避免 httpx SSL EOF）
- 超时 5–8 秒
- 并发检测（`asyncio.gather` 或 `concurrent.futures`）
- 对微信公众号：可只检测 `api.weixin.qq.com` 连通性，不必须带 token

### 3. 前端页面

- 路由：`/settings/network-audit` 或 `/network-audit`
- 展示：表格（名称、URL、状态、耗时、错误信息）
- 操作：「立即检测」按钮
- 可选：定时检测、历史记录（若需持久化）

### 4. 数据存储（可选）

- 检测结果可仅存内存/会话，不落库
- 若需历史：写入 SQLite 或 JSON，表结构如 `(id, target_id, status, latency_ms, error, created_at)`

---

## 四、审计目标清单（可直接实现）

| id | name | url / 来源 | 备注 |
|----|------|------------|------|
| duckduckgo | 网页搜索 | https://html.duckduckgo.com/html/ | 固定 |
| outbound_ip | 出口 IP | ip.skk.moe, api.ipify.org 等 | 多源任一连通即可 |
| wechat_mp | 微信公众号 | https://api.weixin.qq.com | 需 APPID/SECRET |
| deepseek | DeepSeek | DEEPSEEK_BASE_URL | 配置型 |
| bailian | 百炼 | BAILIAN_BASE_URL | 配置型 |
| turbogateway | TheTurbo 网关 | TURBOGATEWAY_BASE_URL | 配置型 |
| qweather | 和风天气 | QWEATHER_API_HOST | 配置型 |
| mediawiki | MediaWiki | MEDIAWIKI_URL | 配置型 |
| codecogs | LaTeX 渲染 | https://latex.codecogs.com | 固定，可选 |

---

## 五、与现有模块的关系

- **WechatOutboundIpHint**：已调用出口 IP 接口，可复用逻辑
- **browser_search**：已用 requests 请求 DuckDuckGo，审计可复用同一 URL
- **model_config**：LLM base_url 可从 `get_model_config_manager().get_base_url()` 等获取
