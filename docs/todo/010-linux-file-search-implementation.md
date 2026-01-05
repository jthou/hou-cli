# TODO-010: Linux 文件快速搜索功能实现

## 任务概述

实现 Linux 平台的文件快速搜索功能，优先使用系统内置的 `locate/plocate` 命令，降级到文件系统遍历，提供高性能的文件名搜索能力。

**优先级**: P0（高优先级）  
**预计工时**: 3-4 天  
**创建时间**: 2025-01-XX  
**状态**: ⏳ 待开始

**关联文档**:
- [设计文档](../../docs/design/06-文件快速搜索设计文档.md)
- [macOS 实现参考](../009-macos-file-search-implementation.md)

---

## 需求分析

### 用户场景

1. **文件名搜索（使用 locate）**
   - 用户："搜索所有 .py 文件"
   - 系统：使用 `locate -b "*.py"` 或 `plocate -b "*.py"` 快速返回结果

2. **路径限制搜索**
   - 用户："在 /home/user/project 目录下搜索 test.py"
   - 系统：使用 `locate -b "test.py" | grep "^/home/user/project"` 搜索

3. **文件系统遍历降级**
   - 用户："locate 数据库不存在，使用文件系统遍历"
   - 系统：使用 `pathlib.Path.rglob()` 递归遍历，支持异步优化

---

## 任务分解

### 阶段 1: 基础框架和适配器基类（P0）- 预计 0.5 天

**说明**: 如果阶段 1 已在 macOS 实现中完成，可跳过此阶段，直接进入阶段 2。

#### 任务 1.1: 创建搜索服务目录结构和基础数据模型

**文件**: `backend/services/search/`（如果已存在则跳过）

**实现步骤**:
1. 确认目录结构存在
   ```
   backend/services/search/
   ├── __init__.py
   ├── file_search_service.py
   ├── query_builder.py
   ├── models.py
   └── platform/
       ├── __init__.py
       ├── base.py
       └── linux_search.py
   ```
2. 确认数据模型（FileSearchRequest, FileSearchResult, FileSearchResponse）已定义

**验收标准**:
- [ ] 目录结构完整
- [ ] 数据模型定义完整（如果已存在则验证）

---

#### 任务 1.2: 确认平台适配器基类

**文件**: `backend/services/search/platform/base.py`（如果已存在则验证）

**实现步骤**:
1. 确认 PlatformAdapter 抽象基类存在
2. 确认抽象方法：search_by_name, search_by_content, check_availability

**验收标准**:
- [ ] 抽象基类定义完整
- [ ] 所有抽象方法都有文档说明

---

### 阶段 2: Linux 平台适配器实现（P0）- 预计 1.5 天

#### 任务 2.1: 实现 Linux 平台适配器基础功能

**文件**: `backend/services/search/platform/linux_search.py`（新建）

**实现步骤**:
1. 创建 LinuxSearchAdapter 类，继承 PlatformAdapter
2. 实现 check_availability() 方法
   - 检查 `locate` 或 `plocate` 命令是否可用
   - 检查索引数据库是否存在：
     - `locate`: `/var/lib/mlocate/mlocate.db`
     - `plocate`: `/var/lib/plocate/plocate.db`
   - 返回可用状态和数据库路径
3. 实现 search_by_name() 方法
   - 优先使用 `locate` 或 `plocate` 命令
   - 支持通配符匹配（`-b` 参数用于精确匹配文件名）
   - 解析命令输出，转换为统一的结果格式
4. 实现文件信息解析（使用 `os.stat()` 获取文件元数据）

**验收标准**:
- [ ] LinuxSearchAdapter 类实现完整
- [ ] check_availability() 正确检查系统命令和数据库
- [ ] search_by_name() 正确执行搜索
- [ ] 文件信息解析正确（路径、大小、修改时间等）
- [ ] 错误处理完善

---

#### 任务 2.2: 实现路径限制和基本过滤

**文件**: `backend/services/search/platform/linux_search.py`

**实现步骤**:
1. 实现路径限制
   - 使用 `grep` 过滤 `locate` 输出：`locate pattern | grep "^/path/to/dir"`
   - 或使用 `locate` 的 `-r` 正则表达式选项
2. 实现文件类型过滤
   - 在 `locate` 命令中使用通配符：`locate "*.py"`
   - 或在结果中过滤扩展名
3. 实现结果限制
   - 使用 `head` 或 `tail` 命令限制结果数量
   - 或在 Python 中限制结果数量

**验收标准**:
- [ ] 路径限制功能正常
- [ ] 文件类型过滤功能正常
- [ ] 结果限制功能正常

---

#### 任务 2.3: 实现文件系统遍历降级方案

**文件**: `backend/services/search/platform/linux_search.py`

**实现步骤**:
1. 实现 FallbackSearch 类（或作为 LinuxSearchAdapter 的方法）
2. 使用 `pathlib.Path.rglob()` 递归遍历文件系统
3. 实现通配符匹配（使用 `fnmatch` 模块）
4. 实现正则表达式匹配（使用 `re` 模块）
5. 实现异步遍历优化（大目录使用 `asyncio`）
6. 实现搜索深度限制（避免遍历过深）

**验收标准**:
- [ ] 文件系统遍历功能正常
- [ ] 通配符匹配正确
- [ ] 正则表达式匹配正确
- [ ] 异步遍历性能可接受
- [ ] 深度限制生效

---

#### 任务 2.4: 实现系统要求检查和错误处理

**文件**: `backend/services/search/platform/linux_search.py`

**实现步骤**:
1. 实现启动时检查
   - 检查 `locate` 或 `plocate` 命令是否可用
   - 检查索引数据库是否存在
   - 如果数据库不存在，提供明确的错误提示和修复指导
2. 实现错误处理
   - 捕获命令执行异常
   - 提供友好的错误信息
3. 实现错误提示（locate 不可用时的修复指导）
   - 提示用户安装 `mlocate` 或 `plocate` 包
   - 提示用户运行 `updatedb` 创建索引数据库
   - 提供安装和配置的详细步骤：
     ```bash
     # Ubuntu/Debian
     sudo apt-get install mlocate
     sudo updatedb
     
     # Fedora/RHEL
     sudo dnf install mlocate
     sudo updatedb
     
     # Arch Linux
     sudo pacman -S mlocate
     sudo updatedb
     ```

**验收标准**:
- [ ] 启动时检查功能正常
- [ ] 错误处理完善
- [ ] 错误提示清晰有用
- [ ] 提供详细的安装和配置指导

---

### 阶段 3: 统一搜索服务和 API 集成（P0）- 预计 0.5 天

#### 任务 3.1: 集成 Linux 适配器到统一搜索服务

**文件**: `backend/services/search/file_search_service.py`

**实现步骤**:
1. 在 FileSearchService 中添加 Linux 平台检测
2. 集成 LinuxSearchAdapter
3. 实现降级逻辑（locate 不可用时使用文件系统遍历）

**验收标准**:
- [ ] Linux 平台检测正确
- [ ] LinuxSearchAdapter 正确集成
- [ ] 降级逻辑正常工作

---

#### 任务 3.2: 验证 API 集成

**文件**: `backend/api/routes.py`

**实现步骤**:
1. 确认搜索 API 路由 `/api/search/files` 已存在
2. 验证 Linux 平台下的 API 正常工作
3. 测试错误处理

**验收标准**:
- [ ] API 路由正常工作
- [ ] 请求参数验证正确
- [ ] 响应格式正确
- [ ] 错误处理正确

---

### 阶段 4: 功能完善（P1）- 预计 1 天

#### 任务 4.1: 实现查询构建器（Linux 特定）

**文件**: `backend/services/search/query_builder.py`

**实现步骤**:
1. 扩展 QueryBuilder 类，支持 Linux 特定查询
2. 实现 `locate` 命令构建
   - 文件名查询：`locate -b "pattern"`
   - 路径限制：结合 `grep` 或使用正则表达式
   - 文件类型过滤：通配符模式
3. 实现查询验证和转义
   - 特殊字符转义（避免 shell 注入）
   - 路径验证

**验收标准**:
- [ ] 查询构建器支持 Linux 特定查询
- [ ] locate 命令构建正确
- [ ] 查询验证正确
- [ ] 特殊字符转义正确

---

#### 任务 4.2: 实现结果排序和分页

**文件**: `backend/services/search/file_search_service.py`

**实现步骤**:
1. 实现排序功能（按文件名、大小、时间）
2. 实现分页功能
3. 实现结果格式化

**验收标准**:
- [ ] 排序功能正常
- [ ] 分页功能正常
- [ ] 分页信息准确

---

#### 任务 4.3: 实现大目录异步遍历优化

**文件**: `backend/services/search/platform/linux_search.py`

**实现步骤**:
1. 实现异步文件系统遍历（使用 `asyncio`）
2. 实现并发遍历（限制并发数）
3. 实现进度回调（可选）

**验收标准**:
- [ ] 异步遍历功能正常
- [ ] 并发控制正确
- [ ] 性能提升明显（大目录）

---

#### 任务 4.4: 添加搜索统计信息

**文件**: `backend/services/search/file_search_service.py`

**实现步骤**:
1. 实现搜索统计（耗时、结果数、搜索方法等）
2. 添加统计信息到响应

**验收标准**:
- [ ] 统计信息记录准确
- [ ] 统计信息包含在响应中
- [ ] 区分 locate 和文件系统遍历的统计

---

### 阶段 5: 性能优化（P2）- 预计 0.5 天

#### 任务 5.1: 实现结果缓存

**文件**: `backend/services/search/file_search_service.py`

**实现步骤**:
1. 实现缓存机制（内存缓存，TTL）
2. 实现缓存策略（区分 locate 和文件系统遍历）
3. 实现缓存失效（文件系统变化时）

**验收标准**:
- [ ] 缓存机制正常工作
- [ ] 缓存命中率可接受
- [ ] 内存使用合理

---

#### 任务 5.2: 性能测试和优化

**文件**: `backend/services/search/tests/test_linux_performance.py`（新建）

**实现步骤**:
1. 实现性能测试
   - 小目录搜索（< 1000 文件）
   - 大目录搜索（> 1000 文件）
   - locate vs 文件系统遍历对比
2. 性能优化
   - 优化 locate 命令参数
   - 优化文件系统遍历算法
   - 优化结果处理

**验收标准**:
- [ ] 小目录搜索响应时间 < 100ms（locate）
- [ ] 大目录搜索响应时间 < 500ms（locate）
- [ ] 文件系统遍历性能可接受（大目录 < 2s）

---

#### 任务 5.3: 支持并发搜索

**文件**: `backend/services/search/file_search_service.py`

**实现步骤**:
1. 实现并发搜索（asyncio）
2. 实现线程安全
3. 实现资源限制（避免过多并发）

**验收标准**:
- [ ] 并发搜索功能正常
- [ ] 线程安全保证
- [ ] 资源使用合理

---

### 阶段 6: 测试和文档（P1）- 预计 0.5 天

#### 任务 6.1: 单元测试

**文件**: `backend/services/search/tests/test_linux_search.py`（新建）

**实现步骤**:
1. Linux 平台适配器测试
   - check_availability() 测试
   - search_by_name() 测试（locate）
   - search_by_name() 测试（文件系统遍历）
   - 路径限制测试
   - 文件类型过滤测试
2. 查询构建器测试（Linux 特定）
3. 错误处理测试

**验收标准**:
- [ ] 单元测试覆盖主要功能
- [ ] 测试覆盖率 > 80%
- [ ] 所有测试通过

---

#### 任务 6.2: 集成测试

**文件**: `backend/services/search/tests/test_linux_integration.py`（新建）

**实现步骤**:
1. 端到端测试
   - API 接口测试
   - 完整搜索流程测试
2. 平台特定测试
   - locate 可用场景测试
   - locate 不可用场景测试（降级）
   - 数据库不存在场景测试

**验收标准**:
- [ ] 集成测试覆盖主要场景
- [ ] 所有测试通过
- [ ] 降级场景测试通过

---

#### 任务 6.3: 文档更新

**文件**: `backend/services/search/README.md`（更新）

**实现步骤**:
1. 编写 Linux 平台使用文档
2. 添加 Linux 特定配置说明
3. 添加故障排除指南
4. 更新项目文档

**验收标准**:
- [ ] 文档完整清晰
- [ ] 示例代码可运行
- [ ] 故障排除指南有用

---

## 技术细节

### locate/plocate 命令使用

#### locate 命令
```bash
# 基本搜索
locate pattern

# 精确匹配文件名（-b 参数）
locate -b "pattern"

# 限制结果数量
locate pattern | head -n 100

# 路径过滤
locate pattern | grep "^/path/to/dir"

# 正则表达式搜索（-r 参数）
locate -r "pattern"
```

#### plocate 命令（更快）
```bash
# plocate 是 locate 的更快替代品
plocate -b "pattern"
plocate -r "pattern"
```

### 数据库路径

- **mlocate**: `/var/lib/mlocate/mlocate.db`
- **plocate**: `/var/lib/plocate/plocate.db`

### 文件系统遍历优化

```python
import asyncio
from pathlib import Path
import fnmatch

async def async_search(pattern, root_path, max_depth=10):
    """异步文件系统遍历搜索"""
    results = []
    root = Path(root_path)
    
    async def search_dir(path, depth=0):
        if depth > max_depth:
            return
        
        try:
            for item in path.iterdir():
                if item.is_file():
                    if fnmatch.fnmatch(item.name, pattern):
                        results.append(item)
                elif item.is_dir():
                    await search_dir(item, depth + 1)
        except PermissionError:
            pass  # 忽略权限错误
    
    await search_dir(root)
    return results
```

---

## 验收标准

### 功能验收
- [ ] 可以按文件名搜索文件（使用 locate）
- [ ] 可以按文件名搜索文件（文件系统遍历降级）
- [ ] 支持路径限制搜索
- [ ] 支持文件类型过滤
- [ ] 支持结果排序和分页
- [ ] API 接口正常工作
- [ ] 系统要求检查正常工作
- [ ] 错误提示清晰有用

### 性能验收
- [ ] 小目录搜索响应时间 < 100ms（locate）
- [ ] 大目录搜索响应时间 < 500ms（locate）
- [ ] 文件系统遍历性能可接受（大目录 < 2s）

### 代码质量验收
- [ ] 代码符合项目规范
- [ ] 错误处理完善
- [ ] 测试覆盖充分（> 80%）
- [ ] 文档完整

---

## 已知问题和限制

1. **locate 数据库可能不是最新的**
   - 数据库由 `updatedb` 定期更新（通常每天一次）
   - 新创建的文件可能不会立即出现在搜索结果中
   - 需要告知用户此限制

2. **文件系统遍历性能限制**
   - 大目录（> 10000 文件）遍历可能较慢
   - 需要实现深度限制和异步优化

3. **权限问题**
   - 某些目录可能需要 root 权限访问
   - 需要处理 PermissionError

---

**创建时间**: 2025-01-XX  
**优先级**: P0  
**状态**: ⏳ 待开始

