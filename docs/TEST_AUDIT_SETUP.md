# 测试审计功能设置说明

## 问题排查

如果遇到 404 错误，请按以下步骤检查：

### 1. 确认后端服务已重启

测试路由是在 `backend/api/test_routes.py` 中定义的，需要重启后端服务才能加载：

```bash
# 停止现有后端服务
# 然后重新启动
make start
# 或
python cli.py restart
```

### 2. 验证路由注册

确认 `backend/api/routes.py` 中已包含测试路由：

```python
from backend.api.test_routes import router as test_router
router.include_router(test_router, tags=["tests"])
```

### 3. 验证 API 端点

测试后端 API 是否可用：

```bash
# 检查测试状态
curl http://127.0.0.1:8000/api/tests/status

# 列出测试文件
curl http://127.0.0.1:8000/api/tests/list
```

### 4. 检查前端代理

确认 `backend` 已注册测试相关 API 路由：

- `POST /api/tests/run`
- `GET /api/tests/status`
- `GET /api/tests/list`

## 功能说明

### 后端 API

- **POST /api/tests/run** - 运行测试
  - 请求体：`{"test_path": null, "verbose": false, "coverage": false}`
  - 返回：测试结果详情

- **GET /api/tests/status** - 获取测试状态
  - 返回：测试统计信息（总数、通过、失败等）

- **GET /api/tests/list** - 列出测试文件
  - 返回：所有测试文件列表

### 前端功能

在设置页面的"测试审计"部分：

1. **测试状态栏** - 显示测试统计
2. **运行所有测试** - 执行完整测试套件
3. **刷新状态** - 更新测试状态
4. **测试结果列表** - 显示每个测试的状态
5. **测试输出** - 显示详细输出

## 常见问题

### Q: 404 错误
A: 后端服务需要重启以加载新路由

### Q: 测试运行超时
A: 测试默认超时时间为 5 分钟，可以在 `test_routes.py` 中调整

### Q: 测试结果不显示
A: 检查浏览器控制台是否有错误，确认后端服务正常运行
