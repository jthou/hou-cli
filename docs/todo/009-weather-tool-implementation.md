
# TODO-009: 天气预报工具实现

## 概述

实现天气预报工具，支持通过和风天气 API 获取天气信息，使用 JWT 进行安全认证。

## 前置条件

### 需要确认的信息
- [ ] JWT Payload 的具体结构（iss, aud, sub 等字段的值）
- [ ] 私钥格式（RSA/其他）和是否需要公钥
- [ ] 城市 ID 的获取方式（是否需要实现城市搜索）

### 环境准备
- [ ] 生成 RSA 私钥对（如果还没有）
- [ ] 将私钥添加到 `.env` 文件中的 `WEATHER_JWT_PRIVATE_KEY` 变量
- [ ] 确保 `.env` 文件已添加到 `.gitignore`（如果还没有）

**注意：** 和风天气 API 不需要 API Key，仅使用 JWT 认证。

## 阶段 1: 基础架构实现（P0）

### 任务 1.1: 实现 Tool 基类
- [ ] 创建 `backend/core/agent/tools/base.py`
- [ ] 定义 `Tool` 基类（抽象类）
- [ ] 定义 `ToolResult` 数据类
- [ ] 定义 `ToolParameter` 数据类
- [ ] 实现工具参数验证逻辑
- [ ] 编写单元测试

**验收标准：**
- Tool 基类可以被子类继承
- ToolResult 包含 success, data, error 字段
- 参数验证逻辑正确

### 任务 1.2: 实现 Tool 注册器
- [ ] 创建 `backend/core/agent/tools/registry.py`
- [ ] 实现 `ToolRegistry` 类
- [ ] 实现工具注册功能 `register()`
- [ ] 实现工具查找功能 `get_tool()`
- [ ] 实现工具列表功能 `list_tools()`
- [ ] 实现 LLM 格式工具定义生成 `get_tools_for_llm()`
- [ ] 实现工具执行功能 `execute()`
- [ ] 编写单元测试

**验收标准：**
- 可以注册和查找工具
- LLM 格式的工具定义符合 OpenAI Function Calling 规范
- 工具执行时参数验证正确

### 任务 1.3: 实现私钥加载工具
- [ ] 创建 `backend/core/agent/tools/utils/` 目录
- [ ] 创建 `backend/core/agent/tools/utils/key_loader.py`
- [ ] 实现 `KeyLoader` 类
- [ ] 实现 `load_private_key()` 方法
- [ ] 实现 `validate_key_permissions()` 方法
- [ ] 实现错误处理（文件不存在、权限错误等）
- [ ] 编写单元测试

**验收标准：**
- 可以正确加载私钥文件
- 权限验证逻辑正确（文件权限应为 600）
- 错误处理完善

## 阶段 2: JWT 认证实现（P0）

### 任务 2.1: 安装依赖
- [ ] 在 `requirements.txt` 或 `pyproject.toml` 中添加依赖
  - `PyJWT[crypto]>=2.8.0` - JWT 库
  - `cryptography>=41.0.0` - 加密库（用于 RSA）
- [ ] 运行 `pip install -r requirements.txt`

### 任务 2.2: 实现 JWT 认证类
- [ ] 创建 `backend/core/agent/tools/auth/` 目录
- [ ] 创建 `backend/core/agent/tools/auth/__init__.py`
- [ ] 创建 `backend/core/agent/tools/auth/jwt_auth.py`
- [ ] 实现 `JWTAuth` 类
- [ ] 实现 `__init__()` 方法（加载私钥）
- [ ] 实现 `generate_token()` 方法（生成 JWT）
- [ ] 实现 `_build_payload()` 方法（构建 JWT payload）
- [ ] 实现错误处理
- [ ] 编写单元测试

**验收标准：**
- 可以正确生成 JWT token
- JWT payload 包含必要的字段（iss, iat, exp, aud, sub）
- JWT 使用 RS256 算法签名
- 错误处理完善

### 任务 2.3: 配置管理
- [ ] 在 `.env.example` 中添加配置项
  - `WEATHER_JWT_PRIVATE_KEY_PATH`
  - `QWEATHER_API_BASE_URL`
  - `QWEATHER_API_KEY`
  - `WEATHER_JWT_EXPIRES_IN`
- [ ] 实现配置加载逻辑（从环境变量读取）
- [ ] 实现默认值处理

**验收标准：**
- 配置可以从环境变量正确加载
- 默认值设置合理

## 阶段 3: 天气工具实现（P0）

### 任务 3.1: 实现天气工具类
- [ ] 创建 `backend/core/agent/tools/builtin/weather_tool.py`
- [ ] 实现 `WeatherTool` 类
- [ ] 实现 `__init__()` 方法（初始化 JWT 认证和 API 配置）
- [ ] 实现 `get_current_weather()` 方法（获取实时天气）
- [ ] 实现 `get_forecast()` 方法（获取天气预报）
- [ ] 实现 `get_warning()` 方法（获取天气预警）
- [ ] 实现 `_make_request()` 方法（发送 API 请求，带 JWT 认证）
- [ ] 实现 `_resolve_location()` 方法（解析城市名称或 ID）
- [ ] 实现错误处理和重试逻辑
- [ ] 编写单元测试

**验收标准：**
- 可以正确调用和风天气 API
- JWT 认证正确添加到请求头
- 响应数据解析正确
- 错误处理和重试逻辑完善

### 任务 3.2: 实现 Tool 装饰器
- [ ] 在 `weather_tool.py` 中使用 Tool 装饰器定义工具
- [ ] 定义 `get_weather` 工具函数
- [ ] 定义工具参数（location, days）
- [ ] 定义工具描述
- [ ] 实现工具函数逻辑（调用 WeatherTool）

**验收标准：**
- 工具函数符合 Tool 基类接口
- 参数定义清晰
- 返回值符合 ToolResult 格式

### 任务 3.3: 集成测试
- [ ] 创建 `backend/core/agent/tools/tests/test_weather_tool.py`
- [ ] 编写集成测试（需要真实的 API Key 和私钥）
- [ ] 测试实时天气查询
- [ ] 测试天气预报查询
- [ ] 测试天气预警查询
- [ ] 测试错误场景（城市不存在、API 错误等）

**验收标准：**
- 所有测试用例通过
- 错误场景处理正确

## 阶段 4: 工具注册和集成（P0）

### 任务 4.1: 注册天气工具
- [ ] 在 `backend/core/agent/tools/builtin/__init__.py` 中导出天气工具
- [ ] 在 `backend/core/agent/tools/__init__.py` 中注册天气工具
- [ ] 确保工具可以被 ToolRegistry 发现

**验收标准：**
- 工具可以正确注册
- 工具可以在 ToolRegistry 中查找

### 任务 4.2: 在 Orchestrator 中集成工具
- [ ] 修改 `backend/core/agent/orchestrator.py`
- [ ] 在 Orchestrator 中初始化 ToolRegistry
- [ ] 在 LLM 调用时传递工具定义
- [ ] 处理 LLM 返回的工具调用请求
- [ ] 执行工具并返回结果

**验收标准：**
- Orchestrator 可以使用工具
- LLM 可以调用天气工具
- 工具执行结果正确返回给 LLM

## 阶段 5: 文档和示例（P1）

### 任务 5.1: 使用文档
- [ ] 在 `backend/core/agent/tools/README.md` 中添加天气工具使用说明
- [ ] 添加配置说明
- [ ] 添加使用示例
- [ ] 添加常见问题解答

### 任务 5.2: 使用示例
- [ ] 创建 `backend/core/agent/tools/examples/weather_example.py`
- [ ] 实现完整的使用示例
- [ ] 包含配置、初始化、调用等步骤

## 阶段 6: 优化和扩展（P2）

### 任务 6.1: 性能优化
- [ ] 实现请求缓存（相同城市短时间内不重复请求）
- [ ] 实现异步请求支持
- [ ] 实现连接池

### 任务 6.2: 功能扩展
- [ ] 支持更多天气数据（空气质量、生活指数等）
- [ ] 支持批量查询多个城市
- [ ] 支持天气数据历史记录

## 测试清单

### 单元测试
- [ ] Tool 基类测试
- [ ] ToolRegistry 测试
- [ ] KeyLoader 测试
- [ ] JWTAuth 测试
- [ ] WeatherTool 测试

### 集成测试
- [ ] 端到端天气查询流程
- [ ] JWT 认证流程
- [ ] 错误处理流程

### 手动测试
- [ ] 使用真实 API Key 和私钥测试
- [ ] 测试不同城市的天气查询
- [ ] 测试错误场景（城市不存在、网络错误等）

## 验收标准

1. **功能完整性**
   - 可以获取实时天气、天气预报、天气预警
   - JWT 认证正确工作
   - 错误处理完善

2. **代码质量**
   - 代码符合项目规范
   - 有完整的类型注解
   - 有完整的文档字符串
   - 测试覆盖率 > 80%

3. **安全性**
   - 私钥文件权限正确
   - JWT 生成安全
   - 不在日志中暴露敏感信息

4. **可用性**
   - 配置简单
   - 错误提示友好
   - 文档完整

## 依赖关系

```
阶段 1 (基础架构)
  ↓
阶段 2 (JWT 认证)
  ↓
阶段 3 (天气工具)
  ↓
阶段 4 (工具注册和集成)
  ↓
阶段 5 (文档和示例)
  ↓
阶段 6 (优化和扩展)
```

## 预计工作量

- 阶段 1: 2-3 天
- 阶段 2: 1-2 天
- 阶段 3: 2-3 天
- 阶段 4: 1-2 天
- 阶段 5: 1 天
- 阶段 6: 2-3 天（可选）

**总计：** 7-11 天（不含阶段 6）
