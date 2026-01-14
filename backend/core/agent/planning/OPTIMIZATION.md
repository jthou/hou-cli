# 规划功能优化建议

## 当前实现分析

### 已实现功能
- ✅ 规划文件创建和管理
- ✅ 任务复杂度判断
- ✅ 自动更新机制
- ✅ 对话评估集成
- ✅ 错误处理
- ✅ 测试用例

### 潜在问题

1. **性能问题**
   - 每次更新都要读取整个文件，然后写回
   - 文件操作是同步的，可能阻塞主流程
   - 频繁的文件 I/O 操作

2. **文件管理问题**
   - 没有文件清理机制，可能积累大量文件
   - 没有文件大小限制
   - 没有文件版本管理

3. **复杂度判断问题**
   - 基于规则的判断可能不够准确
   - 没有使用 LLM 进行智能判断

4. **并发问题**
   - 多会话并发时可能文件冲突
   - 没有文件锁机制

## 优化建议

### 1. 性能优化 ⭐⭐⭐⭐⭐

#### 1.1 异步文件更新
**问题**：当前文件更新是同步的，可能阻塞主流程

**方案**：
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class PlanningManager:
    def __init__(self, ...):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.update_queue = asyncio.Queue()
    
    async def add_progress_async(self, action: str, ...):
        """异步添加进度"""
        await self.update_queue.put(('progress', action, ...))
        # 后台任务处理队列
```

**收益**：
- 不阻塞主流程
- 提升响应速度
- 可以批量处理更新

#### 1.2 文件缓存机制
**问题**：每次更新都要读取整个文件

**方案**：
```python
class PlanningManager:
    def __init__(self, ...):
        self._file_cache = {}  # 缓存文件内容
        self._cache_ttl = 5  # 缓存有效期（秒）
    
    def _get_cached_content(self, file_path: Path) -> str:
        """获取缓存的文件内容"""
        cache_key = str(file_path)
        if cache_key in self._file_cache:
            content, timestamp = self._file_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return content
        # 缓存失效，重新读取
        content = file_path.read_text(encoding='utf-8')
        self._file_cache[cache_key] = (content, time.time())
        return content
```

**收益**：
- 减少文件 I/O 操作
- 提升更新速度
- 降低磁盘负载

#### 1.3 批量更新机制
**问题**：每次工具调用都更新文件，可能过于频繁

**方案**：
```python
class PlanningManager:
    def __init__(self, ...):
        self._pending_updates = []  # 待更新的操作
        self._batch_size = 5  # 批量大小
        self._batch_timeout = 2  # 批量超时（秒）
    
    async def add_progress_batched(self, action: str, ...):
        """批量添加进度"""
        self._pending_updates.append(('progress', action, ...))
        if len(self._pending_updates) >= self._batch_size:
            await self._flush_updates()
```

**收益**：
- 减少文件写入次数
- 提升性能
- 降低磁盘磨损

### 2. 文件管理优化 ⭐⭐⭐⭐

#### 2.1 自动清理机制
**问题**：规划文件会不断积累，占用磁盘空间

**方案**：
```python
class PlanningManager:
    def cleanup_old_files(self, max_age_days: int = 7, max_files: int = 100):
        """清理旧文件"""
        files = sorted(self.work_dir.glob("*_*.md"), key=lambda p: p.stat().st_mtime)
        
        # 按时间清理
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        for file in files:
            if file.stat().st_mtime < cutoff_time:
                file.unlink()
        
        # 按数量清理
        if len(files) > max_files:
            for file in files[:-max_files]:
                file.unlink()
```

**收益**：
- 自动管理磁盘空间
- 避免文件积累
- 可配置清理策略

#### 2.2 文件大小限制
**问题**：规划文件可能变得很大

**方案**：
```python
MAX_FILE_SIZE = 100 * 1024  # 100KB

def add_finding(self, finding: str, ...):
    """添加发现，检查文件大小"""
    file_path = self.get_planning_files(session_id).findings
    if file_path.exists() and file_path.stat().st_size > MAX_FILE_SIZE:
        # 压缩或归档旧内容
        self._archive_old_content(file_path)
```

**收益**：
- 控制文件大小
- 提升读取性能
- 避免内存问题

#### 2.3 文件压缩
**问题**：规划文件可能包含大量历史信息

**方案**：
```python
def archive_planning_files(self, session_id: str):
    """归档规划文件"""
    files = self.get_planning_files(session_id)
    archive_path = self.work_dir / "archive" / f"{session_id}.tar.gz"
    
    import tarfile
    with tarfile.open(archive_path, "w:gz") as tar:
        for file in [files.task_plan, files.findings, files.progress]:
            if file.exists():
                tar.add(file, arcname=file.name)
```

**收益**：
- 节省磁盘空间
- 保留历史记录
- 便于管理

### 3. 复杂度判断优化 ⭐⭐⭐⭐

#### 3.1 LLM 辅助判断
**问题**：基于规则的判断可能不够准确

**方案**：
```python
class TaskComplexityAnalyzer:
    async def is_complex_task_llm(self, task: str, llm_service) -> bool:
        """使用 LLM 判断任务复杂度"""
        prompt = f"""判断以下任务是否需要详细规划（创建 task_plan.md）：
        
任务：{task}

请分析任务复杂度，考虑：
1. 任务步骤数量
2. 所需工具数量
3. 是否需要研究
4. 是否需要多轮对话

只返回 "是" 或 "否"。"""
        
        response = await llm_service.chat(user_prompt=prompt)
        return "是" in response or "yes" in response.lower()
    
    async def is_complex_task(self, task: str, ...) -> bool:
        """混合判断：规则 + LLM"""
        # 先用规则快速判断
        rule_result = self._is_complex_by_rules(task, ...)
        
        # 如果规则判断不确定，使用 LLM
        if rule_result is None:
            return await self.is_complex_task_llm(task, llm_service)
        
        return rule_result
```

**收益**：
- 更准确的判断
- 减少误判
- 提升用户体验

#### 3.2 判断结果缓存
**问题**：相同任务可能重复判断

**方案**：
```python
class TaskComplexityAnalyzer:
    def __init__(self, ...):
        self._judgment_cache = {}  # 缓存判断结果
    
    def is_complex_task(self, task: str, ...) -> bool:
        """带缓存的判断"""
        cache_key = hash(task[:100])  # 使用任务前100字符作为key
        if cache_key in self._judgment_cache:
            return self._judgment_cache[cache_key]
        
        result = self._judgment_task(task, ...)
        self._judgment_cache[cache_key] = result
        return result
```

**收益**：
- 避免重复判断
- 提升性能
- 减少 LLM 调用

### 4. 并发安全优化 ⭐⭐⭐

#### 4.1 文件锁机制
**问题**：多会话并发时可能文件冲突

**方案**：
```python
import fcntl  # Linux
# 或 import msvcrt  # Windows

class PlanningManager:
    def _update_file_with_lock(self, file_path: Path, update_func):
        """带锁的文件更新"""
        with open(file_path, 'r+', encoding='utf-8') as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # 排他锁
                content = f.read()
                new_content = update_func(content)
                f.seek(0)
                f.write(new_content)
                f.truncate()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # 释放锁
```

**收益**：
- 避免文件冲突
- 保证数据一致性
- 支持并发访问

#### 4.2 重试机制
**问题**：文件操作可能失败

**方案**：
```python
from tenacity import retry, stop_after_attempt, wait_exponential

class PlanningManager:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=3))
    def add_progress(self, action: str, ...):
        """带重试的进度添加"""
        try:
            # 文件操作
            ...
        except IOError as e:
            logger.warning(f"文件操作失败，重试: {str(e)}")
            raise
```

**收益**：
- 提高可靠性
- 处理临时故障
- 更好的错误恢复

### 5. 规划文件格式优化 ⭐⭐⭐

#### 5.1 增量更新
**问题**：每次更新都要读取整个文件

**方案**：
```python
def add_progress_incremental(self, action: str, ...):
    """增量更新进度文件"""
    file_path = self.get_planning_files(session_id).progress
    
    # 使用追加模式
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(f"\n- {action}\n")
        if files_modified:
            for file in files_modified:
                f.write(f"  - {file}\n")
```

**收益**：
- 避免读取整个文件
- 提升更新速度
- 降低内存使用

#### 5.2 结构化存储
**问题**：Markdown 格式解析效率低

**方案**：
```python
# 使用 JSON 作为后端存储，Markdown 作为展示格式
class PlanningManager:
    def __init__(self, ...):
        self.use_json_backend = True  # 使用 JSON 后端
    
    def add_progress(self, action: str, ...):
        """使用 JSON 后端存储"""
        json_file = self.get_planning_files(session_id).progress.with_suffix('.json')
        
        # 读取 JSON
        if json_file.exists():
            data = json.loads(json_file.read_text())
        else:
            data = {"actions": []}
        
        # 添加新记录
        data["actions"].append({
            "action": action,
            "files": files_modified,
            "timestamp": datetime.now().isoformat()
        })
        
        # 写回 JSON
        json_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        
        # 生成 Markdown（可选）
        self._generate_markdown_from_json(json_file)
```

**收益**：
- 更高效的更新
- 更容易解析
- 支持复杂查询

### 6. 监控和诊断优化 ⭐⭐

#### 6.1 性能监控
**问题**：不知道规划功能的性能影响

**方案**：
```python
import time
from functools import wraps

def monitor_performance(func):
    """性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{func.__name__} 执行时间: {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} 执行失败，耗时: {duration:.3f}s, 错误: {str(e)}")
            raise
    return wrapper
```

**收益**：
- 了解性能瓶颈
- 优化依据
- 问题诊断

#### 6.2 统计信息
**问题**：缺少使用统计

**方案**：
```python
class PlanningManager:
    def __init__(self, ...):
        self.stats = {
            "files_created": 0,
            "updates_count": 0,
            "errors_count": 0,
            "total_size": 0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "files_count": len(list(self.work_dir.glob("*_*.md"))),
            "total_size_mb": sum(f.stat().st_size for f in self.work_dir.glob("*_*.md")) / 1024 / 1024
        }
```

**收益**：
- 了解使用情况
- 优化依据
- 问题诊断

## 优化优先级

### 高优先级（立即实施）
1. ⭐⭐⭐⭐⭐ **异步文件更新** - 提升性能，不阻塞主流程
2. ⭐⭐⭐⭐⭐ **文件缓存机制** - 减少 I/O 操作
3. ⭐⭐⭐⭐ **自动清理机制** - 避免文件积累

### 中优先级（近期实施）
4. ⭐⭐⭐⭐ **LLM 辅助判断** - 提升判断准确性
5. ⭐⭐⭐ **文件锁机制** - 保证并发安全
6. ⭐⭐⭐ **批量更新机制** - 减少写入次数

### 低优先级（长期优化）
7. ⭐⭐ **结构化存储** - 提升更新效率
8. ⭐⭐ **性能监控** - 了解性能影响
9. ⭐ **文件压缩** - 节省空间

## 实施建议

### 第一阶段：性能优化（1-2天）
- 实现异步文件更新
- 添加文件缓存机制
- 实现批量更新

### 第二阶段：文件管理（1天）
- 实现自动清理机制
- 添加文件大小限制
- 实现文件压缩

### 第三阶段：智能优化（2-3天）
- 实现 LLM 辅助判断
- 添加判断结果缓存
- 优化复杂度判断算法

### 第四阶段：稳定性和监控（1-2天）
- 实现文件锁机制
- 添加重试机制
- 实现性能监控

## 注意事项

1. **向后兼容**：优化时保持 API 兼容
2. **渐进式优化**：逐步实施，避免大改动
3. **测试覆盖**：每次优化都要有测试
4. **性能测试**：优化前后对比性能
5. **用户影响**：优化不应影响用户体验

