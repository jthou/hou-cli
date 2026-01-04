# 测试运行指南

## 快速测试（Mock 数据）

### 1. 上下文管理器测试
```bash
python tests/test_context_manager_quick.py
```

### 2. 端到端对话测试
```bash
python tests/test_e2e_chat.py
```

### 3. 多轮对话上下文测试
```bash
python tests/test_multi_turn_chat.py
```

### 4. 运行所有测试
```bash
python tests/test_context_manager_quick.py && python tests/test_e2e_chat.py && python tests/test_multi_turn_chat.py
```

---

## 实际端到端测试

### 准备工作

1. **配置环境变量**:
   ```bash
   cp env.example .env
   # 编辑 .env 文件，设置 DEEPSEEK_API_KEY=your_actual_api_key
   ```

2. **启动后端**（终端 1）:
   ```bash
   python -m backend.main
   ```

3. **启动前端测试**（终端 2）:
   ```bash
   # 单次对话
   python -m frontend.main chat "你好"
   
   # 交互式多轮对话
   python -m frontend.main chat
   ```

---

## 多轮对话测试步骤

在交互式模式下（`python -m frontend.main chat`），依次输入：

1. **第一轮**: "你好，我的名字是张三"
2. **第二轮**: "你还记得我的名字吗？"（应该回答"张三"）
3. **第三轮**: "很好，谢谢"（应该理解上下文）

---

**详细文档**: 查看 `TESTING.md` 和 `docs/todo/002-integration-test-guide.md`

