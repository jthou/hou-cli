# TODO-009: macOS 文件快速搜索功能实现

## 任务概述

实现 macOS 平台的文件快速搜索功能，利用系统内置的 `mdfind` 命令和 Spotlight 索引，提供高性能的文件名搜索和内容搜索能力。

**优先级**: P0（高优先级）  
**预计工时**: 3-4 天  
**创建时间**: 2025-01-XX  
**状态**: ⏳ 待开始

**关联文档**:
- [设计文档](../../docs/design/06-文件快速搜索设计文档.md)

---

## 需求分析

### 用户场景

1. **文件名搜索**
   - 用户："搜索所有 .py 文件"
   - 系统：使用 `mdfind -name "*.py"` 快速返回结果

2. **路径限制搜索**
   - 用户："在 /Users/xxx/project 目录下搜索 test.py"
   - 系统：使用 `mdfind -name "test.py" -onlyin /Users/xxx/project` 搜索

3. **文件内容搜索**
   - 用户："搜索包含 'TODO' 的文件"
   - 系统：使用 `mdfind "kMDItemTextContent == 'TODO'"` 搜索文件内容

---

## 任务分解

### 阶段 1: 基础框架和适配器基类（P0）- 预计 1 天

#### 任务 1.1: 创建搜索服务目录结构和基础数据模型

**文件**: `backend/services/search/`（新建目录）

**实现步骤**:
1. 创建目录结构
   ```
   backend/services/search/
   ├── __init__.py
   ├── file_search_service.py
   ├── query_builder.py
   ├── models.py
   └── platform/
       ├── __init__.py
       ├── base.py
       └── macos_search.py
   ```
2. 实现数据模型（FileSearchRequest, FileSearchResult, FileSearchResponse）

**验收标准**:
- [ ] 目录结构创建完整
- [ ] 数据模型定义完整

---

#### 任务 1.2: 实现平台适配器基类

**文件**: `backend/services/search/platform/base.py`（新建）

**实现步骤**:
1. 创建 PlatformAdapter 抽象基类
2. 定义抽象方法：search_by_name, search_by_content, check_availability

**验收标准**:
- [ ] 抽象基类定义完整
- [ ] 所有抽象方法都有文档说明

---

### 阶段 2: macOS 平台适配器实现（P0）- 预计 1.5 天

#### 任务 2.1: 实现 macOS 平台适配器基础功能

**文件**: `backend/services/search/platform/macos_search.py`（新建）

**实现步骤**:
1. 创建 MacOSSearchAdapter 类
2. 实现 check_availability() 方法（检查 mdfind 命令和 Spotlight）
3. 实现 search_by_name() 方法
4. 实现文件信息解析

**验收标准**:
- [ ] MacOSSearchAdapter 类实现完整
- [ ] check_availability() 正确检查系统命令
- [ ] search_by_name() 正确执行搜索
- [ ] 错误处理完善

---

#### 任务 2.2: 实现路径限制和基本过滤

**文件**: `backend/services/search/platform/macos_search.py`

**实现步骤**:
1. 实现路径限制（-onlyin 参数）
2. 实现文件类型过滤
3. 实现结果限制

**验收标准**:
- [ ] 路径限制功能正常
- [ ] 文件类型过滤功能正常
- [ ] 结果限制功能正常

---

#### 任务 2.3: 实现系统要求检查和错误处理

**文件**: `backend/services/search/platform/macos_search.py`

**实现步骤**:
1. 实现启动时检查
2. 实现错误处理
3. 实现错误提示（Spotlight 不可用时的修复指导）

**验收标准**:
- [ ] 启动时检查功能正常
- [ ] 错误处理完善
- [ ] 错误提示清晰有用

---

### 阶段 3: 统一搜索服务和 API 集成（P0）- 预计 0.5 天

#### 任务 3.1: 实现统一搜索服务

**文件**: `backend/services/search/file_search_service.py`（新建）

**实现步骤**:
1. 创建 FileSearchService 类
2. 实现平台检测
3. 实现 search() 方法

**验收标准**:
- [ ] FileSearchService 类实现完整
- [ ] 平台检测正确
- [ ] 搜索接口统一

---

#### 任务 3.2: 集成到后端 API

**文件**: `backend/api/routes.py`

**实现步骤**:
1. 添加搜索 API 路由 `/api/search/files`
2. 集成 FileSearchService
3. 实现错误处理

**验收标准**:
- [ ] API 路由实现完整
- [ ] 请求参数验证正确
- [ ] 响应格式正确

---

### 阶段 4: 功能完善（P1）- 预计 1 天

#### 任务 4.1: 实现文件内容搜索

**文件**: `backend/services/search/platform/macos_search.py`

**实现步骤**:
1. 实现 search_by_content() 方法
2. 使用 mdfind 内容查询语法
3. 处理特殊字符转义

**验收标准**:
- [ ] 内容搜索功能正常
- [ ] 路径限制在内容搜索中生效
- [ ] 特殊字符处理正确

---

#### 任务 4.2: 实现查询构建器

**文件**: `backend/services/search/query_builder.py`（新建）

**实现步骤**:
1. 创建 QueryBuilder 类
2. 实现各种查询构建方法
3. 实现查询验证和转义

**验收标准**:
- [ ] QueryBuilder 类实现完整
- [ ] 所有查询构建方法正常工作
- [ ] 查询验证正确

---

#### 任务 4.3: 实现结果排序和分页

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

#### 任务 4.4: 添加搜索统计信息

**文件**: `backend/services/search/file_search_service.py`

**实现步骤**:
1. 实现搜索统计（耗时、结果数等）
2. 添加统计信息到响应

**验收标准**:
- [ ] 统计信息记录准确
- [ ] 统计信息包含在响应中

---

### 阶段 5: 性能优化（P2）- 预计 0.5 天

#### 任务 5.1: 实现结果缓存

**文件**: `backend/services/search/file_search_service.py`

**实现步骤**:
1. 实现缓存机制（内存缓存，TTL）
2. 实现缓存策略

**验收标准**:
- [ ] 缓存机制正常工作
- [ ] 缓存命中率可接受
- [ ] 内存使用合理

---

#### 任务 5.2: 性能测试和优化

**文件**: `backend/services/search/tests/test_performance.py`（新建）

**实现步骤**:
1. 实现性能测试
2. 性能优化

**验收标准**:
- [ ] 小目录搜索响应时间 < 100ms
- [ ] 大目录搜索响应时间 < 500ms

---

#### 任务 5.3: 支持并发搜索

**文件**: `backend/services/search/file_search_service.py`

**实现步骤**:
1. 实现并发搜索（asyncio）
2. 实现线程安全

**验收标准**:
- [ ] 并发搜索功能正常
- [ ] 线程安全保证

---

### 阶段 6: 测试和文档（P1）- 预计 0.5 天

#### 任务 6.1: 单元测试

**文件**: `backend/services/search/tests/`（新建测试目录）

**实现步骤**:
1. 平台适配器测试
2. 查询构建器测试
3. 搜索服务测试

**验收标准**:
- [ ] 单元测试覆盖主要功能
- [ ] 测试覆盖率 > 80%

---

#### 任务 6.2: 集成测试

**文件**: `backend/services/search/tests/test_integration.py`（新建）

**实现步骤**:
1. 端到端测试
2. 平台特定测试

**验收标准**:
- [ ] 集成测试覆盖主要场景
- [ ] 所有测试通过

---

#### 任务 6.3: 文档更新

**文件**: `backend/services/search/README.md`（新建）

**实现步骤**:
1. 编写使用文档
2. 更新项目文档

**验收标准**:
- [ ] 文档完整清晰
- [ ] 示例代码可运行

---

## 验收标准

### 功能验收
- [ ] 可以按文件名搜索文件
- [ ] 可以按文件内容搜索文件
- [ ] 支持路径限制搜索
- [ ] 支持文件类型过滤
- [ ] 支持结果排序和分页
- [ ] API 接口正常工作

### 性能验收
- [ ] 小目录搜索响应时间 < 100ms
- [ ] 大目录搜索响应时间 < 500ms

### 代码质量验收
- [ ] 代码符合项目规范
- [ ] 错误处理完善
- [ ] 测试覆盖充分（> 80%）

---

**创建时间**: 2025-01-XX  
**优先级**: P0  
**状态**: ⏳ 待开始

