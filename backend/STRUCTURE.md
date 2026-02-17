# 后端代码结构说明

## 目录结构

```
backend/
├── api/                    # API 路由层
│   ├── chat_routes.py      # 聊天相关路由
│   ├── session_routes.py   # 会话管理路由
│   ├── search_routes.py    # 搜索相关路由
│   ├── mediawiki_routes.py # MediaWiki 相关路由
│   ├── tool_routes.py      # 工具相关路由
│   ├── heartbeat_routes.py # 心跳监控路由
│   ├── storage_routes.py   # 存储配置路由
│   ├── task_routes.py      # 任务相关路由
│   ├── routes.py           # 主路由文件（聚合所有子路由）
│   └── stream_sender.py    # 流式响应工具
│
├── core/                   # 核心业务逻辑
│   ├── agent/              # Agent 相关
│   ├── context/            # 上下文管理
│   └── workflow/           # 工作流
│
├── services/               # 服务层
│   ├── file_search_service/    # 文件搜索服务
│   ├── google_search_service/   # Google 搜索服务
│   ├── mediawiki_client_service/ # MediaWiki 客户端服务
│   ├── wikipedia_service/       # Wikipedia 服务
│   ├── llm/                     # LLM 服务
│   ├── gvim_service/            # GVim 服务
│   └── tools/                   # 工具服务
│
├── infrastructure/         # 基础设施层
│   ├── execution/          # 执行器
│   ├── knowledge/          # 知识库
│   ├── memory/             # 内存管理
│   ├── monitoring/         # 监控
│   └── security/           # 安全
│
├── externals/              # 外部依赖（第三方库）
│   ├── browser-use/
│   ├── ffmpeg/
│   ├── whisper/
│   ├── you-get/
│   └── yt-dlp/
│
└── main.py                 # 后端服务入口

```

## API 路由组织

### 模块化设计
- **chat_routes.py**: 处理聊天请求（/chat, /chat/stream）
- **session_routes.py**: 会话管理（/sessions/*）
- **search_routes.py**: 搜索功能（/search/*）
- **mediawiki_routes.py**: MediaWiki 操作（/mediawiki/*）
- **tool_routes.py**: 工具列表（/tools/*）
- **heartbeat_routes.py**: 心跳监控（/heartbeat/*）
- **storage_routes.py**: 存储配置（/storage/*）
- **task_routes.py**: 任务管理（/tasks/*）

### 主路由文件
`routes.py` 作为主路由文件，负责：
- 导入所有子路由模块
- 统一注册到主路由器
- 提供统一的标签（tags）用于 API 文档

## 服务层组织

所有服务统一使用 `_service` 后缀命名：
- `file_search_service/`
- `google_search_service/`
- `mediawiki_client_service/`
- `wikipedia_service/`
- `llm/` (LLM 服务)
- `gvim_service/`
- `tools/` (工具服务)

## 设计原则

1. **单一职责**: 每个路由文件只负责一个功能模块
2. **模块化**: 按功能拆分，便于维护和扩展
3. **统一命名**: 服务层统一使用 `_service` 后缀
4. **清晰分层**: API -> Core -> Services -> Infrastructure

