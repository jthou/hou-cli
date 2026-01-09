# 数据存储目录统一规范

## 概述

所有临时数据、会话数据、配置文件等都应统一存储在项目配置目录下，而不是项目根目录或系统临时目录。这确保了：

- ✅ 跨平台兼容性
- ✅ 统一管理
- ✅ 易于备份和清理
- ✅ 符合操作系统规范

## 配置目录位置

项目使用 `shared.platform_utils.get_app_data_dir()` 获取统一的配置目录：

- **macOS**: `~/Library/Application Support/hou-cli`
- **Linux**: `~/.local/share/hou-cli`
- **Windows**: `%LOCALAPPDATA%\hou-cli`

## 目录结构

```
~/.local/share/hou-cli/              # 项目配置目录（Linux）
├── browser-profiles/                # 浏览器会话数据
│   ├── zhihu/                       # 知乎会话
│   ├── github/                      # GitHub 会话
│   └── weibo/                       # 微博会话
├── contexts/                        # 上下文会话数据
│   ├── sessions.json                # 会话列表
│   └── {session_id}/                # 会话目录
│       └── messages.json            # 会话消息
├── contexts.db                      # 上下文数据库（SQLite）
├── mediawiki_sync/                  # MediaWiki 同步数据
│   ├── sync_status.json             # 同步状态
│   └── {page_title}.json            # 页面数据
├── tmp/                             # 临时文件
│   └── {temp_files}                 # 临时文件（如 gvim 编辑的 MediaWiki 页面）
├── port.txt                         # 端口文件
└── last_session.txt                 # 最后会话ID
```

## 已统一的模块

### 1. 浏览器会话数据

**文件**: `backend/core/agent/tools/builtin/browser_tool.py`

**位置**: `{app_data_dir}/browser-profiles/{site_name}`

**使用方式**:
```python
from shared.platform_utils import get_app_data_dir
profile_dir = get_app_data_dir() / "browser-profiles" / "zhihu"
```

**工具参数**: `user_data_dir="zhihu"` (自动使用项目配置目录)

### 2. 上下文会话数据

**文件**: `backend/core/context/storage/file.py`

**位置**: `{app_data_dir}/contexts`

**使用方式**:
```python
from shared.platform_utils import get_app_data_dir
storage_dir = get_app_data_dir() / "contexts"
```

**默认行为**: 如果不指定 `storage_dir`，自动使用项目配置目录

### 3. 上下文数据库

**文件**: `backend/core/context/storage/database.py`

**位置**: `{app_data_dir}/contexts.db`

**使用方式**:
```python
from shared.platform_utils import get_app_data_dir
db_path = str(get_app_data_dir() / "contexts.db")
```

**默认行为**: 如果不指定 `db_path`，自动使用项目配置目录

### 4. MediaWiki 同步数据

**文件**: `backend/services/mediawiki/sync_service.py`

**位置**: `{app_data_dir}/mediawiki_sync`

**使用方式**:
```python
from shared.platform_utils import get_app_data_dir
sync_data_dir = get_app_data_dir() / "mediawiki_sync"
```

### 5. 临时文件（Gvim 服务）

**文件**: `backend/services/editor/gvim_service.py`

**位置**: `{app_data_dir}/tmp`

**使用方式**:
```python
from shared.platform_utils import get_app_data_dir
tmpdir = str(get_app_data_dir() / "tmp")
```

**默认行为**: 如果不指定 `tmpdir`，自动使用项目配置目录

## 使用规范

### 1. 导入工具函数

```python
from shared.platform_utils import get_app_data_dir
```

### 2. 创建子目录

```python
# 获取配置目录
base = get_app_data_dir()

# 创建子目录
data_dir = base / "my_module" / "data"
data_dir.mkdir(parents=True, exist_ok=True)
```

### 3. 默认参数处理

```python
def __init__(self, data_dir: Optional[Path] = None):
    """初始化
    
    Args:
        data_dir: 数据目录，如果为 None，使用项目配置目录
    """
    if data_dir is None:
        from shared.platform_utils import get_app_data_dir
        data_dir = get_app_data_dir() / "my_module"
    self.data_dir = Path(data_dir)
    self.data_dir.mkdir(parents=True, exist_ok=True)
```

### 4. 文件路径

```python
# 数据库文件
db_path = str(get_app_data_dir() / "my_module.db")

# 配置文件
config_file = get_app_data_dir() / "my_module" / "config.json"

# 临时文件
temp_file = get_app_data_dir() / "tmp" / "temp_file.txt"
```

## 迁移指南

### 从项目根目录迁移

**旧代码**:
```python
storage_dir = Path("data/contexts")
```

**新代码**:
```python
from shared.platform_utils import get_app_data_dir
storage_dir = get_app_data_dir() / "contexts"
```

### 从系统临时目录迁移

**旧代码**:
```python
tmpdir = tempfile.gettempdir()
```

**新代码**:
```python
from shared.platform_utils import get_app_data_dir
tmpdir = str(get_app_data_dir() / "tmp")
```

### 从硬编码路径迁移

**旧代码**:
```python
if platform.system() == "Windows":
    base = Path.home() / "AppData" / "Local" / "hou-cli"
elif platform.system() == "Darwin":
    base = Path.home() / "Library" / "Application Support" / "hou-cli"
else:
    base = Path.home() / ".local" / "share" / "hou-cli"
```

**新代码**:
```python
from shared.platform_utils import get_app_data_dir
base = get_app_data_dir()
```

## 检查清单

在添加新的数据存储功能时，确保：

- [ ] 使用 `get_app_data_dir()` 获取配置目录
- [ ] 在配置目录下创建子目录，而不是项目根目录
- [ ] 默认参数为 `None`，自动使用项目配置目录
- [ ] 确保目录存在（使用 `mkdir(parents=True, exist_ok=True)`）
- [ ] 跨平台兼容（不要硬编码路径）
- [ ] 文档中说明数据存储位置

## 例外情况

以下情况可以使用系统临时目录或项目根目录：

1. **测试代码**: 测试中的临时文件可以使用 `tempfile.mkdtemp()`
2. **开发调试**: 开发时的调试数据可以放在项目根目录的 `data/` 下（但不应提交到版本控制）
3. **用户明确指定**: 如果用户明确指定了路径，应使用用户指定的路径

## 参考

- `shared/platform_utils.py` - 平台工具函数
- `docs/tools/browser-session-management.md` - 浏览器会话管理示例

