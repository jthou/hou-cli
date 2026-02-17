# 测试历史功能故障排除

## 问题：404 错误

如果遇到以下错误：
- `HTTP error! status: 404`
- `加载测试状态失败`
- `运行测试失败`

### 原因

后端服务没有重启，新的测试历史 API 路由没有被加载。

### 解决方法

1. **重启后端服务**：
   ```bash
   # 停止当前后端服务（如果正在运行）
   # 然后重新启动
   make start
   # 或者
   python cli.py restart
   ```

2. **验证后端路由**：
   ```bash
   # 检查后端是否运行
   curl http://127.0.0.1:8000/api/tests/status
   
   # 应该返回 JSON 响应，而不是 404
   ```

3. **检查后端日志**：
   查看后端日志文件，确认路由是否正确注册：
   ```bash
   tail -f ~/.local/share/hou-cli/logs/backend.log
   ```

## 问题：`loadTestHistory is not a function`

### 原因

浏览器缓存了旧版本的 JavaScript 文件。

### 解决方法

1. **强制刷新浏览器**：
   - Windows/Linux: `Ctrl + Shift + R` 或 `Ctrl + F5`
   - macOS: `Cmd + Shift + R`

2. **清除浏览器缓存**：
   - 打开浏览器开发者工具（F12）
   - 右键点击刷新按钮
   - 选择"清空缓存并硬性重新加载"

3. **检查文件是否正确加载**：
   - 打开浏览器开发者工具（F12）
   - 切换到 Network 标签
   - 刷新页面
   - 检查 `app.js` 文件是否加载成功
   - 查看文件内容，确认包含 `loadTestHistory` 方法

## 验证功能是否正常

1. **检查测试历史 API**：
   ```bash
   curl http://127.0.0.1:8081/api/tests/history
   ```

2. **检查测试状态 API**：
   ```bash
   curl http://127.0.0.1:8081/api/tests/status
   ```

3. **在前端测试审计页面**：
   - 点击"刷新状态"按钮
   - 点击"刷新历史"按钮
   - 应该能看到测试历史记录（如果有的话）

## 数据库位置

测试结果数据库存储在：
- 数据库文件：`~/.local/share/hou-cli/databases/test_results.db` (Linux/macOS)
- 或：`%APPDATA%\hou-cli\databases\test_results.db` (Windows)

## 常见问题

### Q: 为什么看不到测试历史记录？

A: 如果还没有运行过测试，数据库中不会有记录。先运行一次测试，然后刷新历史记录。

### Q: 测试历史记录不更新？

A: 确保：
1. 后端服务正在运行
2. 测试运行成功（检查是否有 `run_id` 返回）
3. 数据库文件有写入权限

### Q: 如何查看数据库内容？

A: 可以使用 SQLite 命令行工具：
```bash
sqlite3 ~/.local/share/hou-cli/databases/test_results.db
.tables
SELECT * FROM test_runs ORDER BY started_at DESC LIMIT 10;
```

