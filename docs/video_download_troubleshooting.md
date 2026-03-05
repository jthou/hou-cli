# 视频下载失败排查报告

## 0. YouTube 最新情况（yt-dlp 官方文档）

YouTube 正在逐步要求 **PO Token**（Proof of Origin）才能下载。若默认客户端失败，可尝试：

1. **player_client=default,tv**：`tv` 客户端当前不需要 PO Token，已自动加入备选
2. **format_sort 替代 format**：严格 format 在部分视频会报 "Requested format is not available"，已改用 `format_sort`（如 `res:1080`）支持回退
3. **Cookies**：仍建议提供 cookies（`cookies_from_browser='chrome'` 或扩展导出）
4. **PO Token 插件**：若仍失败，可安装 [bgutil-ytdlp-pot-provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider) 等 PO Token 提供插件

参考：[yt-dlp PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)、[Extractors#YouTube](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#youtube)

## 1. 诊断脚本

运行以下命令查看系统中失败的视频下载任务及错误原因：

```bash
python scripts/diagnose_video_download.py
```

输出包括：
- 失败的视频下载任务列表（URL、错误信息、创建时间）
- 最近 20 个视频下载任务状态

## 2. 失败任务汇总（本次排查）

| 任务 ID | URL | 错误类型 | 根因 |
|---------|-----|----------|------|
| a02920f6 | https://youtu.be/aAPpQC-3EyE | Requested format is not available | **HTTP 403**：HLS 片段全部 403，需 cookies |
| 4d79117b | https://youtu.be/tjW_gms7CME | Requested format is not available | 同上 |
| c5d3c9f8 | https://youtu.be/MPTNHrq_4LU | SSL UNEXPECTED_EOF | 网络/SSL 瞬时问题，重试或换网络可恢复 |
| 1b51bbd3 | Bilibili BV1PsZeB7EU2 | you-get 失败 | B 站反爬，建议用 yt-dlp + cookies |

## 3. 根因分析

### 3.1 "Requested format is not available" 的真实原因

该错误可能由两种不同情况触发：

1. **格式选择过严**：如 `best[height<=1080]` 在部分视频上不可用  
   - 解决：已实现格式回退（`/best`）和重试逻辑

2. **HTTP 403 导致所有格式失败**（本次主要发现）  
   - YouTube 对 HLS 片段返回 403 Forbidden  
   - yt-dlp 逐个尝试格式均失败后，最终报 "Requested format is not available"  
   - **解决**：使用 `cookies_from_browser='chrome'` 或 `cookies_file` 提供 cookies

### 3.2 format=best 的陷阱

对**仅提供 HLS 分离流**（无预合并格式）的 YouTube 视频：

- `format=best` 会立即失败（"best" 指最佳预合并格式，此类视频不存在）
- 正确做法：**不指定 format**，让 yt-dlp 自动合并最佳音视频

已调整重试顺序：优先去掉 format，而非先试 format=best。

### 3.3 SSL 错误

`SSL: UNEXPECTED_EOF_WHILE_READING` 多为瞬时网络问题，可：

- 重试下载
- 检查代理/防火墙
- 更新 yt-dlp：`pip install -U yt-dlp`

## 4. 已实施的代码改进

1. **format_sort 替代 format**（参考 yt-dlp#11295）：分辨率质量（1080p/720p 等）改用 `format_sort`（如 `res:1080,ext`），可回退到可用格式，避免严格 format 导致 "Requested format is not available"

2. **YouTube player_client**：自动添加 `player_client=default,tv`，`tv` 客户端当前不需要 PO Token

3. **重试逻辑**：`Requested format is not available` 时  
   - 若有 format：去掉 format 重试  
   - 若有 format_sort：去掉 format_sort 重试  
   - 否则：用 `bv*+ba/b` 显式合并重试  

4. **错误提示**：重试失败且错误含 403 时，明确建议使用 cookies  

5. **quality=best/auto**：不设置 format，由 yt-dlp 使用默认合并逻辑  

## 5. 用户建议

| 场景 | 建议 |
|------|------|
| YouTube 下载失败 | 使用 `cookies_from_browser='chrome'` 或提供 cookies 文件 |
| Bilibili 412/403 | 使用 cookies，或 `cookies_from_browser='chrome'` |
| 持续失败 | 运行 `pip install -U yt-dlp` 更新到最新版 |
| 网络异常 | 检查代理、防火墙，或更换网络后重试 |

## 6. 验证

- 单元测试：`pytest backend/core/agent/tools/tests/test_video_downloader_tool.py -v`
- 真实下载测试：`https://youtu.be/MPTNHrq_4LU` 在 quality=best 下可成功下载（需正常网络）
