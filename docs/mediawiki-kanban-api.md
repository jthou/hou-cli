# MediaWiki 看板 API 使用说明

看板扩展通过 MediaWiki 的 `api.php?action=kanban` 提供接口。需已登录（Cookie 或 Bot/用户认证）。

## 1. 接口入口

- **URL**：`{MEDIAWIKI_BASE}/api.php`
- **方式**：GET（只读）或 POST（写操作）
- **参数**：`action=kanban`，且必须带 `kanban_action=<操作名>`，其余参数依操作而定。

---

## 2. 读取看板

### 2.1 看板列表 `getboards`

获取当前用户有权限的看板列表。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kanban_action | string | 是 | `getboards` |
| filter_status | string | 否 | 筛选：`active`、`hidden`、`archived`、`deleted`、`all`，默认 `active` |

**示例（GET）**：
```
GET api.php?action=kanban&kanban_action=getboards&filter_status=active
```

**返回**：`{ "boards": [ { "board_id", "board_name", "board_description", ... } ], "result": "success" }`

---

### 2.2 单个看板详情（含列与任务）`getboard`

获取指定看板的列、任务、里程碑。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kanban_action | string | 是 | `getboard` |
| board_id | int | 是 | 看板 ID |

**示例（GET）**：
```
GET api.php?action=kanban&kanban_action=getboard&board_id=1
```

**返回**：`board` 对象，内含：
- 看板基础信息（board_id, kanban_name, board_description, ...）
- `columns`：列数组，每列含 `column_id`、`column_name`、`cards`（该列下的任务）
- `milestones`：里程碑数组  
- 每个 card：`card_id`、`card_title`、`card_description`、`card_priority`、`card_due_date`、`column_id` 等

---

## 3. 操作看板

以下为写操作，需使用 **POST**。

### 3.1 列

| kanban_action | 说明 | 主要参数 |
|---------------|------|----------|
| addcolumn | 添加列 | board_id, name；可选：description, color, position, width, max_cards, wip_limit |
| updatecolumn | 更新列 | board_id, column_id；可选：name, description, color, width, max_cards, wip_limit |
| deletecolumn | 删除列 | board_id, column_id；可选：move_cards_to（目标列 ID，0 表示删除该列下任务） |
| reordercolumns | 列排序 | board_id, column_orders（JSON 字符串，如 `[{"column_id":1,"order":1},{"column_id":2,"order":2}]`） |

### 3.2 任务（卡片）

| kanban_action | 说明 | 主要参数 |
|---------------|------|----------|
| createtask | 创建任务 | board_id, column_id, title；可选：description, priority(low/medium/high/urgent), color, due_date |
| updatetask | 更新任务 | task_id；可选：title, description, priority, color, due_date, status_id（移动到某列） |
| deletetask | 删除任务 | board_id, task_id |
| reordercards | 卡片排序 | board_id, card_orders（JSON，如 `[{"card_id":1,"column_id":2,"order":1}]`） |

### 3.3 里程碑

| kanban_action | 说明 | 主要参数 |
|---------------|------|----------|
| getmilestones | 获取里程碑 | board_id（getboard 已包含，可单独调） |
| createmilestone | 创建 | board_id, name；可选：description, start_date, end_date, color |
| updatemilestone | 更新 | board_id, milestone_id；可选：name, description, start_date, end_date, color, status |
| deletemilestone | 删除 | board_id, milestone_id |

### 3.4 看板状态

| kanban_action | 说明 | 主要参数 |
|---------------|------|----------|
| hideboard | 隐藏看板 | board_id |
| archiveboard | 归档看板 | board_id |
| deleteboard | 删除看板 | board_id |
| restoreboard | 恢复看板 | board_id |

### 3.5 统计与历史

| kanban_action | 说明 | 主要参数 |
|---------------|------|----------|
| getstats | 统计 | board_id（可选）；可选：time_range(week/month), start_date, end_date |
| gethistory | 任务历史 | task_id；可选：limit, offset |

---

## 4. 在 hou-cli 中调用（Python）

项目中的 `MediaWikiClientService` 使用 `mwclient`，可通过 `site.api()` 调用任意 action。

### 4.1 使用现有客户端调用看板 API

```python
from backend.services.mediawiki_client_service import MediaWikiClientService

client = MediaWikiClientService()
client.connect()

# 看板列表
resp = client.site.api("kanban", kanban_action="getboards", filter_status="active")
boards = resp.get("boards", [])

# 单个看板（含列和任务）
resp = client.site.api("kanban", kanban_action="getboard", board_id=1)
board = resp.get("board", {})
columns = board.get("columns", [])
for col in columns:
    print(col["column_name"], ":", [c["card_title"] for c in col.get("cards", [])])

# 创建任务（POST，写操作）
client.site.api(
    "kanban",
    kanban_action="createtask",
    board_id=1,
    column_id=2,
    title="新任务标题",
    description="可选描述",
    priority="medium",
)
```

### 4.2 使用封装方法（MediaWikiClientService）

`backend.services.mediawiki_client_service.client.MediaWikiClientService` 已提供看板封装方法：

```python
from backend.services.mediawiki_client_service import MediaWikiClientService

client = MediaWikiClientService()
client.connect()

# 读取
boards = client.kanban_get_boards(filter_status="active")
board = client.kanban_get_board(board_id=1)
# board["columns"] 每列含 "cards"

# 操作
task_id = client.kanban_create_task(
    board_id=1, column_id=2, title="新任务",
    description="描述", priority="high", due_date="2026-03-10"
)
client.kanban_update_task(task_id, title="新标题", status_id=3)  # 移到列 3
client.kanban_delete_task(board_id=1, task_id=task_id)
```

---

## 5. 常见错误

- **Permission denied**：当前用户对该看板无 view/edit 权限。
- **Board not found**：board_id 不存在或已被删除。
- **Column not found**：column_id 不属于该 board_id。
- **Task title cannot be empty**：创建任务时 title 必填。
- 写操作需 **POST**，且需已登录（Bot 或普通用户）。
