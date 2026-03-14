# 写作助手「写入 MediaWiki」后回跳到网页阅读 - 根因分析

**分析时间**：2025-03-13  
**现象**：用户反馈「从写作助手里，完成 写入 MediaWiki 操作之后，回跳到 网页阅读」

---

## 一、代码排查结论

### 1. 「写入 MediaWiki」流程本身不触发任何跳转

`MarkdownActionButtons.jsx` 中，写入 MediaWiki 成功后的逻辑为：

```javascript
// 第 135-139 行
if (res.ok && data.success) {
  toast?.info?.('任务已创建，可在任务管理中查看执行状态')
  setMwDialogOpen(false)
  setMwTitle('')
  setMwSummary('')
  setMwMode('create')
}
```

**无任何 `navigate()` 调用**，仅关闭弹窗并重置表单。

### 2. 唯一会触发「回跳」的代码：AddReference 的 `navigate(-1)`

全项目搜索 `navigate(-1)`，仅在 `AddReference.jsx` 中出现：

- 第 89 行：`handleSelect` 选择已有会话并添加后
- 第 115 行：`handleNewAndAdd` 新建会话并添加后

```javascript
toast?.info?.(`已添加到${cfg.label}会话`)
navigate(-1)  // 返回上一页
```

### 3. `navigate(-1)` 会回到哪里？

`navigate(-1)` 是浏览器历史后退，回到**上一页**。

| 用户操作路径 | 历史栈 | `navigate(-1)` 后 |
|-------------|--------|-------------------|
| 网页阅读 → 添加到参考 | [web-reader, add-reference] | 网页阅读 |
| 写作助手 → 添加到参考 | [article-writing, add-reference] | 写作助手 |
| 网页阅读 → 写作助手 → 添加到参考 | [web-reader, article-writing, add-reference] | 写作助手 |

---

## 二、根因推断

**结论：出现「回跳到网页阅读」时，一定是用户执行了「添加到参考」，而不是「写入 MediaWiki」。**

原因：

1. **写入 MediaWiki**：只创建任务、关闭弹窗，**不调用 `navigate()`**。
2. **添加到参考**：会跳转到 `/add-reference`，完成后 `navigate(-1)` 回到上一页。

若上一页是**网页阅读**，则完成「添加到参考」后就会回到网页阅读。

### 可能的用户操作路径

1. 用户在**网页阅读**页面。
2. 点击了「**添加到参考**」按钮（与「写入 MediaWiki」相邻）。
3. 进入 AddReference 页面，选择会话并完成添加。
4. `navigate(-1)` 执行，回到网页阅读。

用户可能误以为点击的是「写入 MediaWiki」，或对两个按钮的功能记忆有偏差。

---

## 三、按钮布局（易混淆点）

`MarkdownActionButtons.jsx` 中按钮顺序为：

```
复制 Markdown | 写回输入框(或发送到写作助手) | 写入 MediaWiki | 添加到参考
```

- 「写入 MediaWiki」：主色按钮（`bg-accent`）
- 「添加到参考」：边框按钮（`border border-border`）

两者相邻，容易误点。

---

## 四、建议

### 1. 若用户确实希望「写入 MediaWiki」后不跳转

当前实现已满足：写入 MediaWiki 后不会跳转，无需改动。

### 2. 若希望减少「添加到参考」与「写入 MediaWiki」的混淆

- 调整按钮顺序或样式，使两者更易区分。
- 或在「添加到参考」完成时，根据来源页（`location.state.from`）显式跳回目标页，而不是依赖 `navigate(-1)`，避免历史栈异常导致意外回到网页阅读。

### 3. 若用户仍坚持是「写入 MediaWiki」导致跳转

建议：

- 确认是否使用最新前端构建（`make build-web` 后强制刷新）。
- 复现时录屏，确认实际点击的是哪个按钮。
