# 磁盘空间分析报告

**扫描范围**: 用户主目录 `/Users/jintinghou`（无需 sudo）  
**全盘已用**: 805.27 GB (df 统计)  
**生成时间**: 基于 `docs/disk_report.txt` 中间结果

---

## Top 15 占用（≥1 GB）

| 大小 | 路径 |
|------|------|
| 34.61 GB | 微信 (com.tencent.xinWeChat) |
| 26.02 GB | Cursor |
| 16.57 GB | Lingma（通义灵码） |
| 12.38 GB | VS Code |
| 10.18 GB | LarkShell（飞书） |
| 9.02 GB | QQ 音乐 |
| 7.57 GB | Google（Chrome 等） |
| 3.10 GB | Qoder |
| 2.78 GB | WPS Office |
| 1.54 GB | 钉钉 |
| 1.47 GB | 某应用容器 (22E021C0...) |
| 1.31 GB | AnythingLLM |
| 1.13 GB | Microsoft Edge |

---

## 可清理项建议

| 类型 | 路径/操作 | 预估可释放 |
|------|-----------|------------|
| 微信缓存 | `~/Library/Containers/com.tencent.xinWeChat` | 可清理聊天缓存、图片视频 |
| Cursor | `~/Library/Application Support/Cursor` | 模型/扩展缓存，谨慎清理 |
| Lingma | `~/Library/Application Support/Lingma` | 可清理缓存 |
| VS Code | `~/Library/Application Support/Code` | 扩展/缓存可清理 |
| Chrome/Edge | `~/Library/Application Support/Google`、`Microsoft Edge` | 浏览器缓存 |
| QQ 音乐 | 应用内清理缓存 | 约 9 GB |
| 钉钉 | `~/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac` | 约 1.5 GB |

---

## 建议操作

1. **微信**：在微信设置中清理聊天文件、图片视频缓存（约 34 GB 中大部分可清理）
2. **开发工具**：Cursor + VS Code + Lingma 合计约 55 GB，可考虑清理扩展缓存、旧版本
3. **音乐/办公**：QQ 音乐、WPS 可在应用内清理缓存
4. **系统缓存**：`rm -rf ~/Library/Caches/*`（谨慎，可能影响应用）
5. **完整扫描**：运行 `sudo python3 scripts/disk_system_data_breakdown.py -o docs/disk_report_full.txt` 获取全盘分析（含 /opt、/Library 等）

---

*注：完整报告需等待 `disk_system_data_breakdown.py` 跑完，或使用 sudo 执行全盘扫描。*
