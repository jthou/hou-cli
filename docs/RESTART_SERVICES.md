# 重启服务指南

## 问题：404 错误或路由不生效

如果遇到以下问题：
- API 返回 404 Not Found
- 新添加的路由不生效
- 前端无法访问后端 API

## 解决方法

### 1. 重启后端服务

```bash
# 方法1：使用 Makefile（推荐）
make start

# 方法2：使用 CLI
python cli.py restart

# 方法3：手动重启
# 停止当前后端进程
pkill -f "backend/main.py"
# 然后重新启动
python -m backend.main
```

### 2. 重启前端服务

```bash
# 前端开发（Vite 热更新）
cd frontend/react-app && npm run dev

# 或重新构建后由 make start 提供
make build-web && make start
```

### 3. 同时重启前后端

```bash
# 使用 Makefile（推荐）
make start

# 这会：
# 1. 重启后端服务
# 2. 启动 CLI 前端
# 3. 启动 Web 前端
```

## 检查服务状态

### 检查后端服务

```bash
# 检查后端端口
lsof -i :8000

# 测试后端 API
curl http://127.0.0.1:8000/api/health
```

### 检查前端服务

```bash
# 检查前端端口
lsof -i :8081

# 测试前端 API 代理
curl http://127.0.0.1:8081/api/health
```

## 常见问题

### Q: 为什么需要重启服务？

A: 当添加新的路由或修改代码后，需要重启服务才能加载新的代码。Python 是解释型语言，代码修改后需要重新加载。

### Q: 如何确认服务已重启？

A: 
1. 检查进程 ID 是否变化
2. 检查日志时间戳
3. 测试新的 API 端点

### Q: 重启后仍然 404？

A: 
1. 确认代码已保存
2. 检查路由是否正确注册
3. 查看服务日志是否有错误
4. 确认访问的是正确的端口

## 快速重启脚本

可以创建一个快速重启脚本：

```bash
#!/bin/bash
# restart.sh

echo "停止所有服务..."
pkill -f "backend/main.py"
pkill -f "backend.main"

echo "等待服务停止..."
sleep 2

echo "启动后端服务..."
python -m backend.main &
BACKEND_PID=$!

echo "等待后端启动..."
sleep 3

echo "启动前端服务..."
python -m backend.main &
FRONTEND_PID=$!

echo "后端 PID: $BACKEND_PID"
echo "前端 PID: $FRONTEND_PID"
echo "服务已启动"
```
