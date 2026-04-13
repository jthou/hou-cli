# `.agents/` 目录说明

## 职责（与 `.cursor` 的分工）

| 位置 | 用途 | 是否进 Git |
|------|------|------------|
| **`.agents/skills/`** | 本仓库**权威**的 Agent Skill：产品流程、提示约定、与 hou-cli 后端/前端路径对齐的说明（`SKILL.md` / `reference.md`）。Orchestrator 注册的 Python 技能在 `backend/core/agent/skills/`，二者可交叉引用文档名。 | **是** |
| **`.cursor/`** | Cursor IDE **本机**配置：调试日志、个人 `mcp.json`、可选的 `.cursor/rules`、若需让 Cursor UI 识别 Skill 而放置的**本地**副本或符号链接。 | **默认否**（见仓库根 `.gitignore`，仅忽略日志类噪音） |

原则：**可复现、可评审、与产品行为一致**的 Skill 文档放在 **`.agents/skills`**；不要在 `.cursor` 里维护另一套长期分叉的 Markdown。

## 目录约定

```
.agents/
└── skills/
    └── <skill-id>/
        ├── SKILL.md       # 主说明（可被 Cursor / 人类 / CI 引用）
        └── reference.md   # 可选：长参考、链接表
```

命名：与 frontmatter `name`、后端技能名、任务类型名保持一致或可追溯（见各 `SKILL.md` 头部）。

## 与 Cursor「项目 Skill」路径的关系

若希望 Cursor 侧「Skills」面板加载与本仓库**同一内容**，可在本机使用**符号链接**（示例）：

```bash
mkdir -p .cursor/skills
ln -sf ../../.agents/skills/daily-ai-briefing .cursor/skills/daily-ai-briefing
```

是否链接由开发者自选；**真相源**仍在 `.agents/skills/`。

## MCP 配置模板

编辑器侧 MCP 的**合并示例**（含本仓库 `scripts/mcp_*.py`）见 **`config/cursor/mcp.json.example`**，复制到 `~/.cursor/mcp.json` 或项目 `.cursor/mcp.json` 后把路径换成本机绝对路径。
