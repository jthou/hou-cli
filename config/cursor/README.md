# Cursor / MCP 配置（仓库模板）

本目录为**可提交**的 Cursor 相关模板，与 **`.agents/`**（Skill 文档真相源）分离：

| 文件 | 说明 |
|------|------|
| `mcp.json.example` | 汇总本仓库提供的 stdio MCP 服务名与脚本路径占位；复制后改为本机 **绝对路径** 与所用 `python`。 |

## 使用步骤

1. 将 `mcp.json.example` 复制为 **`~/.cursor/mcp.json`**（用户级，多项目共用）或 **`项目根/.cursor/mcp.json`**（仅本项目）。
2. 把所有 `/ABSOLUTE/PATH/TO/hou-cli` 替换为本地克隆路径。
3. `command` 建议使用当前 venv 的 Python，与启动 hou-cli 后端一致，避免缺依赖。
4. **不要**把含密钥的 `mcp.json` 提交进 Git；密钥仍来自仓库根 `.env`。

## 与 `.cursor/` 目录

工作区里可能存在 **`.cursor/`**（日志、本机配置）。团队约定：

- **Skill 文档**：以 **`.agents/skills/`** 为准。
- **MCP 合并示例**：以 **`config/cursor/mcp.json.example`** 为准并随仓库更新。
- 个人调试日志、本地实验可留在 `.cursor/`，勿提交密钥与大文件。
