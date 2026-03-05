# Hou CLI 扩展与系统通讯设计

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│  前端 (React) - 运行在 localhost:8081                            │
│  - PdfReader, WebReader, TaskManagement, SettingsNetworkAudit    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ window.postMessage
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Content Script - 注入到 localhost/127.0.0.1 页面                 │
│  - 监听 window message                                          │
│  - 转发到 Background 或直接响应                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ chrome.runtime.connect (Port)
                            │ chrome.runtime.sendMessage
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Background (Service Worker)                                     │
│  - 处理 HOU_CLI_EXPORT_COOKIES, HOU_CLI_FETCH_PDF, HOU_CLI_FETCH │
│  - 访问 chrome.cookies, chrome.tabs, fetch 等                    │
└─────────────────────────────────────────────────────────────────┘
```

## 通讯方式

### 1. 双向通道

- **页面 → Content Script**：`window.postMessage({ type: 'HOU_CLI_XXX', ... }, '*')`
- **Content Script → 页面**：`window.postMessage({ type: 'HOU_CLI_XXX_RESULT', ... }, '*')`
- **Content Script ↔ Background**：`chrome.runtime.connect({ name: 'hou-cli-web-reader' })` 建立 Port 长连接，或 `chrome.runtime.sendMessage` 一次性请求

### 2. 消息类型

| 类型 | 方向 | 用途 |
|------|------|------|
| HOU_CLI_PING | 页→扩展 | 检测扩展是否加载 |
| HOU_CLI_PONG | 扩展→页 | 扩展就绪响应 |
| HOU_CLI_EXPORT_COOKIES | 页→扩展 | 导出指定域名 cookies（视频下载） |
| HOU_CLI_EXPORT_COOKIES_RESULT | 扩展→页 | 返回 Netscape 格式 cookies |
| HOU_CLI_FETCH_PDF | 页→扩展 | 获取在线 PDF（带 cookies） |
| HOU_CLI_FETCH_PDF_RESULT | 扩展→页 | 返回 base64 PDF 数据 |
| HOU_CLI_FETCH | 页→扩展 | 抓取网页内容（DOM/截图） |
| HOU_CLI_FETCH_RESULT | 扩展→页 | 返回 HTML/截图等 |

### 3. Content Script 注入范围

`manifest.json` 中 `content_scripts.matches` 限定为 localhost/127.0.0.1 的若干端口，确保仅在本系统页面注入，避免影响其他站点。

### 4. 扩展能力

- **cookies**：读取指定域名的 cookies（需 host_permissions: `<all_urls>`）
- **tabs**：创建/切换标签页（网页抓取、微信读书截图）
- **scripting**：在标签页内执行脚本（DOM 提取）
- **fetch**：从 Background 发起带 cookies 的请求（PDF 下载）

## 限制

- **后端无法直接检测扩展**：扩展运行在用户浏览器，服务端无法访问。扩展状态检测需在前端通过 PING/PONG 完成。
- **同源要求**：Content Script 仅注入到配置的 localhost 页面，用户需通过本系统 URL 访问。
