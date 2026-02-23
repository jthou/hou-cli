"""任务处理器注册和定义"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from backend.infrastructure.execution.task_worker import get_task_worker

logger = logging.getLogger(__name__)


# 任务类型定义（仅保留有实际实现的类型）
# metadata_schema 支持: type, required, description, placeholder, enum
# enum 格式: [{"value": "xxx", "label": "显示名"}]
TASK_TYPES = {
    "video_download": {
        "name": "视频下载",
        "description": "从 Bilibili、YouTube 等平台下载视频",
        "metadata_schema": {
            "url": {
                "type": "string",
                "required": True,
                "description": "视频链接",
                "placeholder": "如：https://www.bilibili.com/video/BVxxx 或 b23.tv/xxx"
            },
            "quality": {
                "type": "string",
                "required": False,
                "description": "视频质量",
                "enum": [
                    {"value": "best", "label": "最佳"},
                    {"value": "1080p", "label": "1080p"},
                    {"value": "720p", "label": "720p"},
                    {"value": "480p", "label": "480p"}
                ],
                "default": "best"
            },
            "download_subtitle": {"type": "boolean", "required": False, "description": "下载字幕", "default": False},
            "extract_audio_only": {"type": "boolean", "required": False, "description": "仅提取音频", "default": False},
        }
    },
    "weather_query": {
        "name": "天气查询",
        "description": "查询指定地点的天气预报",
        "metadata_schema": {
            "location": {
                "type": "string",
                "required": True,
                "description": "城市名称",
                "placeholder": "如：北京、上海、深圳"
            },
            "query_type": {
                "type": "string",
                "required": False,
                "description": "查询类型",
                "enum": [
                    {"value": "current", "label": "实时天气"},
                    {"value": "forecast", "label": "天气预报"}
                ],
                "default": "current"
            }
        }
    }
}


async def process_weather_query_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """处理天气查询任务"""
    task_id = task_info["task_id"]
    metadata = task_info.get("metadata", {})
    worker = get_task_worker()

    location = (metadata.get("location") or "").strip()
    query_type = metadata.get("query_type", "current")

    if not location:
        raise ValueError("location 参数是必需的")

    worker.update_task_progress(10, f"开始查询 {location} 的天气...")

    try:
        from backend.core.agent.tools.auth.jwt_auth import JWTAuth, JWTAuthError
        from backend.core.agent.tools.builtin.weather_tool import WeatherTool

        try:
            jwt_auth = JWTAuth.from_env()
            weather_tool = WeatherTool(jwt_auth=jwt_auth)
        except JWTAuthError as e:
            raise ValueError(f"天气工具初始化失败: {str(e)}")
        except Exception as e:
            raise ValueError(f"天气工具初始化失败: {str(e)}")

        worker.update_task_progress(30, "正在获取天气数据...")

        if query_type == "forecast":
            result = weather_tool.get_forecast(location)
            weather_data = result
        else:
            result = weather_tool.get_current_weather(location)
            weather_data = result

        worker.update_task_progress(80, "天气数据获取成功")

        if query_type == "forecast":
            formatted_result = {
                "location": location,
                "query_type": "forecast",
                "forecast": weather_data
            }
        else:
            cur = (weather_data.get("now") if isinstance(weather_data, dict) and "now" in weather_data else weather_data) or {}
            if not isinstance(cur, dict):
                cur = weather_data
            formatted_result = {
                "location": location,
                "query_type": "current",
                "current_weather": cur
            }

        worker.update_task_progress(100, f"{location} 天气查询完成")

        # 统一结果格式：summary 供列表/摘要展示，result 供详情展示
        if query_type == "forecast":
            summary = f"{location} 天气预报"
        else:
            cur = (weather_data.get("now") if isinstance(weather_data, dict) and "now" in weather_data else weather_data) or {}
            if not isinstance(cur, dict):
                cur = {}
            summary = f"{location} {cur.get('text', '')} {cur.get('temp', '')}°C".strip() or f"{location} 天气查询完成"
        return {
            "status": "success",
            "summary": summary,
            "location": location,
            "query_type": query_type,
            "result": formatted_result
        }
    except Exception as e:
        error_msg = f"天气查询失败: {str(e)}"
        worker.update_task_progress(100, error_msg)
        raise Exception(error_msg)


async def process_video_download_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """处理视频下载任务"""
    task_id = task_info["task_id"]
    metadata = task_info.get("metadata", {})
    worker = get_task_worker()

    url = (metadata.get("url") or "").strip()
    if not url:
        raise ValueError("url 参数是必需的")

    worker.update_task_progress(5, "准备下载...")

    def _run_download():
        from backend.core.agent.tools.builtin.video_downloader_tool import (
            VideoDownloaderTool,
            normalize_output_dir,
        )
        tool = VideoDownloaderTool()
        output_dir = normalize_output_dir(metadata.get("output_dir"))
        opts = {
            "quality": metadata.get("quality", "best"),
            "download_subtitle": metadata.get("download_subtitle", False),
            "download_thumbnail": metadata.get("download_thumbnail", False),
            "extract_audio_only": metadata.get("extract_audio_only", False),
        }
        if metadata.get("preferred_tool"):
            opts["preferred_tool"] = metadata["preferred_tool"]

        def on_progress(pct, msg):
            try:
                worker.update_task_progress(pct or 0, msg or "")
            except Exception:
                pass

        tool.progress_callback = on_progress
        result = tool.execute(url=url, output_dir=output_dir, **opts)
        return result

    try:
        result = await asyncio.to_thread(_run_download)
        if result.success:
            worker.update_task_progress(100, "下载完成")
            data = result.data or {}
            output_dir = data.get("output_dir", "")
            title = data.get("title", "")
            summary = f"已保存至 {output_dir}" if output_dir else (title or "下载完成")
            if title and output_dir:
                summary = f"{title} → {output_dir}"
            return {
                "status": "success",
                "summary": summary,
                "data": data
            }
        raise Exception(result.error or "下载失败")
    except Exception as e:
        worker.update_task_progress(100, str(e))
        raise


def register_default_handlers():
    """注册默认的任务处理器"""
    worker = get_task_worker()
    worker.register_handler("video_download", process_video_download_task)
    worker.register_handler("weather_query", process_weather_query_task)
    logger.info(f"已注册 {len(worker.task_handlers)} 个任务处理器")


def get_available_task_types() -> List[Dict[str, Any]]:
    """获取可用的任务类型列表"""
    return [
        {
            "type": task_type,
            "name": info["name"],
            "description": info["description"],
            "metadata_schema": info["metadata_schema"]
        }
        for task_type, info in TASK_TYPES.items()
    ]


def get_task_type_info(task_type: str) -> Dict[str, Any]:
    """获取特定任务类型的信息"""
    if task_type not in TASK_TYPES:
        return None

    info = TASK_TYPES[task_type]
    return {
        "type": task_type,
        "name": info["name"],
        "description": info["description"],
        "metadata_schema": info["metadata_schema"]
    }


def validate_task_creation(task_type: str, metadata: Any) -> Tuple[bool, Optional[str]]:
    """
    校验任务创建参数：task_type 白名单 + metadata 按 metadata_schema 校验。
    供 API 创建任务时调用，与「任务管理验证规范」一致。

    Returns:
        (True, None) 校验通过；(False, "错误描述") 校验失败。
    """
    metadata = metadata if isinstance(metadata, dict) else {}
    if task_type not in TASK_TYPES:
        return False, f"无效的任务类型: {task_type}，可选: {', '.join(TASK_TYPES.keys())}"

    schema = TASK_TYPES[task_type].get("metadata_schema") or {}
    for field_name, field_spec in schema.items():
        if not isinstance(field_spec, dict):
            continue
        required = field_spec.get("required", False)
        value = metadata.get(field_name)
        if required:
            if value is None:
                return False, f"缺少必填参数: {field_name}"
            if isinstance(value, str) and not value.strip():
                return False, f"必填参数不能为空: {field_name}"
        if value is not None and field_spec.get("enum"):
            allowed = [e.get("value") for e in field_spec["enum"] if isinstance(e, dict) and "value" in e]
            if allowed and value not in allowed:
                return False, f"参数 {field_name} 取值无效，可选: {allowed}"
    return True, None
