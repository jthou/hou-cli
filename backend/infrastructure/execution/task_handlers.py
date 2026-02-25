"""任务处理器注册和定义"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
import ipaddress

from backend.infrastructure.execution.task_worker import get_task_worker

logger = logging.getLogger(__name__)


def _validate_video_download_url(url: str) -> Tuple[bool, Optional[str]]:
    """校验视频下载 URL：仅允许 http(s)，禁止内网/本地地址以降低 SSRF 风险。

    Returns:
        (True, None) 通过；(False, "错误说明") 不通过。
    """
    url = (url or "").strip()
    if not url:
        return False, "URL 不能为空"
    if not url.startswith(("http://", "https://")):
        return False, "仅支持 http 或 https 链接，请填写完整链接（如 https://...）"
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"URL 格式无效: {e}"
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False, "URL 缺少主机名"
    # 禁止本地/内网主机名
    if host in ("localhost", "localhost.", "0.0.0.0") or host.endswith(".localhost"):
        return False, "不允许使用本地地址"
    # 若为 IP，禁止环回与私网
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_loopback or addr.is_private or addr.is_reserved or addr.is_link_local:
            return False, "不允许使用内网或保留地址"
    except ValueError:
        pass  # 非 IP 则仅做主机名检查
    return True, None


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
                    {"value": "480p", "label": "480p"},
                    {"value": "360p", "label": "360p"}
                ],
                "default": "best"
            },
            "download_subtitle": {"type": "boolean", "required": False, "description": "下载字幕", "default": False},
            "extract_audio_only": {"type": "boolean", "required": False, "description": "仅提取音频", "default": False},
            "output_dir": {
                "type": "string",
                "required": False,
                "description": "保存目录（须在用户主目录下，否则使用默认下载目录）",
                "placeholder": "留空使用默认"
            },
            "preferred_tool": {
                "type": "string",
                "required": False,
                "description": "优先使用的下载工具",
                "default": "auto",
                "enum": [
                    {"value": "auto", "label": "自动"},
                    {"value": "yt-dlp", "label": "yt-dlp"},
                    {"value": "you-get", "label": "you-get"}
                ]
            },
            "download_thumbnail": {"type": "boolean", "required": False, "description": "下载封面", "default": False},
            "cookies_file": {
                "type": "string",
                "required": False,
                "description": "Cookies 文件路径（Netscape 或 JSON）",
                "placeholder": "用于需登录的视频"
            },
            "cookies_from_browser": {
                "type": "string",
                "required": False,
                "description": "从浏览器提取 Cookies",
                "enum": [
                    {"value": "chrome", "label": "Chrome"},
                    {"value": "firefox", "label": "Firefox"},
                    {"value": "safari", "label": "Safari"},
                    {"value": "edge", "label": "Edge"}
                ]
            },
            "subtitle_languages": {
                "type": "string",
                "required": False,
                "description": "字幕语言代码，逗号分隔",
                "placeholder": "如：zh,en"
            },
            "download_subtitle_only": {"type": "boolean", "required": False, "description": "仅下载字幕不下载视频", "default": False},
            "audio_format": {
                "type": "string",
                "required": False,
                "description": "仅提取音频时的格式（extract_audio_only 为 true 时有效）",
                "default": "mp3",
                "enum": [
                    {"value": "mp3", "label": "MP3"},
                    {"value": "m4a", "label": "M4A"},
                    {"value": "opus", "label": "Opus"},
                    {"value": "wav", "label": "WAV"},
                    {"value": "aac", "label": "AAC"}
                ]
            },
            "audio_quality": {
                "type": "string",
                "required": False,
                "description": "仅提取音频时的码率",
                "default": "192k",
                "enum": [
                    {"value": "128k", "label": "128k"},
                    {"value": "192k", "label": "192k"},
                    {"value": "256k", "label": "256k"},
                    {"value": "320k", "label": "320k"}
                ]
            },
            "download_danmaku": {"type": "boolean", "required": False, "description": "下载 B 站弹幕（ASS）", "default": False},
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
                    {"value": "forecast", "label": "天气预报"},
                    {"value": "warning", "label": "仅查预警"},
                    {"value": "air_quality", "label": "仅查空气质量"}
                ],
                "default": "current"
            },
            "include_warning": {
                "type": "boolean",
                "required": False,
                "description": "实时/预报时是否同时拉取预警",
                "default": False
            },
            "include_air_quality": {
                "type": "boolean",
                "required": False,
                "description": "实时/预报时是否同时拉取空气质量",
                "default": False
            },
            "days": {
                "type": "number",
                "required": False,
                "description": "预报天数（仅预报时有效）",
                "enum": [
                    {"value": 3, "label": "3 天"},
                    {"value": 7, "label": "7 天"},
                    {"value": 15, "label": "15 天"}
                ],
                "default": 7
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
    days = metadata.get("days")
    if days is not None:
        try:
            days = int(days)
            if days not in (3, 7, 15):
                days = 7
        except (TypeError, ValueError):
            days = 7
    else:
        days = 7

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

        include_warning = metadata.get("include_warning") in (True, "true", "1", 1)
        include_air_quality = metadata.get("include_air_quality") in (True, "true", "1", 1)

        if query_type == "warning":
            warning_data = weather_tool.get_warning(location)
            warning_list = (warning_data.get("warning") or []) if isinstance(warning_data, dict) else []
            formatted_result = {
                "location": location,
                "query_type": "warning",
                "update_time": warning_data.get("updateTime") if isinstance(warning_data, dict) else None,
                "warning": warning_list,
            }
            summary = f"{location} {len(warning_list)} 条预警" if warning_list else f"{location} 暂无预警"
            worker.update_task_progress(100, f"{location} 预警查询完成")
            return {"status": "success", "summary": summary, "location": location, "query_type": query_type, "result": formatted_result}

        if query_type == "air_quality":
            air_data = weather_tool.get_air_quality(location)
            now_air = (air_data.get("now") or {}) if isinstance(air_data, dict) else {}
            formatted_result = {
                "location": location,
                "query_type": "air_quality",
                "update_time": air_data.get("updateTime") if isinstance(air_data, dict) else None,
                "air_quality": now_air,
            }
            aqi = now_air.get("aqi") or ""
            category = now_air.get("category", "")
            summary = f"{location} AQI {aqi} {category}".strip() or f"{location} 空气质量查询完成"
            worker.update_task_progress(100, f"{location} 空气质量查询完成")
            return {"status": "success", "summary": summary, "location": location, "query_type": query_type, "result": formatted_result}

        if query_type == "forecast":
            result = weather_tool.get_forecast(location, days=days)
            weather_data = result
        else:
            result = weather_tool.get_current_weather(location)
            weather_data = result

        worker.update_task_progress(80, "天气数据获取成功")

        if query_type == "forecast":
            daily_raw = (weather_data.get("daily") or []) if isinstance(weather_data, dict) else []
            daily = [
                {
                    "date": d.get("fxDate"),
                    "temp_max": d.get("tempMax"),
                    "temp_min": d.get("tempMin"),
                    "text_day": d.get("textDay"),
                    "text_night": d.get("textNight"),
                    "icon_day": d.get("iconDay"),
                    "icon_night": d.get("iconNight"),
                    "wind_dir_day": d.get("windDirDay"),
                    "wind_scale_day": d.get("windScaleDay"),
                    "humidity": d.get("humidity"),
                    "uv_index": d.get("uvIndex"),
                    "sunrise": d.get("sunrise"),
                    "sunset": d.get("sunset"),
                }
                for d in daily_raw
            ]
            formatted_result = {
                "location": location,
                "query_type": "forecast",
                "update_time": weather_data.get("updateTime") if isinstance(weather_data, dict) else None,
                "daily": daily,
                "raw": weather_data,
            }
        else:
            cur = (weather_data.get("now") if isinstance(weather_data, dict) and "now" in weather_data else weather_data) or {}
            if not isinstance(cur, dict):
                cur = weather_data
            formatted_result = {
                "location": location,
                "query_type": "current",
                "current_weather": cur,
            }

        if include_warning:
            try:
                warning_data = weather_tool.get_warning(location)
                formatted_result["warning"] = (warning_data.get("warning") or []) if isinstance(warning_data, dict) else []
            except Exception:
                formatted_result["warning"] = []
        if include_air_quality:
            try:
                air_data = weather_tool.get_air_quality(location)
                now_air = (air_data.get("now") or {}) if isinstance(air_data, dict) else {}
                formatted_result["air_quality"] = now_air
            except Exception:
                formatted_result["air_quality"] = {}

        worker.update_task_progress(100, f"{location} 天气查询完成")

        if query_type == "forecast":
            daily_raw = (weather_data.get("daily") or []) if isinstance(weather_data, dict) else []
            first = daily_raw[0] if daily_raw else {}
            summary = f"{location} 预报 {len(daily_raw)} 天"
            if first:
                summary = f"{location} {first.get('textDay', '')} {first.get('tempMin', '')}~{first.get('tempMax', '')}°C 等"
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
    ok, err = _validate_video_download_url(url)
    if not ok:
        raise ValueError(err)

    worker.update_task_progress(5, "准备下载...")

    def _run_download():
        from backend.core.agent.tools.builtin.video_downloader_tool import (
            VideoDownloaderTool,
            normalize_output_dir,
        )
        tool = VideoDownloaderTool()
        output_dir = normalize_output_dir(metadata.get("output_dir"), restrict_to_home=True)
        opts = {
            "quality": metadata.get("quality", "best"),
            "download_subtitle": metadata.get("download_subtitle", False),
            "download_thumbnail": metadata.get("download_thumbnail", False),
            "extract_audio_only": metadata.get("extract_audio_only", False),
            "download_subtitle_only": metadata.get("download_subtitle_only", False),
            "download_danmaku": metadata.get("download_danmaku", False),
            "audio_format": metadata.get("audio_format", "mp3"),
            "audio_quality": metadata.get("audio_quality", "192k"),
        }
        if metadata.get("preferred_tool"):
            opts["preferred_tool"] = metadata["preferred_tool"]
        if metadata.get("cookies_file"):
            opts["cookies_file"] = (metadata.get("cookies_file") or "").strip()
        if metadata.get("cookies_from_browser"):
            opts["cookies_from_browser"] = metadata["cookies_from_browser"]
        raw_subs = (metadata.get("subtitle_languages") or "").strip()
        if raw_subs:
            opts["subtitle_languages"] = [s.strip() for s in raw_subs.split(",") if s.strip()]

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
            if allowed:
                compare = value
                if field_name == "days" and compare is not None:
                    try:
                        compare = int(compare)
                    except (TypeError, ValueError):
                        pass
                if compare not in allowed:
                    return False, f"参数 {field_name} 取值无效，可选: {allowed}"
    return True, None
