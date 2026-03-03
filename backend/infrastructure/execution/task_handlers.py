"""任务处理器注册和定义"""
import asyncio
import logging
import os
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
import ipaddress

from backend.infrastructure.execution.task_worker import get_task_worker
from backend.infrastructure.storage.task_queue_db import get_task_queue_db, TaskStatus

logger = logging.getLogger(__name__)


def _err(code: str, summary: str, message: str, details: Optional[str] = None) -> Dict[str, Any]:
    """统一错误返回结构（设计 doc 2.5 节）。"""
    return {
        "status": "error",
        "summary": summary,
        "error": {"code": code, "message": message, "details": details or ""},
    }


def _validate_input_path_in_home(input_path: Path) -> Tuple[bool, Optional[str]]:
    """校验输入路径存在且位于用户主目录下。Returns: (True, None) 通过；(False, "错误说明") 不通过。"""
    if not input_path.exists():
        return False, f"指定的文件不存在: {input_path}"
    if not input_path.is_file():
        return False, "路径必须是文件"
    try:
        input_path.resolve().relative_to(Path.home().resolve())
    except ValueError:
        return False, "输入路径必须在用户主目录下"
    return True, None


def _validate_output_path_in_home(output_path: Path) -> Tuple[bool, Optional[str]]:
    """校验输出路径（或父目录）在用户主目录下。"""
    try:
        output_path.resolve().relative_to(Path.home().resolve())
    except ValueError:
        return False, "输出路径必须在用户主目录下"
    return True, None


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
                "description": "保存目录（须在用户主目录下，不填则使用 ~/hou-cli/outputs）",
                "placeholder": "留空使用 ~/hou-cli/outputs"
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
        },
        "pipeline_outputs": [
            {"path": "result.data.output_file", "type": "file", "format": "audio", "description": "输出音频文件路径（仅当 extract_audio_only 为 true 时有效）"},
            {"path": "result.data.output_file", "type": "file", "format": "video", "description": "输出视频文件路径（完整下载时有效）"}
        ],
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
            "fetch_current": {
                "type": "boolean",
                "required": False,
                "description": "实时天气",
                "default": True
            },
            "fetch_forecast": {
                "type": "boolean",
                "required": False,
                "description": "天气预报",
                "default": True
            },
            "fetch_warning": {
                "type": "boolean",
                "required": False,
                "description": "预警",
                "default": True
            },
            "fetch_air_quality": {
                "type": "boolean",
                "required": False,
                "description": "空气质量",
                "default": True
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
    },
    "web_search": {
        "name": "网页搜索",
        "description": "使用 DuckDuckGo 执行关键词搜索，可定时执行",
        "metadata_schema": {
            "query": {
                "type": "string",
                "required": True,
                "description": "搜索关键词或语句",
                "placeholder": "如：伊朗和美国战争的最新情况"
            },
            "num_results": {
                "type": "number",
                "required": False,
                "description": "返回结果数量（可设置，建议 1–100，默认 10）",
                "default": 10
            },
            "language": {
                "type": "string",
                "required": False,
                "description": "语言代码（可选）",
                "placeholder": "zh-CN, en"
            }
        }
    },
    "speech_to_text": {
        "name": "语音转文字",
        "description": "使用 Whisper 将音频文件转成文字或字幕（支持 json/text/srt）",
        "pipeline_outputs": [
            {"path": "result.data.output_file", "type": "file", "format": "text", "description": "输出字幕/文本文件路径"}
        ],
        "metadata_schema": {
            "input_file": {
                "type": "string",
                "required": True,
                "description": "音频文件路径（支持 mp3, wav, m4a, flac 等）",
                "placeholder": "如：/Users/xx/audio.mp3",
                "pipeline_accept": {"type": "file", "formats": ["audio"]}
            },
            "language": {
                "type": "string",
                "required": False,
                "description": "语言代码，auto 为自动检测",
                "default": "auto",
                "placeholder": "zh, en, ja"
            },
            "model": {
                "type": "string",
                "required": False,
                "description": "Whisper 模型大小",
                "default": "base",
                "enum": [
                    {"value": "tiny", "label": "Tiny"},
                    {"value": "base", "label": "Base"},
                    {"value": "small", "label": "Small"},
                    {"value": "medium", "label": "Medium"},
                    {"value": "large", "label": "Large"}
                ]
            },
            "output_format": {
                "type": "string",
                "required": False,
                "description": "输出格式",
                "default": "srt",
                "enum": [
                    {"value": "json", "label": "JSON"},
                    {"value": "text", "label": "纯文本"},
                    {"value": "srt", "label": "字幕 SRT"}
                ]
            },
            "output_file": {
                "type": "string",
                "required": False,
                "description": "输出文件路径；不填则自动生成到 ~/hou-cli/outputs",
                "placeholder": "如：/Users/xx/out.srt"
            },
            "output_dir": {
                "type": "string",
                "required": False,
                "description": "输出目录（仅当未指定 output_file 时生效），不填则使用 ~/hou-cli/outputs",
                "placeholder": "留空使用 ~/hou-cli/outputs"
            },
        }
    },
    "video_extract_audio": {
        "name": "视频提取音频",
        "description": "从本地视频文件中提取音频轨并保存为音频文件",
        "pipeline_outputs": [
            {"path": "result.data.output_file", "type": "file", "format": "audio", "description": "输出音频文件路径"}
        ],
        "metadata_schema": {
            "input_file": {
                "type": "string",
                "required": True,
                "description": "本地视频文件路径",
                "placeholder": "如：/Users/xx/video.mp4",
                "pipeline_accept": {"type": "file", "formats": ["video"]}
            },
            "output_file": {
                "type": "string",
                "required": False,
                "description": "输出音频文件路径；不填则自动生成到 ~/hou-cli/outputs",
                "placeholder": "如：/Users/xx/audio.mp3"
            },
            "output_dir": {
                "type": "string",
                "required": False,
                "description": "输出目录（仅当未指定 output_file 时生效），不填则使用 ~/hou-cli/outputs",
                "placeholder": "留空使用 ~/hou-cli/outputs"
            },
            "audio_format": {
                "type": "string",
                "required": False,
                "description": "音频格式",
                "default": "mp3",
                "enum": [
                    {"value": "mp3", "label": "MP3"},
                    {"value": "wav", "label": "WAV"},
                    {"value": "aac", "label": "AAC"},
                    {"value": "flac", "label": "FLAC"},
                    {"value": "ogg", "label": "OGG"}
                ]
            },
            "audio_quality": {
                "type": "string",
                "required": False,
                "description": "音频码率",
                "default": "192k",
                "enum": [
                    {"value": "128k", "label": "128k"},
                    {"value": "192k", "label": "192k"},
                    {"value": "256k", "label": "256k"},
                    {"value": "320k", "label": "320k"}
                ]
            },
        }
    },
    "mediawiki_write": {
        "name": "MediaWiki 写入",
        "description": "向 MediaWiki 编辑或创建页面（wikitext 格式）",
        "metadata_schema": {
            "title": {
                "type": "string",
                "required": True,
                "description": "页面标题",
                "placeholder": "如：我的笔记/2025-02"
            },
            "content": {
                "type": "string",
                "required": False,
                "description": "页面内容（wikitext）；与 content_file 二选一",
                "placeholder": "支持 Wiki 语法、链接、分类等"
            },
            "content_file": {
                "type": "string",
                "required": False,
                "description": "本地文本文件路径（与 content 二选一，填写则从该文件读取内容）",
                "placeholder": "如：/Users/xx/note.txt",
                "pipeline_accept": {"type": "file", "formats": ["text"]}
            },
            "summary": {
                "type": "string",
                "required": False,
                "description": "编辑摘要",
                "placeholder": "留空则使用默认摘要"
            },
            "operation": {
                "type": "string",
                "required": False,
                "description": "操作类型",
                "default": "edit",
                "enum": [
                    {"value": "edit", "label": "编辑（存在则覆盖）"},
                    {"value": "create", "label": "创建（仅当页面不存在时）"}
                ]
            },
        }
    },
    "url_to_wiki": {
        "name": "网文抓取",
        "description": "抓取指定 URL 正文，翻译成中文后生成 Markdown 草稿，可按需写入 MediaWiki",
        "metadata_schema": {
            "url": {
                "type": "string",
                "required": True,
                "description": "要抓取并翻译的文章 URL（仅 http/https）",
                "placeholder": "https://example.com/article"
            },
            "wiki_title": {
                "type": "string",
                "required": False,
                "description": "Wiki 页面标题（留空则从网页 title 或 URL 推断；若 URL 为哈希/随机路径，建议填写可读标题）",
                "placeholder": "如：文章标题，留空则用网页标题或 URL 推断"
            },
            "language": {
                "type": "string",
                "required": False,
                "description": "目标语言；选「不翻译」则保留原文写入 Wiki",
                "default": "zh",
                "enum": [
                    {"value": "zh", "label": "中文"},
                    {"value": "en", "label": "英文"},
                    {"value": "ja", "label": "日文"},
                    {"value": "original", "label": "不翻译（保留原文）"},
                ]
            },
            "categories": {
                "type": "array",
                "required": False,
                "description": "Wiki 分类",
                "placeholder": "输入标签后回车添加",
                "default": ["网文抓取", "hou-cli"]
            },
            "auto_write": {
                "type": "boolean",
                "required": False,
                "description": "自动写入 MediaWiki（关闭则仅生成 Markdown 草稿）",
                "default": True
            },
        }
    },
    "pdf_to_wiki": {
        "name": "PDF 转 Wiki",
        "description": "从 PDF URL 或本地路径读取，按页拆分、转文字、翻译后写入 MediaWiki；支持大文件分块处理。",
        "metadata_schema": {
            "url": {
                "type": "string",
                "required": False,
                "description": "PDF 的 http(s) URL（与 file_path 二选一）",
                "placeholder": "https://example.com/doc.pdf"
            },
            "file_path": {
                "type": "string",
                "required": False,
                "description": "本地 PDF 路径，须在用户主目录下（与 url 二选一）",
                "placeholder": "~/Downloads/doc.pdf"
            },
            "wiki_title": {
                "type": "string",
                "required": False,
                "description": "Wiki 主页面标题（留空则从 PDF 文件名推断；若链接为哈希/随机文件名，建议填写可读标题）",
                "placeholder": "如：文章标题、书名，留空则用文件名"
            },
            "language": {
                "type": "string",
                "required": False,
                "description": "目标语言；选「不翻译」则保留原文写入 Wiki",
                "default": "zh",
                "enum": [
                    {"value": "zh", "label": "中文"},
                    {"value": "en", "label": "英文"},
                    {"value": "ja", "label": "日文"},
                    {"value": "original", "label": "不翻译（保留原文）"},
                ]
            },
            "categories": {
                "type": "array",
                "required": False,
                "description": "Wiki 分类",
                "default": ["PDF转Wiki", "hou-cli"]
            },
            "wiki_output_mode": {
                "type": "string",
                "required": False,
                "description": "输出模式：单页汇总或目录页+多子页",
                "default": "single",
                "enum": [
                    {"value": "single", "label": "单页汇总"},
                    {"value": "multi", "label": "多子页面（目录页+书名/第k部分）"},
                ]
            },
            "max_pages": {
                "type": "integer",
                "required": False,
                "description": "仅处理前 N 页（不填则用系统上限）",
                "placeholder": "可选"
            },
        }
    },
    "wiki_directory_refresh": {
        "name": "Wiki 目录页刷新",
        "description": "根据任务记录（网文抓取、PDF 转 Wiki）生成并写入一个 Wiki 目录页，列出已写入的页面与来源。",
        "metadata_schema": {
            "wiki_title": {
                "type": "string",
                "required": False,
                "description": "目录页标题（不填则使用「网文与PDF翻译目录」）",
                "placeholder": "网文与PDF翻译目录"
            },
            "limit": {
                "type": "integer",
                "required": False,
                "description": "最多纳入最近 N 条任务记录",
                "default": 300,
                "placeholder": "300"
            },
        }
    },
    "wechat_mp_draft": {
        "name": "公众号草稿",
        "description": "向微信公众号草稿箱新增或更新一篇图文草稿（个人号可用；发布需在手机端「公众号助手」操作）。正文不超过 2 万字、1MB。",
        "metadata_schema": {
            "operation": {
                "type": "string",
                "required": True,
                "description": "操作类型",
                "enum": [
                    {"value": "add", "label": "新增草稿"},
                    {"value": "update", "label": "更新草稿"}
                ],
                "default": "add"
            },
            "title": {
                "type": "string",
                "required": True,
                "description": "标题（不超过 32 字）",
                "placeholder": "文章标题"
            },
            "content": {
                "type": "string",
                "required": True,
                "description": "正文 HTML（不超过 2 万字、1MB）",
                "placeholder": "<p>正文内容...</p>"
            },
            "author": {
                "type": "string",
                "required": False,
                "description": "作者（不超过 16 字）"
            },
            "digest": {
                "type": "string",
                "required": False,
                "description": "摘要（不超过 120 字，超限接口报 45004）"
            },
            "thumb_media_id": {
                "type": "string",
                "required": False,
                "description": "封面图素材 media_id（新增草稿时必填，需先通过上传图文消息内图片接口获取）",
                "placeholder": "永久素材 media_id"
            },
            "content_source_url": {
                "type": "string",
                "required": False,
                "description": "阅读原文链接",
                "placeholder": "https://..."
            },
            "media_id": {
                "type": "string",
                "required": False,
                "description": "要更新的草稿（从当前草稿列表选择，operation=update 时必填，无需手动填写）",
                "placeholder": ""
            },
        }
    },
}


def _to_bool(v) -> bool:
    return v in (True, "true", "1", 1)


async def process_weather_query_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """处理天气查询任务（多选：实时/预报/预警/空气质量可任意组合）"""
    task_id = task_info["task_id"]
    metadata = task_info.get("metadata", {})
    worker = get_task_worker()

    location = (metadata.get("location") or "").strip()
    fetch_current = _to_bool(metadata.get("fetch_current", True))
    fetch_forecast = _to_bool(metadata.get("fetch_forecast", True))
    fetch_warning = _to_bool(metadata.get("fetch_warning", True))
    fetch_air_quality = _to_bool(metadata.get("fetch_air_quality", True))

    # 兼容旧任务：若存在 query_type 则按旧逻辑解析
    query_type = metadata.get("query_type")
    if query_type is not None and str(query_type).strip() != "":
        qt = str(query_type).strip()
        if qt == "warning":
            fetch_current, fetch_forecast, fetch_warning, fetch_air_quality = False, False, True, False
        elif qt == "air_quality":
            fetch_current, fetch_forecast, fetch_warning, fetch_air_quality = False, False, False, True
        else:
            fetch_current = qt == "current"
            fetch_forecast = qt == "forecast"
            fetch_warning = _to_bool(metadata.get("include_warning", True))
            fetch_air_quality = _to_bool(metadata.get("include_air_quality", True))

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

    if not any((fetch_current, fetch_forecast, fetch_warning, fetch_air_quality)):
        raise ValueError("请至少勾选一种查询类型（实时天气、天气预报、预警、空气质量）")

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

        formatted_result = {"location": location}
        summary_parts = []

        # 实时天气
        if fetch_current:
            worker.update_task_progress(30, "正在获取实时天气...")
            weather_data = weather_tool.get_current_weather(location)
            cur = (weather_data.get("now") if isinstance(weather_data, dict) and "now" in weather_data else weather_data) or {}
            if not isinstance(cur, dict):
                cur = weather_data if isinstance(weather_data, dict) else {}
            formatted_result["current_weather"] = cur
            formatted_result["update_time"] = weather_data.get("updateTime") if isinstance(weather_data, dict) else None
            if cur.get("text") or cur.get("temp") is not None:
                summary_parts.append(f"{cur.get('text', '')} {cur.get('temp', '')}°C".strip())

        # 天气预报
        if fetch_forecast:
            worker.update_task_progress(40, "正在获取天气预报...")
            weather_data = weather_tool.get_forecast(location, days=days)
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
            formatted_result["daily"] = daily
            formatted_result["raw"] = weather_data
            if not formatted_result.get("update_time") and isinstance(weather_data, dict):
                formatted_result["update_time"] = weather_data.get("updateTime")
            summary_parts.append(f"预报 {len(daily_raw)} 天")

        # 预警
        if fetch_warning:
            worker.update_task_progress(60, "正在获取预警...")
            try:
                warning_data = weather_tool.get_warning(location)
                warning_list = (warning_data.get("warning") or []) if isinstance(warning_data, dict) else []
                formatted_result["warning"] = warning_list
                if not formatted_result.get("update_time") and isinstance(warning_data, dict):
                    formatted_result["update_time"] = warning_data.get("updateTime")
                summary_parts.append(f"{len(warning_list)} 条预警" if warning_list else "暂无预警")
            except Exception:
                formatted_result["warning"] = []

        # 空气质量
        if fetch_air_quality:
            worker.update_task_progress(80, "正在获取空气质量...")
            try:
                air_data = weather_tool.get_air_quality(location)
                now_air = (air_data.get("now") or {}) if isinstance(air_data, dict) else {}
                formatted_result["air_quality"] = now_air
                if not formatted_result.get("update_time") and isinstance(air_data, dict):
                    formatted_result["update_time"] = air_data.get("updateTime")
                aqi = now_air.get("aqi") or ""
                category = now_air.get("category", "")
                if aqi or category:
                    summary_parts.append(f"AQI {aqi} {category}".strip())
            except Exception:
                formatted_result["air_quality"] = {}

        worker.update_task_progress(100, f"{location} 天气查询完成")
        summary = f"{location} {' '.join(summary_parts)}".strip() or f"{location} 天气查询完成"

        return {
            "status": "success",
            "summary": summary,
            "location": location,
            "result": formatted_result,
        }
    except Exception as e:
        error_msg = f"天气查询失败: {str(e)}"
        worker.update_task_progress(100, error_msg)
        raise Exception(error_msg)


async def process_web_search_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """处理网页搜索任务（DuckDuckGo，可定时执行）"""
    metadata = task_info.get("metadata", {})
    worker = get_task_worker()

    query = (metadata.get("query") or "").strip()
    if not query:
        raise ValueError("query 参数是必需的")

    num_results = metadata.get("num_results", 10)
    try:
        num_results = max(1, min(100, int(num_results)))
    except (TypeError, ValueError):
        num_results = 10
    language = (metadata.get("language") or "").strip() or None

    worker.update_task_progress(10, f"正在搜索: {query[:30]}…")

    try:
        from backend.services.google_search_service.browser_search import (
            search as browser_search,
            BrowserSearchError,
        )
        response = browser_search(
            query=query,
            num_results=num_results,
            language=language,
        )
    except BrowserSearchError as e:
        raise Exception(f"网页搜索失败: {str(e)}")

    worker.update_task_progress(100, f"找到 {len(response.results)} 条结果")

    results = [
        {"title": r.title, "link": r.link, "snippet": r.snippet, "display_link": r.display_link}
        for r in response.results
    ]
    summary = (
        f"找到 {len(results)} 条结果，耗时 {response.search_time:.2f} 秒"
        if response.search_time is not None
        else f"找到 {len(results)} 条结果"
    )

    return {
        "status": "success",
        "summary": summary,
        "query": query,
        "result": {
            "results": results,
            "count": len(results),
            "search_time": response.search_time,
            "query": response.query,
        },
    }


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

        # 适配 Tool.progress_callback 的 (str) -> None：下载器可能调用 (pct, msg) 或 (msg)
        def _cb(a, b=None):
            if b is not None:
                on_progress(a, b)
            else:
                on_progress(0, a or "")
        tool.progress_callback = _cb
        result = tool.execute(url=url, output_dir=output_dir, **opts)
        return result

    try:
        result = await asyncio.to_thread(_run_download)
        if result.success:
            worker.update_task_progress(100, "下载完成")
            data = dict(result.data or {})
            # 管道衔接：若工具未提供 output_file，从 output_dir 推断（you-get 等仅返回 output_dir）
            if not data.get("output_file") and data.get("output_dir"):
                try:
                    from backend.core.agent.tools.builtin.video_downloader_tool import _find_single_output_file
                    out_path = _find_single_output_file(Path(data["output_dir"]))
                    if out_path:
                        data["output_file"] = out_path
                except Exception:
                    pass
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


async def process_speech_to_text_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """处理语音转文字任务。失败时返回统一错误结构（不抛异常）。"""
    metadata = task_info.get("metadata", {})
    worker = get_task_worker()

    input_file = (metadata.get("input_file") or "").strip()
    if not input_file:
        return _err("INPUT_FILE_NOT_FOUND", "缺少输入文件", "input_file 参数是必需的")

    input_path = Path(input_file).expanduser().resolve()
    ok, err_msg = _validate_input_path_in_home(input_path)
    if not ok:
        return _err("INPUT_FILE_NOT_FOUND" if "不存在" in (err_msg or "") else "INPUT_PATH_OUTSIDE_HOME", "输入无效", err_msg or "路径校验失败")

    output_file = (metadata.get("output_file") or "").strip()
    output_dir = (metadata.get("output_dir") or "").strip()
    if output_file:
        out_path = Path(output_file).expanduser().resolve()
        ok_out, err_out = _validate_output_path_in_home(out_path)
        if not ok_out:
            return _err("OUTPUT_PATH_DENIED", "输出路径不允许", err_out or "输出路径须在用户主目录下")
    else:
        from shared.platform_utils import normalize_output_dir
        try:
            out_dir = normalize_output_dir(output_dir or None, restrict_to_home=True)
        except Exception as e:
            return _err("OUTPUT_PATH_DENIED", "输出目录无效", str(e))
        ext = {"json": ".json", "text": ".txt", "srt": ".srt"}.get(metadata.get("output_format", "srt"), ".srt")
        output_file = str(out_dir / f"{input_path.stem}_transcription{ext}")

    worker.update_task_progress(0, "准备转写...")

    def _run_transcribe():
        from backend.core.agent.tools.builtin.whisper_tool import WhisperTool
        tool = WhisperTool()
        if hasattr(tool, "report_progress"):
            def on_progress(message: str) -> None:
                try:
                    worker.update_task_progress(0, message or "转写中...")
                except Exception:
                    pass
            tool.report_progress = on_progress
        language = metadata.get("language") or "auto"
        model = metadata.get("model") or "base"
        output_format = metadata.get("output_format") or "srt"
        kwargs = {"audio_file": str(input_path), "language": language, "model": model, "output_format": output_format}
        if output_file:
            kwargs["output_file"] = output_file
        return tool.execute(**kwargs)

    try:
        result = await asyncio.to_thread(_run_transcribe)
    except ImportError as e:
        return _err("WHISPER_NOT_AVAILABLE", "Whisper 未安装或路径错误", str(e))
    except Exception as e:
        return _err("TRANSCRIPTION_FAILED", "转写失败", str(e), details=traceback.format_exc())

    if not result.success:
        return _err("TRANSCRIPTION_FAILED", "转写失败", result.error or "未知错误")

    worker.update_task_progress(100, "转写完成")
    data = result.data or {}
    summary = data.get("summary") or f"已转写至 {data.get('output_file', '')}"
    return {"status": "success", "summary": summary, "data": data}


async def process_video_extract_audio_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """处理视频提取音频任务。失败时返回统一错误结构（不抛异常）。"""
    metadata = task_info.get("metadata", {})
    worker = get_task_worker()

    input_file = (metadata.get("input_file") or "").strip()
    if not input_file:
        return _err("INPUT_FILE_NOT_FOUND", "缺少输入文件", "input_file 参数是必需的")

    input_path = Path(input_file).expanduser().resolve()
    ok, err_msg = _validate_input_path_in_home(input_path)
    if not ok:
        return _err("INPUT_FILE_NOT_FOUND" if "不存在" in (err_msg or "") else "INPUT_PATH_OUTSIDE_HOME", "输入无效", err_msg or "路径校验失败")

    output_file = (metadata.get("output_file") or "").strip()
    output_dir = (metadata.get("output_dir") or "").strip()
    audio_format = metadata.get("audio_format") or "mp3"
    audio_quality = metadata.get("audio_quality") or "192k"
    ext = {"mp3": ".mp3", "wav": ".wav", "aac": ".aac", "flac": ".flac", "ogg": ".ogg"}.get(audio_format, ".mp3")

    if output_file:
        out_path = Path(output_file).expanduser().resolve()
        ok_out, err_out = _validate_output_path_in_home(out_path)
        if not ok_out:
            return _err("OUTPUT_PATH_DENIED", "输出路径不允许", err_out or "输出路径须在用户主目录下")
    else:
        from shared.platform_utils import normalize_output_dir
        try:
            out_dir = normalize_output_dir(output_dir or None, restrict_to_home=True)
        except Exception as e:
            return _err("OUTPUT_PATH_DENIED", "输出目录无效", str(e))
        output_file = str(out_dir / f"{input_path.stem}{ext}")

    worker.update_task_progress(5, "正在提取音频...")

    def _run_extract():
        from backend.core.agent.tools.builtin.ffmpeg_tool import FFmpegTool
        tool = FFmpegTool()
        return tool.execute(
            operation="extract_audio",
            input_file=str(input_path),
            output_file=output_file,
            audio_format=audio_format,
            audio_quality=audio_quality,
        )

    try:
        result = await asyncio.to_thread(_run_extract)
    except Exception as e:
        return _err("EXTRACT_AUDIO_FAILED", "提取音频失败", str(e), details=traceback.format_exc())

    if not result.success:
        if "未找到" in (result.error or "") or "not found" in (result.error or "").lower():
            return _err("FFMPEG_NOT_FOUND", "FFmpeg 未找到", result.error or "请安装 FFmpeg")
        return _err("EXTRACT_AUDIO_FAILED", "提取音频失败", result.error or "未知错误")

    worker.update_task_progress(100, "提取完成")
    data = result.data or {}
    summary = f"已提取至 {data.get('output_file', output_file)}"
    return {"status": "success", "summary": summary, "data": data}


async def process_mediawiki_write_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """处理 MediaWiki 写入任务（编辑或创建页面）。失败时返回统一错误结构。"""
    metadata = task_info.get("metadata", {})
    worker = get_task_worker()

    title = (metadata.get("title") or "").strip()
    if not title:
        return _err("MISSING_TITLE", "缺少页面标题", "title 参数是必需的")

    content_file = (metadata.get("content_file") or "").strip()
    if content_file:
        # 从本地文件读取内容：路径须在主目录下且为已存在文件
        file_path = Path(content_file).expanduser().resolve()
        ok, err_msg = _validate_input_path_in_home(file_path)
        if not ok:
            return _err("CONTENT_FILE_NOT_FOUND" if "不存在" in (err_msg or "") else "CONTENT_FILE_OUTSIDE_HOME", "内容文件无效", err_msg or "路径须在用户主目录下且为已存在文件")
        try:
            raw = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return _err("CONTENT_FILE_READ_FAILED", "读取文件失败", str(e))
        content = raw.strip()
    else:
        content = metadata.get("content")
        content = str(content).strip() if content is not None else ""
    if not content:
        return _err("MISSING_CONTENT", "缺少页面内容", "请填写 content 或 content_file（本地文本文件路径）")

    summary = (metadata.get("summary") or "").strip() or None
    operation = (metadata.get("operation") or "edit").strip().lower()
    if operation not in ("edit", "create"):
        operation = "edit"

    worker.update_task_progress(5, "正在写入 MediaWiki...")

    def _run_write():
        from backend.core.agent.tools.builtin.mediawiki_tool import MediaWikiTool
        tool = MediaWikiTool()
        return tool.execute(
            operation=operation,
            title=title,
            content=content,
            summary=summary or ("由 AI 助手创建" if operation == "create" else "由 AI 助手编辑"),
        )

    try:
        result = await asyncio.to_thread(_run_write)
    except Exception as e:
        err_msg = str(e)
        if "MEDIAWIKI" in err_msg.upper() or "连接" in err_msg or "Login" in err_msg:
            return _err("MEDIAWIKI_UNAVAILABLE", "MediaWiki 不可用", err_msg, details=traceback.format_exc())
        return _err("MEDIAWIKI_WRITE_FAILED", "写入失败", err_msg, details=traceback.format_exc())

    if not result.success:
        return _err("MEDIAWIKI_WRITE_FAILED", "写入失败", result.error or "未知错误")

    worker.update_task_progress(100, "写入完成")
    data = result.data or {}
    summary_text = data.get("message") or f"已{'创建' if operation == 'create' else '编辑'}页面「{title}」"
    return {"status": "success", "summary": summary_text, "data": data}


async def process_wechat_mp_draft_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """处理公众号草稿任务（新增或更新）。失败时返回统一错误结构。"""
    metadata = task_info.get("metadata", {})
    worker = get_task_worker()

    operation = (metadata.get("operation") or "add").strip().lower()
    if operation not in ("add", "update"):
        operation = "add"

    title = (metadata.get("title") or "").strip()
    if not title:
        return _err("MISSING_TITLE", "缺少标题", "title 参数是必需的")

    content = metadata.get("content")
    content = (content.strip() if isinstance(content, str) else str(content or "").strip()) if content is not None else ""
    if not content:
        return _err("MISSING_CONTENT", "缺少正文", "content 参数是必需的")

    author = (metadata.get("author") or "").strip() or None
    digest = (metadata.get("digest") or "").strip() or None
    thumb_media_id = (metadata.get("thumb_media_id") or "").strip() or None
    content_source_url = (metadata.get("content_source_url") or "").strip() or None
    media_id = (metadata.get("media_id") or "").strip() or None

    if operation == "update" and not media_id:
        return _err("MISSING_MEDIA_ID", "更新草稿需要选择草稿", "请在表单中从当前草稿列表选择要更新的草稿")

    if operation == "add" and not thumb_media_id:
        return _err("MISSING_THUMB", "新增草稿需要封面图", "请先通过上传图文消息内图片接口获取 thumb_media_id 并填写")

    worker.update_task_progress(10, "正在写入公众号草稿...")

    def _run_draft():
        from backend.services.wechat_mp_service import WeChatMPClient, WeChatMPClientError
        client = WeChatMPClient()
        if operation == "add":
            result = client.add_draft(
                title=title,
                content=content,
                author=author,
                digest=digest,
                thumb_media_id=thumb_media_id,
                content_source_url=content_source_url,
            )
            mid = result.get("media_id") or ""
            return {"media_id": mid, "operation": "add", "message": "草稿已保存，可在公众号助手发布"}
        else:
            client.update_draft(
                media_id=media_id,
                index=0,
                title=title,
                content=content,
                author=author,
                digest=digest,
                thumb_media_id=thumb_media_id,
                content_source_url=content_source_url,
            )
            return {"media_id": media_id, "operation": "update", "message": "草稿已更新，可在公众号助手发布"}

    try:
        data = await asyncio.to_thread(_run_draft)
    except Exception as e:
        err_msg = str(e)
        if "WeChatMPClientError" in type(e).__name__ or "公众号" in err_msg or "草稿" in err_msg:
            return _err("WECHAT_MP_DRAFT_FAILED", "公众号草稿失败", err_msg, details=traceback.format_exc())
        return _err("WECHAT_MP_DRAFT_FAILED", "公众号草稿失败", err_msg, details=traceback.format_exc())

    worker.update_task_progress(100, "草稿已保存")
    summary = f"已{'新增' if operation == 'add' else '更新'}草稿：{title[:20]}{'…' if len(title) > 20 else ''}"
    return {"status": "success", "summary": summary, "data": data}


# 长文分段阈值（字符），超过则分段翻译
URL_TO_WIKI_CHUNK_SIZE = 5000

# PDF 转 Wiki 限制（可从环境变量覆盖）
PDF_TO_WIKI_MAX_FILE_BYTES = int(
    os.environ.get("PDF_TO_WIKI_MAX_FILE_BYTES", str(50 * 1024 * 1024))
)
PDF_TO_WIKI_MAX_PAGES = int(os.environ.get("PDF_TO_WIKI_MAX_PAGES", "500"))
PDF_TO_WIKI_DOWNLOAD_TIMEOUT = int(os.environ.get("PDF_TO_WIKI_DOWNLOAD_TIMEOUT", "300"))
PDF_TO_WIKI_CHUNK_CHARS = 8000
PDF_TO_WIKI_PAGES_PER_CHUNK = 10


def _download_pdf_to_temp(url: str) -> Tuple[str, int]:
    """将 PDF URL 下载到临时文件。返回 (临时文件路径, 字节数)。超过 PDF_TO_WIKI_MAX_FILE_BYTES 抛 ValueError。"""
    import tempfile
    import httpx

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = f.name
    try:
        with httpx.stream(
            "GET", url, follow_redirects=True, timeout=PDF_TO_WIKI_DOWNLOAD_TIMEOUT
        ) as r:
            r.raise_for_status()
            cl = r.headers.get("content-length")
            if cl and int(cl) > PDF_TO_WIKI_MAX_FILE_BYTES:
                Path(temp_path).unlink(missing_ok=True)
                raise ValueError(
                    f"PDF 超过大小限制（当前上限 {PDF_TO_WIKI_MAX_FILE_BYTES // (1024*1024)} MB）"
                )
            total = 0
            with open(temp_path, "wb") as out:
                for chunk in r.iter_bytes(8192):
                    total += len(chunk)
                    if total > PDF_TO_WIKI_MAX_FILE_BYTES:
                        out.close()
                        Path(temp_path).unlink(missing_ok=True)
                        raise ValueError(
                            f"PDF 超过大小限制（当前上限 {PDF_TO_WIKI_MAX_FILE_BYTES // (1024*1024)} MB）"
                        )
                    out.write(chunk)
        return temp_path, total
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        raise


def _fix_doubled_pdf_text(text: str) -> str:
    """
    部分 PDF 导出会导致「每字重复」（如 TThhee -> The）。
    若相邻重复对占比过高，尝试取偶数位还原（奇数长度时取前 n-1 再取偶，避免误伤）。
    """
    if not text or len(text) < 4:
        return text
    n = len(text)
    pairs = sum(1 for i in range(n - 1) if text[i] == text[i + 1])
    ratio = pairs / (n - 1) if n > 1 else 0
    if ratio < 0.25:
        return text
    # 取偶数位即得到「去重」结果；长度为奇数时仍取 0::2，可能少一个尾字
    undoubled = text[0::2]
    # 校验：还原后不应出现大量连续相同字符（避免误伤正常文段）
    if len(undoubled) > 1:
        runs = sum(1 for i in range(len(undoubled) - 1) if undoubled[i] == undoubled[i + 1])
        if runs / (len(undoubled) - 1) >= 0.5:
            return text
    return undoubled


def _extract_text_from_pdf_page_range(pdf_path: str, page_from: int, page_to: int) -> str:
    """从 PDF 提取指定页范围（1-based，含首尾）的文本。优先用 pdfminer.six（与 pdf2txt 同引擎），效果更好；失败则回退 pdfplumber。"""
    # 优先使用 pdfminer.six（与 pdf2txt 同引擎，排版/编码通常更稳）
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract_text

        page_numbers = list(range(page_from - 1, page_to))
        if not page_numbers:
            return ""
        raw = pdfminer_extract_text(pdf_path, page_numbers=page_numbers)
        if raw and raw.strip():
            text = _fix_doubled_pdf_text(raw.strip())
            return text
    except Exception:
        pass

    # 回退：pdfplumber
    import pdfplumber

    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(page_from - 1, min(page_to, len(pdf.pages))):
            page = pdf.pages[i]
            try:
                page = page.dedupe_chars(tolerance=3)
            except Exception:
                pass
            text = page.extract_text()
            if text:
                text = _fix_doubled_pdf_text(text.strip())
                parts.append(text)
    return "\n\n".join(parts)


def _chunk_text_by_paragraphs(text: str, max_chars: int = 4000) -> List[str]:
    """按段落（双换行）切分，使每块不超过 max_chars。"""
    if len(text) <= max_chars:
        return [text] if text.strip() else []
    chunks = []
    current = []
    current_len = 0
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if current_len + len(para) + 2 <= max_chars:
            current.append(para)
            current_len += len(para) + 2
        else:
            if current:
                chunks.append("\n\n".join(current))
            current = [para]
            current_len = len(para) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks


async def process_url_to_wiki_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """抓取 URL 正文 → 翻译成中文 → 生成 Markdown 草稿；可选自动写入 MediaWiki。"""
    metadata = task_info.get("metadata", {})
    worker = get_task_worker()
    url = (metadata.get("url") or "").strip()
    if not url:
        return _err("MISSING_URL", "缺少 URL", "请填写要抓取的文章 url")
    if not url.startswith(("http://", "https://")):
        return _err("INVALID_URL", "URL 无效", "仅支持 http 或 https 链接")

    worker.update_task_progress(5, "正在抓取 URL...")
    fetch_tool = None
    try:
        from backend.core.agent.tools.builtin.web_fetch_tool import WebFetchTool
        fetch_tool = WebFetchTool()
    except Exception as e:
        return _err("WEB_FETCH_UNAVAILABLE", "web_fetch 不可用", str(e))
    try:
        result = await asyncio.to_thread(fetch_tool.execute, url=url)
    except Exception as e:
        return _err("FETCH_FAILED", "抓取失败", str(e), details=traceback.format_exc())
    if not result.success:
        return _err("FETCH_FAILED", "抓取失败", result.error or "未知错误")
    data = result.data or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    if not content:
        return _err("NO_CONTENT", "未提取到正文", "该 URL 未能提取到正文内容")
    from backend.core.agent.tools.builtin.web_fetch_tool import _url_to_fallback_title
    raw_title = title or _url_to_fallback_title(url)
    user_wiki_title = (metadata.get("wiki_title") or "").strip()

    lang = (metadata.get("language") or "zh").strip().lower()
    skip_translate = lang == "original"
    if skip_translate:
        worker.update_task_progress(25, "保留原文，不翻译...")
        wiki_title = user_wiki_title or raw_title or "Untitled"
        translated = content.strip()
        if not translated:
            return _err("NO_CONTENT", "未提取到正文", "该 URL 未能提取到正文内容")
        # 原文作为 Markdown 草稿（多为纯文本，md_to_wiki 会原样保留非 Markdown 部分）
    else:
        worker.update_task_progress(25, "正在翻译...")
        from backend.services.llm.llm_service import LLMService
        llm = LLMService()
        lang_name = {"zh": "中文", "en": "英文", "ja": "日文"}.get(lang, "中文")

        # 页面标题：用户指定则用用户的；否则默认从 HTML title（或 URL 派生）获取，并按目标语言自动翻译
        if user_wiki_title:
            wiki_title = user_wiki_title
        elif raw_title:
            title_prompt = f"将以下标题翻译成{lang_name}，只输出翻译后的标题，不要引号、换行或多余内容：\n{raw_title}"
            try:
                translated_title = await llm.chat(user_prompt=title_prompt)
                wiki_title = (translated_title or "").strip() or raw_title
            except Exception:
                wiki_title = raw_title
        else:
            wiki_title = "Untitled"

        sys_prompt = (
            f"将用户提供的内容翻译成{lang_name}，保持标题、列表、段落结构。"
            "输出格式为 Markdown：一级标题用 ## 标题，二级用 ### 标题；"
            "无序列表用 - 或 * 项，有序列表用 1. 项；粗体用 **文字**；链接用 [显示文字](url)。"
            "段落之间空一行。只输出转换后的内容，不要其他说明。"
        )
        if len(content) > URL_TO_WIKI_CHUNK_SIZE:
            chunks = _chunk_text_by_paragraphs(content, max_chars=4000)
            translated_parts = []
            for i, chunk in enumerate(chunks):
                worker.update_task_progress(25 + int(45 * (i + 1) / len(chunks)), f"翻译第 {i + 1}/{len(chunks)} 段...")
                part = await llm.chat(system_prompt=sys_prompt, user_prompt=chunk)
                translated_parts.append((part or "").strip())
            translated = "\n\n".join(translated_parts)
        else:
            translated = await llm.chat(system_prompt=sys_prompt, user_prompt=content)
            translated = (translated or "").strip()
        if not translated:
            return _err("TRANSLATE_FAILED", "翻译失败", "LLM 未返回有效内容")

    # 在正文开头加入原文链接（Markdown 格式）
    original_link_line = f"**原文链接**：[原文]({url})"
    markdown = f"{original_link_line}\n\n{translated}"

    # 分类：前端传来的 categories + 执行时的日/周/月（写入 Wiki 时追加到 wikitext）
    categories = metadata.get("categories")
    if isinstance(categories, list) and categories:
        categories = [str(c).strip() for c in categories if str(c).strip()]
    else:
        categories = []
    now = datetime.now()
    iso_year, iso_week, _ = now.isocalendar()
    date_cats = [
        f"{now.year}年{now.month}月{now.day}日",
        f"{iso_year}年第{iso_week}周",
        f"{now.year}年{now.month}月",
    ]
    categories = list(categories) + date_cats

    auto_write = bool(metadata.get("auto_write", True))
    if not auto_write:
        worker.update_task_progress(100, "已生成 Markdown 草稿（未写入 MediaWiki）")
        return {
            "status": "success",
            "summary": "已抓取并生成 Markdown 草稿（未写入 MediaWiki）",
            "data": {"url": url, "wiki_title": wiki_title, "markdown": markdown, "wrote_to_wiki": False},
        }

    worker.update_task_progress(85, "正在写入 MediaWiki...")
    from backend.utils.md_to_wiki import md_to_wiki
    wikitext = md_to_wiki(markdown)
    if categories:
        existing = set(re.findall(r"\[\[Category:\s*([^\]\|]+)", wikitext, re.I))
        for cat in categories:
            if cat and cat not in existing:
                wikitext = wikitext.rstrip() + f"\n\n[[Category:{cat}]]"
                existing.add(cat)

    from backend.core.agent.tools.builtin.mediawiki_tool import MediaWikiTool
    mw_tool = MediaWikiTool()
    try:
        write_result = await asyncio.to_thread(
            mw_tool.execute,
            operation="edit",
            title=wiki_title,
            content=wikitext,
            summary=f"由 url_to_wiki 任务写入：{url[:50]}…",
        )
    except Exception as e:
        return _err("MEDIAWIKI_WRITE_FAILED", "写入 Wiki 失败", str(e), details=traceback.format_exc())
    if not write_result.success:
        return _err("MEDIAWIKI_WRITE_FAILED", "写入 Wiki 失败", write_result.error or "未知错误")

    worker.update_task_progress(100, "完成")
    summary = f"已抓取并写入页面「{wiki_title}」" if skip_translate else f"已抓取并翻译写入页面「{wiki_title}」"
    return {
        "status": "success",
        "summary": summary,
        "data": {"url": url, "wiki_title": wiki_title, "markdown": markdown, "wrote_to_wiki": True},
    }


async def process_pdf_to_wiki_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """PDF（URL 或本地路径）→ 按页拆分 → 转文字 → 逐块翻译 → 单页写入 MediaWiki；支持部分块失败。"""
    metadata = task_info.get("metadata", {})
    worker = get_task_worker()
    url = (metadata.get("url") or "").strip()
    file_path_raw = (metadata.get("file_path") or "").strip()
    if not url and not file_path_raw:
        return _err("MISSING_INPUT", "缺少输入", "请填写 PDF 的 url 或 file_path（二选一）")
    if url and file_path_raw:
        return _err("AMBIGUOUS_INPUT", "只能填一种来源", "请只填写 url 或 file_path 其一")
    use_local = bool(file_path_raw)
    if use_local:
        fp = Path(file_path_raw).expanduser().resolve()
        ok, err_msg = _validate_input_path_in_home(fp)
        if not ok:
            return _err("FILE_PATH_INVALID", "本地路径无效", err_msg or "路径须在用户主目录下且为已存在文件")
        if fp.suffix.lower() != ".pdf":
            return _err("FILE_PATH_INVALID", "非 PDF 文件", "file_path 须指向 .pdf 文件")
        pdf_path = str(fp)
        temp_path: Optional[str] = None
        source_label = file_path_raw
    else:
        if not url.lower().endswith(".pdf"):
            return _err("INVALID_URL", "URL 无效", "当前仅支持 PDF 链接（.pdf）")
        if not url.startswith(("http://", "https://")):
            return _err("INVALID_URL", "URL 无效", "仅支持 http 或 https 链接")
        worker.update_task_progress(5, "正在下载 PDF...")
        try:
            temp_path, _size = await asyncio.to_thread(_download_pdf_to_temp, url)
        except ValueError as e:
            return _err("PDF_TOO_LARGE", "PDF 超过大小限制", str(e))
        except Exception as e:
            return _err(
                "PDF_DOWNLOAD_FAILED",
                "下载失败",
                str(e),
                details=traceback.format_exc(),
            )
        pdf_path = temp_path
        source_label = url

    try:
        worker.update_task_progress(10, "正在解析 PDF...")
        import pdfplumber

        total_pages: int
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
        max_pages = metadata.get("max_pages")
        if max_pages is not None:
            try:
                max_pages = int(max_pages)
            except (TypeError, ValueError):
                max_pages = PDF_TO_WIKI_MAX_PAGES
        else:
            max_pages = PDF_TO_WIKI_MAX_PAGES
        if total_pages > max_pages:
            return _err(
                "PDF_TOO_MANY_PAGES",
                "页数超限",
                f"PDF 共 {total_pages} 页，当前上限 {max_pages} 页；可设置 max_pages 或使用更大上限",
            )

        chunk_ranges: List[Tuple[int, int]] = []
        p = 1
        while p <= total_pages:
            end = min(p + PDF_TO_WIKI_PAGES_PER_CHUNK - 1, total_pages)
            chunk_ranges.append((p, end))
            p = end + 1

        user_wiki_title = (metadata.get("wiki_title") or "").strip()
        if not user_wiki_title:
            if use_local:
                user_wiki_title = Path(pdf_path).stem or "PDF"
            else:
                from urllib.parse import unquote
                raw = unquote((url.split("?")[0].split("/")[-1]) or "")
                name = Path(raw)
                user_wiki_title = (name.stem if name.suffix.lower() == ".pdf" else raw) or "PDF"
        lang = (metadata.get("language") or "zh").strip().lower()
        skip_translate = lang == "original"
        lang_name = {"zh": "中文", "en": "英文", "ja": "日文"}.get(lang, "中文")
        llm = None
        sys_prompt = ""
        if not skip_translate:
            from backend.services.llm.llm_service import LLMService
            llm = LLMService()
            sys_prompt = (
                f"将用户提供的内容翻译成{lang_name}，保持标题、列表、段落结构。"
                "输出格式为 Markdown：一级标题用 ## 标题，二级用 ### 标题；"
                "无序列表用 - 或 * 项，有序列表用 1. 项；粗体用 **文字**；链接用 [显示文字](url)。"
                "段落之间空一行。只输出转换后的内容，不要其他说明。"
            )

        translated_parts: List[str] = []
        failed_chunks: List[Dict[str, Any]] = []
        n = len(chunk_ranges)
        for i, (p_from, p_to) in enumerate(chunk_ranges):
            worker.update_task_progress(
                15 + int(60 * (i + 1) / n),
                f"第 {i + 1}/{n} 块（第 {p_from}-{p_to} 页）" + ("转文字..." if skip_translate else "转文字与翻译..."),
            )
            raw_text = ""
            try:
                raw_text = await asyncio.to_thread(
                    _extract_text_from_pdf_page_range, pdf_path, p_from, p_to
                )
            except Exception as e:
                failed_chunks.append({"chunk_index": i, "page_from": p_from, "page_to": p_to, "reason": f"提取失败: {e}"})
                translated_parts.append(f"\n\n第 {p_from}-{p_to} 页\n\n（本段提取失败）")
                continue
            if not raw_text.strip():
                translated_parts.append(f"\n\n第 {p_from}-{p_to} 页\n\n（本段无提取文本）")
                continue
            if skip_translate:
                translated_parts.append(f"\n\n第 {p_from}-{p_to} 页\n\n{raw_text.strip()}")
                continue
            try:
                if len(raw_text) > PDF_TO_WIKI_CHUNK_CHARS:
                    sub_chunks = _chunk_text_by_paragraphs(raw_text, max_chars=4000)
                    sub_parts = []
                    for sc in sub_chunks:
                        part = await llm.chat(system_prompt=sys_prompt, user_prompt=sc)
                        sub_parts.append((part or "").strip())
                    translated_parts.append("\n\n".join(sub_parts))
                else:
                    part = await llm.chat(system_prompt=sys_prompt, user_prompt=raw_text)
                    translated_parts.append((part or "").strip())
            except Exception as e:
                failed_chunks.append({"chunk_index": i, "page_from": p_from, "page_to": p_to, "reason": f"翻译失败: {e}"})
                translated_parts.append(f"\n\n第 {p_from}-{p_to} 页\n\n（本段翻译失败）")

        full_translated = "\n\n".join(translated_parts)
        if not full_translated.strip():
            return _err("NO_CONTENT", "未提取到正文", "PDF 中未能提取到可翻译的文本")

        categories = metadata.get("categories")
        if isinstance(categories, list) and categories:
            categories = [str(c).strip() for c in categories if str(c).strip()]
        else:
            categories = []
        now = datetime.now()
        iso_year, iso_week, _ = now.isocalendar()
        date_cats = [
            f"{now.year}年{now.month}月{now.day}日",
            f"{iso_year}年第{iso_week}周",
            f"{now.year}年{now.month}月",
        ]
        categories = list(categories) + date_cats

        def _append_categories(wikitext: str, cats: List[str]) -> str:
            if not cats:
                return wikitext
            existing = set(re.findall(r"\[\[Category:\s*([^\]\|]+)", wikitext, re.I))
            out = wikitext.rstrip()
            for cat in cats:
                if cat and cat not in existing:
                    out += f"\n\n[[Category:{cat}]]"
                    existing.add(cat)
            return out

        if url:
            original_link_line_md = f"**原文链接**：[原文]({url})"
        else:
            original_link_line_md = f"**来源**：本地文件 {source_label}"

        from backend.utils.md_to_wiki import md_to_wiki
        output_mode = (metadata.get("wiki_output_mode") or "single").strip().lower()
        worker.update_task_progress(90, "正在写入 MediaWiki...")
        from backend.core.agent.tools.builtin.mediawiki_tool import MediaWikiTool
        mw_tool = MediaWikiTool()
        write_summary = f"由 pdf_to_wiki 任务写入：{(source_label[:50] + '…') if len(source_label) > 50 else source_label}"

        if output_mode == "multi":
            # 多子页面：先写各块子页 书名/第k部分，再写目录页 书名
            wiki_pages: List[str] = []
            for i in range(n):
                sub_title = f"{user_wiki_title}/第{i + 1}部分"
                part_wikitext = md_to_wiki(translated_parts[i])
                part_content = _append_categories(part_wikitext, categories)
                try:
                    wr = await asyncio.to_thread(
                        mw_tool.execute,
                        operation="edit",
                        title=sub_title,
                        content=part_content,
                        summary=write_summary,
                    )
                except Exception as e:
                    return _err("MEDIAWIKI_WRITE_FAILED", "写入子页失败", str(e), details=traceback.format_exc())
                if not wr.success:
                    return _err("MEDIAWIKI_WRITE_FAILED", "写入子页失败", wr.error or "未知错误")
                wiki_pages.append(sub_title)
            index_lines = [
                original_link_line_md,
                "",
                "本页为目录，各子页见下方。",
                "",
            ]
            for k in range(n):
                index_lines.append(f"- [第{k + 1}部分]({user_wiki_title}/第{k + 1}部分)")
            index_wikitext = md_to_wiki("\n".join(index_lines))
            index_content = _append_categories(index_wikitext, categories)
            try:
                wr = await asyncio.to_thread(
                    mw_tool.execute,
                    operation="edit",
                    title=user_wiki_title,
                    content=index_content,
                    summary=write_summary,
                )
            except Exception as e:
                return _err("MEDIAWIKI_WRITE_FAILED", "写入目录页失败", str(e), details=traceback.format_exc())
            if not wr.success:
                return _err("MEDIAWIKI_WRITE_FAILED", "写入目录页失败", wr.error or "未知错误")
            wiki_pages.insert(0, user_wiki_title)
            successful_chunks = n - len(failed_chunks)
            status = "partial" if failed_chunks else "success"
            if failed_chunks:
                summary = f"已处理 {successful_chunks}/{n} 块并写入目录页「{user_wiki_title}」及 {n} 个子页，{len(failed_chunks)} 块失败"
            else:
                summary = f"已处理 PDF 并写入目录页「{user_wiki_title}」及 {n} 个子页"
            if skip_translate:
                summary += "（未翻译）"
            worker.update_task_progress(100, "完成")
            data = {
                "wiki_title": user_wiki_title,
                "wiki_pages": wiki_pages,
                "total_pages": total_pages,
                "total_chunks": n,
                "successful_chunks": successful_chunks,
            }
            if url:
                data["pdf_url"] = url
            else:
                data["file_path"] = source_label
            if failed_chunks:
                data["failed_chunks"] = failed_chunks
            return {"status": status, "summary": summary, "data": data}
        else:
            # single：单页汇总（Markdown → wikitext）
            markdown_content = f"{original_link_line_md}\n\n{full_translated}"
            wikitext_content = md_to_wiki(markdown_content)
            content_to_write = _append_categories(wikitext_content, categories)
            try:
                write_result = await asyncio.to_thread(
                    mw_tool.execute,
                    operation="edit",
                    title=user_wiki_title,
                    content=content_to_write,
                    summary=write_summary,
                )
            except Exception as e:
                return _err(
                    "MEDIAWIKI_WRITE_FAILED",
                    "写入 Wiki 失败",
                    str(e),
                    details=traceback.format_exc(),
                )
            if not write_result.success:
                return _err(
                    "MEDIAWIKI_WRITE_FAILED",
                    "写入 Wiki 失败",
                    write_result.error or "未知错误",
                )
            successful_chunks = n - len(failed_chunks)
            status = "partial" if failed_chunks else "success"
            if failed_chunks:
                summary = f"已处理 {successful_chunks}/{n} 块并写入页面「{user_wiki_title}」，{len(failed_chunks)} 块失败"
            else:
                summary = f"已处理 PDF 并写入页面「{user_wiki_title}」"
            if skip_translate:
                summary += "（未翻译）"
            worker.update_task_progress(100, "完成")
            data = {
                "wiki_title": user_wiki_title,
                "total_pages": total_pages,
                "total_chunks": n,
                "successful_chunks": successful_chunks,
            }
            if url:
                data["pdf_url"] = url
            else:
                data["file_path"] = source_label
            if failed_chunks:
                data["failed_chunks"] = failed_chunks
            return {"status": status, "summary": summary, "data": data}
    finally:
        if temp_path and Path(temp_path).exists():
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass


def _format_iso_datetime(iso_str: Optional[str]) -> str:
    """将 ISO 时间格式化为 YYYY-MM-DD HH:MM 便于阅读。"""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_str[:16] if len(iso_str) >= 16 else iso_str


async def process_wiki_directory_refresh_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
    """根据已完成的任务记录（url_to_wiki、pdf_to_wiki）生成并写入 Wiki 目录页。"""
    metadata = task_info.get("metadata", {})
    worker = get_task_worker()
    dir_title = (metadata.get("wiki_title") or "").strip() or "网文与PDF翻译目录"
    limit = metadata.get("limit")
    if limit is None:
        limit = 300
    try:
        limit = int(limit)
        if limit < 1 or limit > 1000:
            limit = 300
    except (TypeError, ValueError):
        limit = 300

    worker.update_task_progress(10, "正在查询任务记录...")
    db = get_task_queue_db()
    tasks = db.list_tasks(
        status=TaskStatus.COMPLETED,
        limit=limit,
        include_result=True,
        task_types=["url_to_wiki", "pdf_to_wiki"],
    )
    rows: List[Dict[str, Any]] = []
    for t in tasks:
        res = t.get("result")
        if not isinstance(res, dict):
            continue
        data = res.get("data") or {}
        wiki_title = data.get("wiki_title")
        if not wiki_title or not str(wiki_title).strip():
            continue
        source = ""
        if t.get("task_type") == "url_to_wiki":
            url = data.get("url") or ""
            source = f"[{url} 原文]" if url else "—"
            type_label = "网文抓取"
        else:
            url = data.get("pdf_url") or ""
            fp = data.get("file_path") or ""
            if url:
                source = f"[{url} PDF]"
            elif fp:
                source = f"本地 {fp}"
            else:
                source = "—"
            type_label = "PDF转Wiki"
        completed_at = _format_iso_datetime(t.get("completed_at"))
        rows.append({
            "wiki_title": str(wiki_title).strip(),
            "source": source,
            "completed_at": completed_at,
            "type_label": type_label,
        })
        # pdf_to_wiki 多子页面时 data.wiki_pages 为列表，可在此展开多行（当前单页模式仅一条）
        wiki_pages = data.get("wiki_pages")
        if isinstance(wiki_pages, list) and len(wiki_pages) > 1:
            for sub in wiki_pages[1:]:
                if sub and str(sub).strip():
                    rows.append({
                        "wiki_title": str(sub).strip(),
                        "source": f"（见 [[{wiki_title}]]）",
                        "completed_at": completed_at,
                        "type_label": type_label,
                    })

    worker.update_task_progress(50, "正在生成目录内容...")
    intro = "本页由 hou-cli 根据任务记录自动生成，列出网文抓取与 PDF 转 Wiki 任务写入的页面。\n\n"
    table_lines = [
        "{| class=\"wikitable\"",
        "|-",
        "! 页面 !! 来源 !! 完成时间 !! 类型",
    ]
    for r in rows:
        # 单元格内竖线用 &#124; 避免破坏表格
        title_cell = f"[[{r['wiki_title']}]]".replace("|", "&#124;")
        source_cell = (r["source"] or "—").replace("|", "&#124;")
        table_lines.append("|-")
        table_lines.append(f"| {title_cell} || {source_cell} || {r['completed_at']} || {r['type_label']}")
    table_lines.append("|}")
    content = intro + "\n".join(table_lines)
    content += "\n\n[[Category:hou-cli]]"

    worker.update_task_progress(80, "正在写入 Wiki...")
    from backend.core.agent.tools.builtin.mediawiki_tool import MediaWikiTool
    mw_tool = MediaWikiTool()
    try:
        write_result = await asyncio.to_thread(
            mw_tool.execute,
            operation="edit",
            title=dir_title,
            content=content,
            summary="由 wiki_directory_refresh 任务根据任务记录更新",
        )
    except Exception as e:
        return _err(
            "MEDIAWIKI_WRITE_FAILED",
            "写入目录页失败",
            str(e),
            details=traceback.format_exc(),
        )
    if not write_result.success:
        return _err(
            "MEDIAWIKI_WRITE_FAILED",
            "写入目录页失败",
            write_result.error or "未知错误",
        )
    worker.update_task_progress(100, "完成")
    return {
        "status": "success",
        "summary": f"已更新目录页「{dir_title}」，共 {len(rows)} 条",
        "data": {"wiki_title": dir_title, "entry_count": len(rows)},
    }


def register_default_handlers():
    """注册默认的任务处理器"""
    worker = get_task_worker()
    worker.register_handler("video_download", process_video_download_task)
    worker.register_handler("weather_query", process_weather_query_task)
    worker.register_handler("web_search", process_web_search_task)
    worker.register_handler("speech_to_text", process_speech_to_text_task)
    worker.register_handler("video_extract_audio", process_video_extract_audio_task)
    worker.register_handler("mediawiki_write", process_mediawiki_write_task)
    worker.register_handler("url_to_wiki", process_url_to_wiki_task)
    worker.register_handler("pdf_to_wiki", process_pdf_to_wiki_task)
    worker.register_handler("wiki_directory_refresh", process_wiki_directory_refresh_task)
    worker.register_handler("wechat_mp_draft", process_wechat_mp_draft_task)
    logger.info(f"已注册 {len(worker.task_handlers)} 个任务处理器")


def get_available_task_types() -> List[Dict[str, Any]]:
    """获取可用的任务类型列表（含 pipeline_outputs / metadata_schema 中的 pipeline_accept，供管道编排判断可链接性）"""
    return [
        {
            "type": task_type,
            "name": info["name"],
            "description": info["description"],
            "metadata_schema": info["metadata_schema"],
            "pipeline_outputs": info.get("pipeline_outputs"),
        }
        for task_type, info in TASK_TYPES.items()
    ]


def get_task_type_info(task_type: str) -> Optional[Dict[str, Any]]:
    """获取特定任务类型的信息（含 pipeline_outputs，供管道编排判断可链接性）"""
    if task_type not in TASK_TYPES:
        return None

    info = TASK_TYPES[task_type]
    return {
        "type": task_type,
        "name": info["name"],
        "description": info["description"],
        "metadata_schema": info["metadata_schema"],
        "pipeline_outputs": info.get("pipeline_outputs"),
    }


def get_linkable_upstream_types(downstream_task_type: str) -> Dict[str, Any]:
    """
    根据任务类型的输入/输出 metadata，返回可作为管道上游的任务类型及推荐绑定。
    用于编排时筛选「可链接的上游任务类型」与默认绑定关系。
    """
    if downstream_task_type not in TASK_TYPES:
        return {"linkable_task_types": [], "suggested_bindings": {}}
    downstream = TASK_TYPES[downstream_task_type]
    schema = downstream.get("metadata_schema") or {}
    # 下游可被绑定的字段：(field_name, accept_type, accept_formats)
    accept_fields = []
    for field_name, field_spec in schema.items():
        if not isinstance(field_spec, dict):
            continue
        accept = field_spec.get("pipeline_accept")
        if not accept or not isinstance(accept, dict):
            continue
        accept_type = accept.get("type")
        formats = accept.get("formats")
        if isinstance(formats, list):
            accept_fields.append((field_name, accept_type, formats))
        elif accept_type:
            accept_fields.append((field_name, accept_type, []))
    if not accept_fields:
        return {"linkable_task_types": [], "suggested_bindings": {}}
    linkable = []
    suggested = {}
    for up_type, up_info in TASK_TYPES.items():
        if up_type == downstream_task_type:
            continue
        outputs = up_info.get("pipeline_outputs") or []
        for out in outputs:
            if not isinstance(out, dict):
                continue
            path = out.get("path")
            o_type = out.get("type")
            o_format = out.get("format")
            if not path:
                continue
            for field_name, accept_type, accept_formats in accept_fields:
                if o_type != accept_type:
                    continue
                if accept_formats and o_format and o_format not in accept_formats:
                    continue
                if up_type not in linkable:
                    linkable.append(up_type)
                suggested.setdefault(up_type, []).append({
                    "downstream_field": field_name,
                    "upstream_path": path,
                    "upstream_format": o_format,
                })
    return {"linkable_task_types": linkable, "suggested_bindings": suggested}


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

    # pdf_to_wiki：url 与 file_path 二选一，至少填一个
    if task_type == "pdf_to_wiki":
        u = (metadata.get("url") or "").strip()
        f = (metadata.get("file_path") or "").strip()
        if not u and not f:
            return False, "请填写 PDF 的 url 或 file_path（二选一）"
        if u and f:
            return False, "只能填写 url 或 file_path 其一"

    if task_type == "web_search":
        q = (metadata.get("query") or "").strip()
        if not q:
            return False, "请填写搜索关键词（query）"

    # weather_query 多选模式：至少勾选一种查询类型
    if task_type == "weather_query":
        qt = metadata.get("query_type")
        if qt is None or str(qt).strip() == "":
            _tb = lambda v: v in (True, "true", "1", 1)
            if not any((_tb(metadata.get("fetch_current", True)), _tb(metadata.get("fetch_forecast", True)),
                        _tb(metadata.get("fetch_warning", True)), _tb(metadata.get("fetch_air_quality", True)))):
                return False, "请至少勾选一种查询类型（实时天气、天气预报、预警、空气质量）"

    # wechat_mp_draft：operation=update 时须从当前草稿列表选择要更新的草稿
    if task_type == "wechat_mp_draft":
        op = (metadata.get("operation") or "").strip().lower()
        if op == "update":
            mid = (metadata.get("media_id") or "").strip()
            if not mid:
                return False, "请从当前草稿列表选择要更新的草稿"

    return True, None
