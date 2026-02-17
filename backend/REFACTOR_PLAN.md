# 后端代码结构整理计划

## 当前问题分析

### 1. API 路由层问题
- `routes.py` 文件过大（1019行），包含多个功能模块的路由
- 路由按功能分类不清晰
- 应该按功能模块拆分

### 2. Services 目录问题
- 存在重复目录：
  - `google_search/` 和 `google_search_service/`
  - `mediawiki/` 和 `mediawiki_client_service/`
  - `wikipedia/` 和 `wikipedia_service/`
- 存在空目录或只有 `__pycache__` 的目录：
  - `editor/`
  - `search/`
  - `google_search/`
  - `mediawiki/`
  - `wikipedia/`

### 3. 结构组织问题
- API 路由应该按功能模块组织
- 服务层应该统一命名规范（使用 `_service` 后缀）

## 整理方案

### 阶段 1: API 路由模块化
将 `routes.py` 拆分为：
- `chat_routes.py` - 聊天相关路由（/chat, /chat/stream）
- `session_routes.py` - 会话管理路由（/sessions/*）
- `search_routes.py` - 搜索相关路由（/search/*）
- `mediawiki_routes.py` - MediaWiki 相关路由（/mediawiki/*）
- `tool_routes.py` - 工具相关路由（/tools/*）
- `routes.py` - 保留作为主路由文件，导入所有子路由

### 阶段 2: 清理 Services 目录
- 删除空的或重复的目录
- 统一服务命名规范

### 阶段 3: 统一导入和注册
- 在 `main.py` 中统一注册所有路由
- 确保向后兼容

## 实施步骤

1. 创建新的路由模块文件
2. 将路由代码迁移到对应模块
3. 更新 `routes.py` 导入新模块
4. 清理重复和空目录
5. 测试确保功能正常
