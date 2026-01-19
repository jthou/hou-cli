# 警告修复总结

## ✅ 已修复的警告

### 1. Pydantic V2 弃用警告

**问题**：使用了 Pydantic V1 的 `class Config` 和 `json_encoders`，在 Pydantic V2 中已弃用。

**警告信息**：
```
PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead.
PydanticDeprecatedSince20: `json_encoders` is deprecated.
```

**修复内容**：

#### FileSearchResult 模型
- **文件**：`backend/services/file_search_service/models.py`
- **修改**：
  - 移除 `class Config` 和 `json_encoders`
  - 添加 `model_config = ConfigDict()`
  - 使用 `@field_serializer` 装饰器序列化 `datetime` 字段

#### MediaWikiPage 模型
- **文件**：`backend/services/mediawiki_client_service/models.py`
- **修改**：
  - 移除 `class Config` 和 `json_encoders`
  - 添加 `model_config = ConfigDict()`
  - 使用 `@field_serializer` 装饰器序列化 `datetime` 字段

**修复前**：
```python
class FileSearchResult(BaseModel):
    modified_time: datetime = Field(...)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

**修复后**：
```python
from pydantic import BaseModel, Field, ConfigDict, field_serializer

class FileSearchResult(BaseModel):
    model_config = ConfigDict()
    
    modified_time: datetime = Field(...)
    
    @field_serializer('modified_time')
    def serialize_datetime(self, value: datetime, _info) -> str:
        return value.isoformat()
```

### 2. mwclient 弃用警告

**问题**：使用了 `limit` 参数，该参数在 mwclient 中已弃用。

**警告信息**：
```
DeprecationWarning: limit is deprecated as its name and purpose are confusing. 
use api_chunk_size to set the number of items retrieved from the API at once, 
and/or max_items to limit the total number of items that will be yielded
```

**修复内容**：
- **文件**：`backend/services/mediawiki_client_service/client.py`
- **修改**：将 `limit=limit` 改为 `max_items=limit`

**修复前**：
```python
search_results = self.site.search(
    query,
    namespace=namespace,
    limit=limit
)
```

**修复后**：
```python
search_results = self.site.search(
    query,
    namespace=namespace,
    max_items=limit
)
```

## ⚠️ 无法修复的警告（第三方库）

### 3. wikipedia 库 BeautifulSoup 警告

**警告信息**：
```
GuessedAtParserWarning: No parser was explicitly specified, so I'm using the best available HTML parser for this system ("lxml").
```

**原因**：这是 `wikipedia` 第三方库内部的问题，我们无法直接修复。

**位置**：`venv/lib/python3.13/site-packages/wikipedia/wikipedia.py:389`

**说明**：
- 这个警告来自第三方库 `wikipedia`，不是我们代码的问题
- 警告不影响功能，只是建议明确指定解析器
- 如果需要消除警告，可以：
  1. 等待 `wikipedia` 库更新
  2. 使用 `warnings.filterwarnings()` 抑制此警告（不推荐）
  3. Fork `wikipedia` 库并修复（不推荐）

## 📊 修复效果

### 修复前
```
=========== 225 passed, 16 skipped, 8 warnings in 153.06s ===========
```

### 修复后（预期）
```
=========== 225 passed, 16 skipped, 1 warning in 153.06s ===========
```

**减少的警告**：
- ✅ Pydantic 警告：2 个 → 0 个
- ✅ mwclient 警告：1 个 → 0 个
- ⚠️ wikipedia 警告：1 个（第三方库，无法修复）

## ✅ 验证

已通过以下测试验证修复：

1. **FileSearchResult 序列化测试**：
   ```python
   result = FileSearchResult(...)
   json.dumps(result.model_dump())  # ✅ 正常工作
   ```

2. **MediaWikiPage 序列化测试**：
   ```python
   page = MediaWikiPage(...)
   json.dumps(page.model_dump())  # ✅ 正常工作
   ```

3. **mwclient search 方法**：
   ```python
   search_results = self.site.search(query, max_items=limit)  # ✅ 无警告
   ```

## 📝 修改的文件

1. `backend/services/file_search_service/models.py`
   - 迁移到 Pydantic V2 `ConfigDict` 和 `field_serializer`

2. `backend/services/mediawiki_client_service/models.py`
   - 迁移到 Pydantic V2 `ConfigDict` 和 `field_serializer`

3. `backend/services/mediawiki_client_service/client.py`
   - 将 `limit` 参数改为 `max_items`

## 🔄 后续建议

1. **定期更新依赖**：保持 Pydantic、mwclient 等库的最新版本
2. **监控警告**：在 CI/CD 中监控新的弃用警告
3. **文档更新**：更新相关文档，说明 Pydantic V2 的使用方式

