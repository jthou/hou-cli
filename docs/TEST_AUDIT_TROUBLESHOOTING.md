# 测试审计功能故障排查

## 问题：404 错误

如果前端访问测试 API 时出现 404 错误，说明后端服务没有加载新的测试路由。

### 解决方案

**需要重启后端服务以加载新的测试路由**

```bash
# 方法 1: 使用 Makefile
make restart

# 方法 2: 使用 CLI
python cli.py restart

# 方法 3: 手动重启
# 1. 停止现有后端服务
# 2. 重新启动
python -m backend.main
```

### 验证路由是否加载

重启后，可以通过以下方式验证：

```bash
# 检查测试状态 API
curl http://127.0.0.1:8000/api/tests/status

# 应该返回 JSON 响应，而不是 404
```

### 检查路由注册

确认以下文件中的路由已正确注册：

1. **backend/api/routes.py** - 应该包含：
   ```python
   from backend.api.test_routes import router as test_router
   router.include_router(test_router, tags=["tests"])
   ```

2. **backend/main.py** - 应该包含：
   ```python
   from backend.api.routes import router
   app.include_router(router, prefix="/api")
   ```

3. **frontend/web/main.py** - 应该包含测试 API 的代理路由

### 常见错误

1. **ModuleNotFoundError**: 确保虚拟环境已激活，所有依赖已安装
2. **404 Not Found**: 后端服务需要重启
3. **500 Internal Server Error**: 检查后端日志，可能是测试运行失败

### 测试 API 端点

- `POST /api/tests/run` - 运行测试
- `GET /api/tests/status` - 获取测试状态
- `GET /api/tests/list` - 列出测试文件

所有端点都需要通过 `/api` 前缀访问。

