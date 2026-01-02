# 快速开始指南

## 项目已设置完成 ✅

所有依赖已安装，项目结构已创建，可以开始使用了！

## 启动项目

### 方式 1：使用 Makefile（推荐）

```bash
# 激活虚拟环境
source venv/bin/activate

# 终端 1：启动后端
make run-backend

# 终端 2：启动前端
make run-frontend
```

### 方式 2：直接运行

```bash
# 激活虚拟环境
source venv/bin/activate

# 终端 1：启动后端
python -m backend.main

# 终端 2：启动前端
python -m frontend.main chat
```

### 方式 3：使用脚本

```bash
# 终端 1
./scripts/start_backend.sh

# 终端 2
./scripts/start_frontend.sh
```

### 方式 4：统一启动（生产模式）

```bash
source venv/bin/activate
python cli.py
```

## 首次使用

1. **启动后端服务**（必须首先启动）：
   ```bash
   python -m backend.main
   ```
   你会看到类似输出：
   ```
   后端服务启动在 http://127.0.0.1:63415
   ```

2. **启动前端 CLI**（新终端）：
   ```bash
   python -m frontend.main chat
   ```

3. **开始对话**：
   ```
   你: 你好
   Agent: 处理任务: 你好
   ```

## 配置 LLM（可选）

如果需要使用 LLM 功能，创建 `.env` 文件：

```bash
DEEPSEEK_API_KEY=your_api_key_here
```

## 运行测试

```bash
source venv/bin/activate
pytest tests/ -v
```

## 项目状态

- ✅ 虚拟环境已创建
- ✅ 所有依赖已安装
- ✅ 后端服务可正常启动
- ✅ 前端 CLI 可正常启动
- ✅ 基础测试通过
- ⚠️ 部分功能待实现（标记为 TODO）

## 下一步开发

1. **实现 Agent 功能**：完善各个 Agent 的具体实现
2. **实现 SOP 流程**：完成工作流引擎
3. **实现知识库**：完成向量存储和搜索
4. **实现代码执行**：完成安全执行机制
5. **完善 UI**：增强 Rich UI 交互体验

## 常见问题

### Q: 前端提示"无法连接到后端服务"
A: 确保后端服务已启动，检查端口文件是否存在

### Q: 如何查看后端日志？
A: 后端日志会直接输出到终端

### Q: 如何修改端口？
A: 后端会自动查找可用端口，端口号保存在应用数据目录的 `port.txt` 文件中

## 获取帮助

- 查看架构设计：`docs/design/architecture-design.md`
- 查看快速参考：`docs/design/quick-reference.md`
- 查看设置指南：`docs/design/setup-guide.md`

