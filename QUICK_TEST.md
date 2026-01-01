# 快速测试指南

## 运行测试脚本

### 方法 1: 逐个运行

```bash
# 1. 上下文管理器测试
python tests/test_context_manager_quick.py

# 2. 端到端对话测试
python tests/test_e2e_chat.py

# 3. 多轮对话测试
python tests/test_multi_turn_chat.py
```

### 方法 2: 使用 shell 脚本

```bash
chmod +x tests/test_all.sh
./tests/test_all.sh
```

### 方法 3: 一行命令

```bash
python tests/test_context_manager_quick.py && python tests/test_e2e_chat.py && python tests/test_multi_turn_chat.py
```

---

## 实际端到端测试

### 步骤 1: 配置环境

```bash
cp env.example .env
# 编辑 .env，设置 DEEPSEEK_API_KEY
```

### 步骤 2: 启动后端

```bash
python -m backend.main
```

### 步骤 3: 启动前端测试

```bash
# 单次对话
python -m frontend.main chat "你好"

# 交互式多轮对话
python -m frontend.main chat
```

---

## 多轮对话测试

在交互式模式下测试上下文：

1. 输入: "我的名字是张三"
2. 输入: "你还记得我的名字吗？"
3. 验证: Agent 应该回答"张三"

---

**详细文档**: `TESTING.md`

