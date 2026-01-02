# 天气预报工具设计文档

## 1. 概述

本文档描述天气预报工具（Weather Tool）的设计和实现方案。该工具使用和风天气 API 获取天气信息，并通过 JWT 进行安全认证。

## 2. 功能需求

### 2.1 核心功能
- 获取指定城市的实时天气信息
- 获取指定城市的天气预报（未来几天）
- 获取天气预警信息
- 支持城市名称和城市 ID 两种查询方式

### 2.2 安全要求
- 使用 JWT (JSON Web Token) 进行 API 认证
- 私钥存储在 `.env` 文件中（已配置）
- 公钥已存储完成
- 实现安全的 JWT 生成

## 3. 技术方案

### 3.1 API 选择

**和风天气 API 端点：**
- 实时天气：`https://devapi.qweather.com/v7/weather/now`
- 天气预报：`https://devapi.qweather.com/v7/weather/{days}d`
- 天气预警：`https://devapi.qweather.com/v7/warning/now`
- 城市搜索：`https://devapi.qweather.com/v7/city/lookup`

**注意：** 和风天气 API 使用 JWT 认证，不需要 API Key。JWT token 通过 `Authorization: Bearer <jwt_token>` 请求头传递。

### 3.2 JWT 认证设计

#### 3.2.1 JWT Payload 结构
```json
{
  "iss": "hou-cli-weather-tool",  // 发行者
  "iat": 1234567890,              // 签发时间
  "exp": 1234571490,              // 过期时间（1小时后）
  "aud": "qweather-api",          // 受众
  "sub": "weather-query"          // 主题
}
```

**注意：** 和风天气 API 不使用 API Key，仅使用 JWT 认证。
```

#### 3.2.2 JWT 生成流程
1. 从环境变量 `WEATHER_JWT_PRIVATE_KEY` 读取私钥（私钥已配置在 `.env` 文件中）
2. 构建 JWT payload
3. 使用 RS256 算法签名生成 JWT
4. 将 JWT 添加到 HTTP 请求头：`Authorization: Bearer <jwt_token>`

**注意：** 私钥和公钥已配置完成，无需额外配置。

### 3.3 工具接口设计

#### 3.3.1 Tool 定义
```python
@tool(
    name="get_weather",
    description="获取指定城市的实时天气信息",
    parameters={
        "location": {
            "type": "string",
            "description": "城市名称或城市ID，例如：'北京' 或 '101010100'",
            "required": True
        },
        "days": {
            "type": "integer",
            "description": "预报天数（1-15），默认1",
            "required": False,
            "default": 1
        }
    }
)
def get_weather(location: str, days: int = 1) -> Dict[str, Any]:
    """获取天气信息"""
    pass
```

#### 3.3.2 返回数据结构
```python
{
    "success": True,
    "data": {
        "location": "北京",
        "current": {
            "temp": "25",
            "text": "晴",
            "windDir": "东北风",
            "windScale": "3级",
            "humidity": "45%",
            "pressure": "1013",
            "vis": "16"
        },
        "forecast": [...],  # 未来几天预报
        "warning": [...]   # 预警信息（如果有）
    },
    "error": None
}
```

## 4. 实现细节

### 4.1 目录结构
```
backend/core/agent/tools/
├── builtin/
│   └── weather_tool.py      # 天气预报工具实现
├── auth/
│   ├── __init__.py
│   └── jwt_auth.py          # JWT 认证工具类
└── utils/
    └── key_loader.py        # 私钥加载工具
```

### 4.2 核心组件

#### 4.2.1 JWT 认证类 (`auth/jwt_auth.py`)
```python
class JWTAuth:
    """JWT 认证工具类"""
    
    def __init__(self):
        """初始化，从环境变量加载私钥"""
        pass
    
    def generate_token(self, payload: Dict[str, Any]) -> str:
        """生成 JWT token"""
        pass
    
    def _load_private_key(self) -> bytes:
        """从环境变量加载私钥"""
        pass
```

#### 4.2.2 私钥加载工具 (`utils/key_loader.py`)
```python
class KeyLoader:
    """私钥加载工具"""
    
    @staticmethod
    def load_private_key_from_env() -> bytes:
        """从环境变量加载私钥（私钥已配置在 .env 文件中）"""
        pass
    
    @staticmethod
    def normalize_private_key(key: str) -> str:
        """规范化私钥格式（处理换行符等）"""
        pass
```

#### 4.2.3 天气工具 (`builtin/weather_tool.py`)
```python
class WeatherTool:
    """天气预报工具"""
    
    def __init__(self, jwt_auth: JWTAuth, api_base_url: str = None):
        """初始化天气工具"""
        pass
    
    def get_current_weather(self, location: str) -> Dict[str, Any]:
        """获取实时天气"""
        pass
    
    def get_forecast(self, location: str, days: int = 7) -> Dict[str, Any]:
        """获取天气预报"""
        pass
    
    def get_warning(self, location: str) -> Dict[str, Any]:
        """获取天气预警"""
        pass
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送 API 请求（带 JWT 认证）"""
        pass
```

### 4.3 配置管理

#### 4.3.1 环境变量
```bash
# JWT 私钥路径（可选，默认 ~/.ssh/weather_jwt_private_key.pem）
WEATHER_JWT_PRIVATE_KEY_PATH=~/.ssh/weather_jwt_private_key.pem

# 和风天气 API 基础 URL
QWEATHER_API_BASE_URL=https://devapi.qweather.com

# 和风天气 API Key（如果需要）
QWEATHER_API_KEY=your-api-key

# JWT 过期时间（秒，默认 3600）
WEATHER_JWT_EXPIRES_IN=3600
```

#### 4.3.2 配置文件（可选）
```yaml
# config/weather.yaml
weather:
  jwt:
    private_key_path: ~/.ssh/weather_jwt_private_key.pem
    expires_in: 3600
  api:
    base_url: https://devapi.qweather.com
    api_key: your-api-key
```

## 5. 错误处理

### 5.1 错误类型
1. **私钥环境变量未设置**
   - 错误码：`PRIVATE_KEY_NOT_SET`
   - 处理：提示用户检查 `.env` 文件中的 `WEATHER_JWT_PRIVATE_KEY` 配置

2. **JWT 生成失败**
   - 错误码：`JWT_GENERATION_FAILED`
   - 处理：记录错误日志，返回通用错误信息

4. **API 请求失败**
   - 错误码：`API_REQUEST_FAILED`
   - 处理：重试机制（最多 3 次），记录错误日志

5. **城市未找到**
   - 错误码：`LOCATION_NOT_FOUND`
   - 处理：返回友好的错误提示，建议使用城市 ID

### 5.2 重试策略
- 网络错误：最多重试 3 次，指数退避（1s, 2s, 4s）
- 认证错误：不重试，直接返回错误
- 限流错误（429）：等待后重试

## 6. 安全考虑

### 6.1 私钥安全
- 私钥已配置在 `.env` 文件中，不应提交到版本控制系统
- `.env` 文件应添加到 `.gitignore`
- 公钥已存储完成

### 6.2 JWT 安全
- JWT 设置合理的过期时间（默认 1 小时）
- 使用 RS256 算法（非对称加密）
- 不在日志中输出完整的 JWT token

### 6.3 API 安全
- 使用 HTTPS 传输
- 不在错误信息中暴露 JWT token
- 实现请求频率限制

## 7. 测试策略

### 7.1 单元测试
- JWT 生成和验证
- 私钥加载和权限验证
- API 请求和响应解析
- 错误处理逻辑

### 7.2 集成测试
- 端到端天气查询流程
- 错误场景测试
- 重试机制测试

### 7.3 Mock 测试
- 使用 Mock 服务器模拟和风天气 API
- 测试各种错误响应场景

## 8. 待确认信息

### 8.1 需要确认的问题
1. **JWT Payload：** 具体的 payload 结构是什么？需要包含哪些字段？（iss, aud, sub 等字段的具体值）
2. **城市 ID：** 如何获取城市 ID？是否需要实现城市搜索功能？

**注意：** 私钥和公钥已配置完成，无需额外配置。

### 8.2 建议的默认值
- 私钥来源：环境变量 `WEATHER_JWT_PRIVATE_KEY`（已配置在 `.env` 文件中）
- JWT 算法：`RS256`
- JWT 过期时间：`3600` 秒（1 小时）
- API 基础 URL：`https://devapi.qweather.com`
- 默认预报天数：`7` 天

## 9. 后续扩展

### 9.1 功能扩展
- 支持更多天气数据（空气质量、生活指数等）
- 支持批量查询多个城市
- 支持天气数据缓存（减少 API 调用）
- 支持天气数据历史记录

### 9.2 性能优化
- 实现请求缓存（相同城市短时间内不重复请求）
- 实现异步请求（批量查询时）
- 实现连接池（减少连接开销）

## 10. 参考资料

- [和风天气 API 文档](https://dev.qweather.com/docs/)
- [JWT 规范 (RFC 7519)](https://tools.ietf.org/html/rfc7519)
- [Python JWT 库 (PyJWT)](https://pyjwt.readthedocs.io/)

