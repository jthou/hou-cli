"""FFmpeg 工具 - 视频/音频处理工具集"""
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter

logger = logging.getLogger(__name__)


def _get_ffmpeg_path() -> Path:
    """获取 FFmpeg 可执行文件路径"""
    current_file = Path(__file__).resolve()
    # ffmpeg_tool.py 在 backend/core/agent/tools/builtin/
    # 向上找到包含 backend 目录的父目录，然后取其父目录作为项目根
    current = current_file.parent
    while current.name != 'backend' and len(current.parts) > 1:
        current = current.parent
    if current.name == 'backend':
        project_root = current.parent
    else:
        # 如果找不到，使用向上5级的方式（向后兼容）
        project_root = current_file.parent.parent.parent.parent.parent
    return project_root / "backend" / "externals" / "ffmpeg" / "build" / "bin" / "ffmpeg"


def _get_ffprobe_path() -> Path:
    """获取 FFprobe 可执行文件路径"""
    current_file = Path(__file__).resolve()
    current = current_file.parent
    while current.name != 'backend' and len(current.parts) > 1:
        current = current.parent
    if current.name == 'backend':
        project_root = current.parent
    else:
        project_root = current_file.parent.parent.parent.parent.parent
    return project_root / "backend" / "externals" / "ffmpeg" / "build" / "bin" / "ffprobe"


def _get_ffplay_path() -> Path:
    """获取 FFplay 可执行文件路径"""
    current_file = Path(__file__).resolve()
    current = current_file.parent
    while current.name != 'backend' and len(current.parts) > 1:
        current = current.parent
    if current.name == 'backend':
        project_root = current.parent
    else:
        project_root = current_file.parent.parent.parent.parent.parent
    return project_root / "backend" / "externals" / "ffmpeg" / "build" / "bin" / "ffplay"


def _find_ffmpeg_binary(name: str) -> Optional[Path]:
    """查找 FFmpeg 二进制文件（优先使用项目中的，否则查找系统 PATH）"""
    # 先尝试项目中的
    current_file = Path(__file__).resolve()
    current = current_file.parent
    while current.name != 'backend' and len(current.parts) > 1:
        current = current.parent
    if current.name == 'backend':
        project_root = current.parent
    else:
        project_root = current_file.parent.parent.parent.parent.parent
    
    project_binary = project_root / "backend" / "externals" / "ffmpeg" / "build" / "bin" / name
    if project_binary.exists():
        return project_binary
    
    # 查找系统 PATH
    import shutil
    system_binary = shutil.which(name)
    if system_binary:
        return Path(system_binary)
    
    return None


def _run_ffmpeg_command(binary: Path, args: List[str], input_file: Optional[Path] = None) -> Dict[str, Any]:
    """运行 FFmpeg 命令"""
    try:
        cmd = [str(binary)] + args
        logger.debug(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            input=str(input_file) if input_file else None
        )
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }


def _probe_media_file(file_path: Path) -> Dict[str, Any]:
    """使用 ffprobe 分析媒体文件"""
    ffprobe = _find_ffmpeg_binary('ffprobe')
    if not ffprobe:
        return {'success': False, 'error': 'ffprobe not found'}
    
    args = [
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        str(file_path)
    ]
    
    result = _run_ffmpeg_command(ffprobe, args)
    if not result['success']:
        return result
    
    try:
        import json
        data = json.loads(result['stdout'])
        return {
            'success': True,
            'data': data,
            'format': data.get('format', {}),
            'streams': data.get('streams', [])
        }
    except json.JSONDecodeError as e:
        return {
            'success': False,
            'error': f'Failed to parse ffprobe output: {str(e)}',
            'raw_output': result['stdout']
        }


def _extract_audio(input_file: Path, output_file: Path, audio_format: str = 'mp3', 
                   audio_quality: str = '192k') -> Dict[str, Any]:
    """提取音频"""
    ffmpeg = _find_ffmpeg_binary('ffmpeg')
    if not ffmpeg:
        return {'success': False, 'error': 'ffmpeg not found'}
    
    # 先检查是否有音频流
    probe_result = _probe_media_file(input_file)
    if not probe_result.get('success'):
        return {'success': False, 'error': '无法分析输入文件'}
    
    streams = probe_result.get('streams', [])
    audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
    if not audio_streams:
        return {'success': False, 'error': '输入文件不包含音频流'}
    
    args = ['-i', str(input_file), '-vn']  # 不包含视频
    
    # 检查编码器是否可用
    if audio_format == 'mp3':
        # 检查 libmp3lame 是否可用
        check_result = _run_ffmpeg_command(ffmpeg, ['-encoders'])
        if check_result.get('success') and 'libmp3lame' in check_result.get('stdout', ''):
            args.extend(['-acodec', 'libmp3lame', '-ab', audio_quality])
        else:
            # libmp3lame 不可用，使用 copy 或 aac
            logger.warning("libmp3lame 编码器不可用，使用 aac 编码器")
            # 如果输出是 mp3，改为 m4a
            if output_file.suffix.lower() == '.mp3':
                output_file = output_file.with_suffix('.m4a')
                logger.info(f"输出格式改为 m4a: {output_file}")
            args.extend(['-acodec', 'aac', '-ab', audio_quality])
    else:
        # 其他格式使用 copy
        args.extend(['-acodec', 'copy'])
    
    args.extend(['-y', str(output_file)])  # 覆盖输出文件
    
    return _run_ffmpeg_command(ffmpeg, args)


def _cut_video(input_file: Path, output_file: Path, start_time: str, 
               duration: Optional[str] = None, end_time: Optional[str] = None) -> Dict[str, Any]:
    """裁剪视频"""
    ffmpeg = _find_ffmpeg_binary('ffmpeg')
    if not ffmpeg:
        return {'success': False, 'error': 'ffmpeg not found'}
    
    args = ['-i', str(input_file), '-ss', start_time]
    
    if duration:
        args.extend(['-t', duration])
    elif end_time:
        # 计算时长
        args.extend(['-to', end_time])
    
    args.extend(['-c', 'copy', '-y', str(output_file)])
    
    return _run_ffmpeg_command(ffmpeg, args)


def _convert_format(input_file: Path, output_file: Path, 
                   video_codec: Optional[str] = None, 
                   audio_codec: Optional[str] = None,
                   quality: Optional[str] = None) -> Dict[str, Any]:
    """转换视频格式"""
    ffmpeg = _find_ffmpeg_binary('ffmpeg')
    if not ffmpeg:
        return {'success': False, 'error': 'ffmpeg not found'}
    
    args = ['-i', str(input_file)]
    
    # 如果指定了编码器，检查是否可用；否则使用 copy 模式
    if video_codec:
        # 检查编码器是否可用（通过尝试列出编码器）
        check_result = _run_ffmpeg_command(ffmpeg, ['-encoders'])
        if check_result.get('success') and video_codec not in check_result.get('stdout', ''):
            # 编码器不可用，使用 copy
            logger.warning(f"编码器 {video_codec} 不可用，使用 copy 模式")
            args.extend(['-c:v', 'copy'])
        else:
            args.extend(['-c:v', video_codec])
    else:
        args.extend(['-c:v', 'copy'])  # 默认使用 copy
    
    if audio_codec:
        args.extend(['-c:a', audio_codec])
    else:
        args.extend(['-c:a', 'copy'])  # 默认使用 copy
    
    if quality and video_codec:  # 只有重新编码时才使用 quality
        args.extend(['-crf', quality])
    
    args.extend(['-y', str(output_file)])
    
    return _run_ffmpeg_command(ffmpeg, args)


def _merge_videos(input_files: List[Path], output_file: Path) -> Dict[str, Any]:
    """合并多个视频文件"""
    ffmpeg = _find_ffmpeg_binary('ffmpeg')
    if not ffmpeg:
        return {'success': False, 'error': 'ffmpeg not found'}
    
    # 创建临时文件列表
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for input_file in input_files:
            f.write(f"file '{input_file.absolute()}'\n")
        concat_file = Path(f.name)
    
    try:
        args = [
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-c', 'copy',
            '-y',
            str(output_file)
        ]
        
        result = _run_ffmpeg_command(ffmpeg, args)
        return result
    finally:
        concat_file.unlink(missing_ok=True)


def _play_media(input_file: Path, start_time: Optional[str] = None, 
                duration: Optional[str] = None) -> Dict[str, Any]:
    """使用 ffplay 播放媒体文件"""
    ffplay = _find_ffmpeg_binary('ffplay')
    if not ffplay:
        return {'success': False, 'error': 'ffplay not found'}
    
    if not input_file.exists():
        return {'success': False, 'error': f'文件不存在: {input_file}'}
    
    args = []
    
    # 添加开始时间
    if start_time:
        args.extend(['-ss', start_time])
    
    # 添加持续时间
    if duration:
        args.extend(['-t', duration])
    
    # 添加输入文件
    args.append(str(input_file))
    
    # 添加其他选项
    args.extend(['-autoexit'])  # 播放完成后自动退出
    args.extend(['-nodisp'])  # 不显示窗口（用于音频）
    
    # ffplay 是交互式程序，需要在前台运行
    # 这里返回命令信息，实际播放由调用者决定
    return {
        'success': True,
        'command': [str(ffplay)] + args,
        'message': 'ffplay 需要在交互式环境中运行'
    }


class FFmpegTool(Tool):
    """FFmpeg 视频/音频处理工具
    
    提供视频和音频处理功能，包括：
    - 媒体文件分析（ffprobe）
    - 视频裁剪、合并、格式转换
    - 音频提取和处理
    - 复杂操作可通过编程方式完成
    
    注意：对于复杂的视频处理任务，建议使用编程方式调用 FFmpeg API 或编写脚本。
    """
    
    def __init__(self):
        """初始化 FFmpeg 工具"""
        parameters = [
            ToolParameter(
                name="operation",
                type="string",
                description="操作类型：'probe'（分析媒体文件）、'extract_audio'（提取音频）、'cut'（裁剪视频）、'convert'（转换格式）、'merge'（合并视频）、'play'（播放媒体文件）、'custom'（自定义命令）",
                required=True,
                enum=["probe", "extract_audio", "cut", "convert", "merge", "play", "custom"]
            ),
            ToolParameter(
                name="input_file",
                type="string",
                description="输入文件路径（必需，除了 merge 操作）",
                required=False
            ),
            ToolParameter(
                name="output_file",
                type="string",
                description="输出文件路径（必需，除了 probe 操作）",
                required=False
            ),
            ToolParameter(
                name="input_files",
                type="array",
                description="输入文件列表（仅用于 merge 操作）",
                required=False
            ),
            ToolParameter(
                name="start_time",
                type="string",
                description="开始时间（用于 cut 操作，格式：HH:MM:SS 或 秒数）",
                required=False
            ),
            ToolParameter(
                name="duration",
                type="string",
                description="持续时间（用于 cut 操作，格式：HH:MM:SS 或 秒数）",
                required=False
            ),
            ToolParameter(
                name="end_time",
                type="string",
                description="结束时间（用于 cut 操作，格式：HH:MM:SS 或 秒数）",
                required=False
            ),
            ToolParameter(
                name="audio_format",
                type="string",
                description="音频格式（用于 extract_audio，默认：mp3）",
                required=False,
                default="mp3",
                enum=["mp3", "wav", "aac", "flac", "ogg"]
            ),
            ToolParameter(
                name="audio_quality",
                type="string",
                description="音频质量（用于 extract_audio，默认：192k）",
                required=False,
                default="192k"
            ),
            ToolParameter(
                name="video_codec",
                type="string",
                description="视频编码器（用于 convert，如：libx264, libx265）",
                required=False
            ),
            ToolParameter(
                name="audio_codec",
                type="string",
                description="音频编码器（用于 convert，如：aac, mp3）",
                required=False
            ),
            ToolParameter(
                name="quality",
                type="string",
                description="视频质量（用于 convert，CRF 值，0-51，越小质量越好）",
                required=False
            ),
            ToolParameter(
                name="custom_args",
                type="array",
                description="自定义 FFmpeg 参数（用于 custom 操作，数组格式）",
                required=False
            ),
        ]
        
        super().__init__(
            name="ffmpeg",
            description=(
                "FFmpeg 视频/音频处理工具集。"
                "\n\n支持的操作："
                "\n1. probe - 分析媒体文件信息（使用 ffprobe）"
                "\n2. extract_audio - 从视频中提取音频"
                "\n3. cut - 裁剪视频片段"
                "\n4. convert - 转换视频/音频格式"
                "\n5. merge - 合并多个视频文件"
                "\n6. play - 播放媒体文件（使用 ffplay）"
                "\n7. custom - 执行自定义 FFmpeg 命令"
                "\n\n注意："
                "\n- 对于复杂的视频处理任务（如滤镜、特效、多轨道处理等），"
                "\n  建议使用编程方式调用 FFmpeg API 或编写脚本。"
                "\n- 本工具提供基础功能，复杂功能可通过 custom 操作或直接编程实现。"
            ),
            parameters=parameters
        )
    
    def execute(self, **kwargs) -> ToolResult:
        """执行 FFmpeg 操作"""
        try:
            operation = kwargs.get('operation')
            if not operation:
                return ToolResult(
                    success=False,
                    error="operation 参数是必需的"
                )
            
            # 检查 FFmpeg 是否可用
            ffmpeg = _find_ffmpeg_binary('ffmpeg')
            if not ffmpeg:
                return ToolResult(
                    success=False,
                    error="FFmpeg 未找到。请确保已编译 FFmpeg 或系统已安装 FFmpeg。"
                )
            
            if operation == 'probe':
                return self._execute_probe(kwargs)
            elif operation == 'extract_audio':
                return self._execute_extract_audio(kwargs)
            elif operation == 'cut':
                return self._execute_cut(kwargs)
            elif operation == 'convert':
                return self._execute_convert(kwargs)
            elif operation == 'merge':
                return self._execute_merge(kwargs)
            elif operation == 'play':
                return self._execute_play(kwargs)
            elif operation == 'custom':
                return self._execute_custom(kwargs)
            else:
                return ToolResult(
                    success=False,
                    error=f"未知操作: {operation}"
                )
        except Exception as e:
            logger.exception("FFmpeg 操作失败")
            return ToolResult(
                success=False,
                error=f"FFmpeg 操作失败: {str(e)}"
            )
    
    def _execute_probe(self, kwargs: Dict[str, Any]) -> ToolResult:
        """执行媒体文件分析"""
        input_file = kwargs.get('input_file')
        if not input_file:
            return ToolResult(success=False, error="input_file 参数是必需的")
        
        input_path = Path(input_file).expanduser()
        if not input_path.exists():
            return ToolResult(success=False, error=f"文件不存在: {input_file}")
        
        result = _probe_media_file(input_path)
        if not result.get('success'):
            return ToolResult(success=False, error=result.get('error', '分析失败'))
        
        format_info = result.get('format', {})
        streams = result.get('streams', [])
        
        # 提取关键信息
        video_streams = [s for s in streams if s.get('codec_type') == 'video']
        audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
        
        return ToolResult(
            success=True,
            data={
                'file': str(input_path),
                'format': format_info.get('format_name', ''),
                'duration': format_info.get('duration', ''),
                'size': format_info.get('size', ''),
                'bitrate': format_info.get('bit_rate', ''),
                'video_streams': len(video_streams),
                'audio_streams': len(audio_streams),
                'streams': streams,
                'full_info': result.get('data', {})
            }
        )
    
    def _execute_extract_audio(self, kwargs: Dict[str, Any]) -> ToolResult:
        """执行音频提取"""
        input_file = kwargs.get('input_file')
        output_file = kwargs.get('output_file')
        if not input_file or not output_file:
            return ToolResult(success=False, error="input_file 和 output_file 参数是必需的")
        
        input_path = Path(input_file).expanduser()
        output_path = Path(output_file).expanduser()
        
        if not input_path.exists():
            return ToolResult(success=False, error=f"输入文件不存在: {input_file}")
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        audio_format = kwargs.get('audio_format', 'mp3')
        audio_quality = kwargs.get('audio_quality', '192k')
        
        result = _extract_audio(input_path, output_path, audio_format, audio_quality)
        
        if result.get('success'):
            return ToolResult(
                success=True,
                data={
                    'input_file': str(input_path),
                    'output_file': str(output_path),
                    'format': audio_format,
                    'quality': audio_quality
                }
            )
        else:
            return ToolResult(
                success=False,
                error=result.get('error', result.get('stderr', '音频提取失败'))
            )
    
    def _execute_cut(self, kwargs: Dict[str, Any]) -> ToolResult:
        """执行视频裁剪"""
        input_file = kwargs.get('input_file')
        output_file = kwargs.get('output_file')
        start_time = kwargs.get('start_time')
        
        if not input_file or not output_file or not start_time:
            return ToolResult(
                success=False,
                error="input_file、output_file 和 start_time 参数是必需的"
            )
        
        input_path = Path(input_file).expanduser()
        output_path = Path(output_file).expanduser()
        
        if not input_path.exists():
            return ToolResult(success=False, error=f"输入文件不存在: {input_file}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        duration = kwargs.get('duration')
        end_time = kwargs.get('end_time')
        
        if not duration and not end_time:
            return ToolResult(
                success=False,
                error="duration 或 end_time 参数至少需要一个"
            )
        
        result = _cut_video(input_path, output_path, start_time, duration, end_time)
        
        if result.get('success'):
            return ToolResult(
                success=True,
                data={
                    'input_file': str(input_path),
                    'output_file': str(output_path),
                    'start_time': start_time,
                    'duration': duration,
                    'end_time': end_time
                }
            )
        else:
            return ToolResult(
                success=False,
                error=result.get('error', result.get('stderr', '视频裁剪失败'))
            )
    
    def _execute_convert(self, kwargs: Dict[str, Any]) -> ToolResult:
        """执行格式转换"""
        input_file = kwargs.get('input_file')
        output_file = kwargs.get('output_file')
        
        if not input_file or not output_file:
            return ToolResult(success=False, error="input_file 和 output_file 参数是必需的")
        
        input_path = Path(input_file).expanduser()
        output_path = Path(output_file).expanduser()
        
        if not input_path.exists():
            return ToolResult(success=False, error=f"输入文件不存在: {input_file}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        video_codec = kwargs.get('video_codec')
        audio_codec = kwargs.get('audio_codec')
        quality = kwargs.get('quality')
        
        result = _convert_format(input_path, output_path, video_codec, audio_codec, quality)
        
        if result.get('success'):
            return ToolResult(
                success=True,
                data={
                    'input_file': str(input_path),
                    'output_file': str(output_path),
                    'video_codec': video_codec,
                    'audio_codec': audio_codec,
                    'quality': quality
                }
            )
        else:
            return ToolResult(
                success=False,
                error=result.get('error', result.get('stderr', '格式转换失败'))
            )
    
    def _execute_merge(self, kwargs: Dict[str, Any]) -> ToolResult:
        """执行视频合并"""
        input_files = kwargs.get('input_files')
        output_file = kwargs.get('output_file')
        
        if not input_files or not output_file:
            return ToolResult(success=False, error="input_files 和 output_file 参数是必需的")
        
        if not isinstance(input_files, list) or len(input_files) < 2:
            return ToolResult(success=False, error="input_files 必须包含至少 2 个文件")
        
        input_paths = [Path(f).expanduser() for f in input_files]
        output_path = Path(output_file).expanduser()
        
        for input_path in input_paths:
            if not input_path.exists():
                return ToolResult(success=False, error=f"输入文件不存在: {input_path}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        result = _merge_videos(input_paths, output_path)
        
        if result.get('success'):
            return ToolResult(
                success=True,
                data={
                    'input_files': [str(p) for p in input_paths],
                    'output_file': str(output_path)
                }
            )
        else:
            return ToolResult(
                success=False,
                error=result.get('error', result.get('stderr', '视频合并失败'))
            )
    
    def _execute_play(self, kwargs: Dict[str, Any]) -> ToolResult:
        """执行媒体播放"""
        input_file = kwargs.get('input_file')
        if not input_file:
            return ToolResult(success=False, error="input_file 参数是必需的")
        
        input_path = Path(input_file).expanduser()
        
        if not input_path.exists():
            return ToolResult(success=False, error=f"文件不存在: {input_file}")
        
        start_time = kwargs.get('start_time')
        duration = kwargs.get('duration')
        
        result = _play_media(input_path, start_time, duration)
        
        if result.get('success'):
            command = result.get('command', [])
            return ToolResult(
                success=True,
                data={
                    'input_file': str(input_path),
                    'command': ' '.join(command),
                    'message': 'ffplay 需要在交互式环境中运行。可以使用 subprocess 执行命令。',
                    'note': '注意：ffplay 是图形界面程序，需要在有图形环境的终端中运行'
                }
            )
        else:
            return ToolResult(
                success=False,
                error=result.get('error', '播放失败')
            )
    
    def _execute_custom(self, kwargs: Dict[str, Any]) -> ToolResult:
        """执行自定义 FFmpeg 命令"""
        custom_args = kwargs.get('custom_args')
        if not custom_args:
            return ToolResult(success=False, error="custom_args 参数是必需的（数组格式）")
        
        if not isinstance(custom_args, list):
            return ToolResult(success=False, error="custom_args 必须是数组格式")
        
        ffmpeg = _find_ffmpeg_binary('ffmpeg')
        if not ffmpeg:
            return ToolResult(success=False, error="ffmpeg not found")
        
        # 检查是否是查询命令（不需要输出文件）
        query_commands = ['-version', '-encoders', '-decoders', '-formats', '-codecs', '-filters', '-hide_banner']
        is_query = any(arg in query_commands for arg in custom_args)
        
        # 如果不是查询命令，检查是否有输出文件
        if not is_query and not any(arg.startswith('-') or arg.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm', '.mp3', '.wav', '.aac')) for arg in custom_args):
            return ToolResult(
                success=False,
                error="自定义命令必须指定输出文件，或使用查询命令（如 -version, -encoders 等）"
            )
        
        result = _run_ffmpeg_command(ffmpeg, custom_args)
        
        # 对于查询命令，即使返回码非0也可能有输出
        if is_query or result.get('success'):
            return ToolResult(
                success=True,
                data={
                    'command': ' '.join([str(ffmpeg)] + custom_args),
                    'stdout': result.get('stdout', ''),
                    'stderr': result.get('stderr', '')
                }
            )
        else:
            return ToolResult(
                success=False,
                error=result.get('error', result.get('stderr', '自定义命令执行失败'))
            )

