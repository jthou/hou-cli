# 测试指南

## 测试架构说明

### 前后端关系

1. **后端服务**：独立的HTTP服务，运行在端口6080（可配置）
   - 提供REST API和SSE流式API
   - 处理任务执行、工具调用等

2. **前端客户端**：通过HTTP请求与后端通信
   - 使用IPCClient发送请求
   - 接收SSE流式响应
   - 使用StreamRenderer渲染输出

### 测试方法

**❌ 错误方式**：
- 直接运行 `python -m frontend.main chat` - 会进入交互模式，可能卡死
- 在测试脚本中调用交互式函数 - 会阻塞

**✅ 正确方式**：
1. **直接测试后端API**：使用httpx直接调用后端API
2. **测试前端组件**：单独测试StreamRenderer等组件
3. **集成测试**：使用非交互式方式测试完整流程

## 测试脚本

### 1. 后端API测试

**文件**: `scripts/test_backend_api.py`

**功能**：
- 测试后端健康检查
- 测试流式聊天API
- 测试状态更新（心跳）机制

**使用方法**：
```bash
# 确保后端正在运行
export BACKEND_PORT=6080
python scripts/test_backend_api.py
```

### 2. 简单功能测试

**文件**: `scripts/test_simple.py`

**功能**：
- 检查环境配置
- 验证前端代码导入
- 测试后端连接

**使用方法**：
```bash
python scripts/test_simple.py
```

### 3. 状态行更新测试

**文件**: `scripts/test_status_line_update.py`

**功能**：
- 测试状态行同一行更新功能
- 验证前端显示逻辑

**使用方法**：
```bash
# 需要后端运行
export BACKEND_PORT=6080
python scripts/test_status_line_update.py
```

## 测试流程

### 步骤1: 启动后端

```bash
cd /System/Volumes/Data/justin/dev/hou-cli
source venv/bin/activate
export BACKEND_PORT=6080
export ENABLE_AUTONOMOUS_EXECUTION=true
export STREAM_TIMEOUT=600
python -m backend.main
```

### 步骤2: 运行测试

在另一个终端：

```bash
cd /System/Volumes/Data/justin/dev/hou-cli
source venv/bin/activate
export BACKEND_PORT=6080

# 运行简单测试
python scripts/test_simple.py

# 运行API测试
python scripts/test_backend_api.py
```

### 步骤3: 手动测试（可选）

如果需要手动测试前端：

```bash
# 在交互式终端中运行
python -m frontend.main chat "你的任务"
```

## 验证要点

### 1. 后端连接
- ✅ 后端服务正常运行
- ✅ 健康检查通过
- ✅ 端口配置正确

### 2. 流式响应
- ✅ 可以接收流式数据
- ✅ 内容正确显示
- ✅ 状态更新正常

### 3. 状态行更新
- ✅ 状态信息在同一行更新
- ✅ 不产生重复的状态行
- ✅ 有内容输出时自动换行

## 故障排查

### 后端连接失败

**症状**: `无法连接到后端服务`

**解决**:
1. 检查后端是否运行: `ps aux | grep backend.main`
2. 检查端口: `lsof -i:6080`
3. 检查环境变量: `echo $BACKEND_PORT`
4. 重启后端服务

### 测试脚本卡死

**症状**: 测试脚本执行后无响应

**原因**:
- 可能调用了交互式函数
- 可能等待用户输入
- 可能后端响应超时

**解决**:
- 使用 `test_backend_api.py` 直接测试API
- 设置合理的超时时间
- 检查后端日志

### 状态更新不显示

**症状**: 未看到状态行更新

**检查**:
1. 后端是否发送状态更新（查看后端日志）
2. 前端是否正确解析状态消息
3. Live组件是否正常工作

## 注意事项

1. **不要在前端测试脚本中调用交互式函数**
2. **使用异步客户端（httpx）直接测试后端API**
3. **设置合理的超时时间，避免无限等待**
4. **测试脚本应该是独立的，不依赖交互式终端**

