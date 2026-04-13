# 本目录（Cursor 本地）

- **Skill 文档真相源**：`.agents/skills/`（仓库内评审与协作以该处为准）。
- **MCP 合并模板**：`config/cursor/mcp.json.example` → 复制为 `~/.cursor/mcp.json` 或本目录下的 `mcp.json`（`mcp.json` 已被 gitignore，勿提交密钥）。
- 若需让 Cursor「Skills」加载与仓库同一份 Markdown，可对 `.agents/skills/<id>` 建立符号链接到 `.cursor/skills/<id>`（可选）。

时间：2026-04-12；理由：与 `.agents`、`config/cursor` 分工一致；方法：本文件可提交，个人密钥仅留在被忽略的 `mcp.json`。
