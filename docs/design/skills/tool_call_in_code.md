# 代码步骤中调用工具的两种方案对比

## 方案1：使用 tool 类型步骤 + loop 支持

### 优点
- ✅ **架构清晰**：符合现有设计，工具调用统一管理
- ✅ **类型安全**：参数验证和错误处理统一
- ✅ **易于调试**：每个工具调用都有明确的步骤记录
- ✅ **无需修改核心逻辑**：只需要添加 loop 类型步骤支持

### 缺点
- ❌ **需要实现 loop 类型步骤**：当前 SkillExecutor 不支持循环
- ❌ **配置可能冗长**：对于大量 URL，需要配置多个步骤
- ❌ **灵活性有限**：复杂逻辑（如条件重试）需要多个步骤组合

### 实现复杂度
- **中等**：需要添加 loop 类型步骤支持，但逻辑清晰

### 示例配置
```yaml
steps:
  - name: download_videos
    type: loop
    items: ${config.urls}
    item_var: url
    steps:
      - name: download_single
        type: tool
        tool: video_downloader
        inputs:
          url: ${url}
          cookies_from_browser: ${config.cookies_from_browser}
      - name: retry_with_cookies
        type: conditional
        condition: ${result.success == false and 'bilibili.com' in url}
        steps:
          - name: retry_download
            type: tool
            tool: video_downloader
            inputs:
              url: ${url}
              cookies_from_browser: chrome
```

---

## 方案2：代码步骤中直接调用工具

### 优点
- ✅ **灵活性高**：可以在代码中实现任意复杂逻辑
- ✅ **适合批量处理**：循环、条件判断都在代码中
- ✅ **代码集中**：所有逻辑在一个地方，易于维护

### 缺点
- ❌ **实现复杂**：需要在 subprocess 中传递工具调用请求
- ❌ **需要双向通信**：代码执行器需要支持工具调用和结果返回
- ❌ **调试困难**：工具调用隐藏在代码中，不易追踪
- ❌ **类型安全差**：参数验证在运行时进行

### 实现复杂度
- **高**：需要修改代码执行器，实现工具调用代理机制

### 示例代码
```python
# 在代码中调用工具
for url in config['urls']:
    result = call_tool('video_downloader', url=url)
    if not result.success and 'bilibili.com' in url:
        # 重试
        result = call_tool('video_downloader', url=url, cookies_from_browser='chrome')
```

---

## 推荐方案

**推荐使用方案1（tool 类型步骤 + loop 支持）**，原因：

1. **架构清晰**：符合现有设计模式，工具调用统一管理
2. **易于维护**：每个步骤都有明确的定义和错误处理
3. **实现简单**：只需要添加 loop 类型步骤支持
4. **可扩展性好**：未来可以添加 conditional、parallel 等步骤类型

### 实现步骤

1. **添加 loop 类型步骤支持**
   - 在 `SkillExecutor` 中添加 `_execute_loop_step` 方法
   - 支持 `items`、`item_var`、`steps` 配置

2. **添加 conditional 类型步骤支持**（可选）
   - 支持条件判断，用于实现重试逻辑

3. **更新 video_downloader skill.yaml**
   - 使用 loop 步骤批量下载
   - 使用 conditional 步骤实现重试逻辑

---

## 临时方案

在实现 loop 支持之前，可以使用**混合方案**：

- 使用 `code_executor` 步骤准备下载任务列表
- 使用多个 `tool` 步骤（通过代码生成）来下载每个视频
- 或者：在 orchestrator 层面处理批量下载，而不是在 skill 层面






