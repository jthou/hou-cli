# API 路由单元测试

## 测试结构

所有 API 路由都有对应的单元测试文件：

- `test_chat_routes.py` - 聊天路由测试
- `test_session_routes.py` - 会话管理路由测试
- `test_search_routes.py` - 搜索路由测试
- `test_mediawiki_routes.py` - MediaWiki 路由测试
- `test_tool_routes.py` - 工具路由测试
- `test_heartbeat_routes.py` - 心跳监控路由测试
- `test_storage_routes.py` - 存储配置路由测试
- `test_task_api.py` - 任务管理路由测试（已存在）
- `test_routes.py` - 旧版路由测试（已存在，可逐步迁移）
- `test_stream_api_planning_integration.py` - 流式 API 集成测试（已存在）

## 运行测试

### 运行所有测试
```bash
pytest backend/api/tests/
```

### 运行特定测试文件
```bash
pytest backend/api/tests/test_chat_routes.py
```

### 运行特定测试类
```bash
pytest backend/api/tests/test_chat_routes.py::TestChatRoutes
```

### 运行特定测试方法
```bash
pytest backend/api/tests/test_chat_routes.py::TestChatRoutes::test_chat_endpoint_success
```

### 生成覆盖率报告
```bash
pytest backend/api/tests/ --cov=backend.api --cov-report=html
```

## 测试覆盖的 API 端点

### Chat Routes (`/api/chat`)
- ✅ POST `/api/chat` - 非流式聊天
- ✅ POST `/api/chat/stream` - 流式聊天
- ✅ 错误处理测试
- ✅ 会话 ID 支持测试

### Session Routes (`/api/sessions`)
- ✅ GET `/api/sessions/list` - 列出会话
- ✅ GET `/api/sessions/{session_id}` - 获取会话详情
- ✅ GET `/api/sessions/search` - 搜索会话
- ✅ POST `/api/sessions` - 创建会话
- ✅ DELETE `/api/sessions/{session_id}` - 删除会话
- ✅ POST `/api/sessions/{session_id}/clear` - 清除会话消息
- ✅ POST `/api/sessions/{session_id}/summary` - 生成会话摘要

### Search Routes (`/api/search`)
- ✅ GET `/api/search/files` - 文件搜索
- ✅ GET `/api/search/availability` - 检查搜索可用性
- ✅ GET `/api/search/unified` - 统一搜索
- ✅ 参数验证测试

### MediaWiki Routes (`/api/mediawiki`)
- ✅ GET `/api/mediawiki/search` - 搜索页面
- ✅ GET `/api/mediawiki/pages/{title}` - 获取页面
- ✅ POST `/api/mediawiki/pages/{title}` - 编辑页面
- ✅ POST `/api/mediawiki/sync` - 触发同步
- ✅ GET `/api/mediawiki/sync/status` - 获取同步状态

### Tool Routes (`/api/tools`)
- ✅ GET `/api/tools/list` - 获取工具列表

### Heartbeat Routes (`/api/heartbeat`)
- ✅ GET `/api/heartbeat/status` - 获取心跳状态

### Storage Routes (`/api/storage`)
- ✅ GET `/api/storage/config` - 获取存储配置

### Task Routes (`/api/tasks`)
- ✅ GET `/api/tasks/{task_id}` - 获取任务详情
- ✅ GET `/api/tasks` - 列出任务
- ✅ POST `/api/tasks/{task_id}/cancel` - 取消任务

## 测试 Fixtures

`conftest.py` 提供了以下 fixtures：

- `app` - FastAPI 应用实例
- `client` - TestClient 实例
- `mock_orchestrator` - 模拟的 Orchestrator
- `mock_context_manager` - 模拟的 ContextManager
- `mock_search_service` - 模拟的 FileSearchService
- `mock_mediawiki_client` - 模拟的 MediaWikiClientService
- `mock_storage_manager` - 模拟的 StorageManager
- `mock_heartbeat_monitor` - 模拟的 HeartbeatMonitor

## 测试最佳实践

1. **使用 Mock**：所有外部依赖都使用 Mock，避免实际调用
2. **测试边界情况**：包括成功、失败、边界值等
3. **参数验证**：测试无效参数的处理
4. **错误处理**：确保错误情况被正确处理
5. **状态码验证**：验证正确的 HTTP 状态码
6. **响应格式验证**：验证响应 JSON 结构

