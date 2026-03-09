"""技能工具函数：参数提取、结果格式化"""
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def extract_skill_parameters(
    task: str,
    skill: Any,
    tool_registry: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    从用户任务中提取技能参数

    Args:
        task: 用户任务描述
        skill: 技能对象（需有 name、parameters 属性）
        tool_registry: 工具注册表（可选，用于 file_search 查找本地文件）

    Returns:
        参数字典
    """
    parameters = {}

    # 提取 URL
    url_pattern = r'https?://[^\s"\'\),。，、]+'
    raw_urls = re.findall(url_pattern, task)
    urls = []
    for url in raw_urls:
        url = url.rstrip('.,;:!?)\'"）')
        if url.startswith('http://') or url.startswith('https://'):
            urls.append(url)

    if urls:
        if len(urls) == 1:
            parameters['url'] = urls[0]
        elif len(urls) > 1:
            if skill.name == 'video_downloader':
                parameters['urls'] = urls
                logger.info(f"检测到多个 URL（共 {len(urls)} 个），video_downloader 技能支持批量下载")
            else:
                url_param = next((p for p in skill.parameters if p.name == 'url' or p.name == 'urls'), None)
                if url_param and url_param.type == 'array':
                    parameters[url_param.name] = urls
                else:
                    parameters['url'] = urls[0]
                    logger.warning(f"检测到多个 URL（共 {len(urls)} 个），但技能不支持数组参数，将处理第一个: {urls[0]}")

    # 提取本地文件路径（需要 tool_registry）
    local_files = []
    file_path_params = [p for p in skill.parameters if 'file' in p.name.lower() or 'path' in p.name.lower()]
    if file_path_params and tool_registry:
        filename_pattern = r'([\w\u4e00-\u9fff【】！×\s\-_]+\.(?:mp4|avi|mkv|mov|flv|webm|m4v|3gp|ts|mts|vob|ogv|rm|rmvb|asf|f4v|m2v|mpg|mpeg|mpe|mpv|m2ts|mts|mxf|divx|amv|qt|yuv|bik|drc|gifv|mng|nsv|roq|svi|viv|wmv|y4m|mp3|wav|m4a|aac|ogg|flac|srt|vtt|ass|ssa))'
        filename_matches = re.findall(filename_pattern, task, re.IGNORECASE)
        if filename_matches:
            try:
                file_search_tool = tool_registry.get_tool('file_search')
                if file_search_tool:
                    search_query = filename_matches[0].split('.')[0].strip()
                    if len(search_query) < 5:
                        search_query = filename_matches[0]
                    search_result = file_search_tool.execute(
                        query=search_query,
                        file_type=f"*.{filename_matches[0].split('.')[-1]}" if '.' in filename_matches[0] else None,
                        limit=5,
                    )
                    if search_result.success and search_result.data:
                        results = search_result.data.get('results', [])
                        if results:
                            local_files = [results[0]['path']]
                            logger.info(f"使用 file_search_tool 找到文件: {local_files[0]}")
                        else:
                            logger.warning(f"file_search_tool 未找到匹配文件: {search_query}")
                    else:
                        logger.warning(f"file_search_tool 搜索失败: {search_result.error if hasattr(search_result, 'error') else 'unknown error'}")
                else:
                    logger.warning("file_search_tool 未注册，无法使用文件搜索")
            except Exception as e:
                logger.warning(f"使用 file_search_tool 搜索文件失败: {e}", exc_info=True)

    # video_extract_srt
    if local_files and skill.name == 'video_extract_srt':
        if len(local_files) == 1:
            parameters['video_path'] = local_files[0]
        elif len(local_files) > 1:
            video_paths_param = next((p for p in skill.parameters if p.name == 'video_paths'), None)
            if video_paths_param and video_paths_param.type == 'array':
                parameters['video_paths'] = local_files
            else:
                parameters['video_path'] = local_files[0]
                logger.warning(f"检测到多个本地文件（共 {len(local_files)} 个），但技能不支持数组参数，将处理第一个: {local_files[0]}")

    # video_cut
    if skill.name == 'video_cut' and local_files:
        parameters['input_file'] = local_files[0]
        time_pattern = r'(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})'
        times = re.findall(time_pattern, task)
        if len(times) >= 2:
            start_time, end_time = times[0], times[1]

            def normalize_time(t):
                parts = t.split(':')
                if len(parts) == 2:
                    return f"00:{parts[0]}:{parts[1]}"
                return t

            start_time = normalize_time(start_time)
            end_time = normalize_time(end_time)
            parameters['segments'] = [{'start_time': start_time, 'end_time': end_time}]
            input_path = Path(parameters['input_file'])
            time_str = f"{start_time.replace(':', '')}-{end_time.replace(':', '')}"
            output_name = f"{input_path.stem}_cut_{time_str}{input_path.suffix}"
            parameters['output_file'] = str(input_path.parent / output_name)
            logger.info(f"提取 video_cut 参数: input_file={parameters['input_file']}, segments={parameters['segments']}, output_file={parameters['output_file']}")
        elif len(times) == 1:
            logger.warning(f"只检测到一个时间点: {times[0]}，video_cut 需要开始和结束时间")
        else:
            logger.warning("未检测到时间范围，video_cut 需要时间段信息")

    # 默认值填充
    for param in skill.parameters:
        if param.name not in parameters and param.default is not None:
            parameters[param.name] = param.default

    logger.info(f"提取的技能参数: {parameters}")
    return parameters


def format_skill_result(skill: Any, skill_result: Any) -> str:
    """
    格式化技能执行结果为文本

    Args:
        skill: 技能对象（需有 name 属性）
        skill_result: 技能执行结果（需有 success、error、data 属性）

    Returns:
        格式化的文本结果
    """
    if not skill_result.success:
        return f"❌ 技能执行失败: {skill_result.error or '未知错误'}"

    data = skill_result.data or {}
    if skill.name == 'video_downloader':
        results = data.get('results', [])
        errors = data.get('errors', [])
        total = data.get('total', 0)
        success_count = data.get('success', 0)
        failed_count = data.get('failed', 0)
        result_text = "## 📥 视频下载完成\n\n"
        result_text += f"**总计**: {total} 个视频\n"
        result_text += f"**成功**: {success_count} 个\n"
        result_text += f"**失败**: {failed_count} 个\n\n"
        if results:
            result_text += "### ✅ 成功下载的视频：\n"
            for i, result in enumerate(results, 1):
                url = result.get('url', 'N/A')
                output_file = result.get('output_file', '')
                subtitle_file = result.get('subtitle_file', '')
                retry_with_cookies = result.get('retry_with_cookies', False)
                result_text += f"{i}. {url}\n"
                if output_file:
                    result_text += f"   📹 视频文件: {output_file}\n"
                if subtitle_file:
                    result_text += f"   📝 字幕文件: {subtitle_file}\n"
                if retry_with_cookies:
                    result_text += "   💡 使用 cookies 重试成功\n"
                result_text += "\n"
        if errors:
            result_text += "### ❌ 下载失败的视频：\n"
            for i, error in enumerate(errors, 1):
                url = error.get('url', 'N/A')
                error_msg = error.get('error', '未知错误')
                result_text += f"{i}. {url}\n"
                result_text += f"   错误: {error_msg}\n\n"
        return result_text
    else:
        if data:
            return json.dumps(data, ensure_ascii=False, indent=2)
        return "✅ 技能执行完成"
