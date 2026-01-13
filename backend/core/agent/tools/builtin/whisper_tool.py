"""Whisper 语音转文字工具"""
import logging
import sys
import os
import threading
import time
import re
from pathlib import Path
from typing import Optional, Callable
from io import StringIO

from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter

logger = logging.getLogger(__name__)

# 设置环境变量以避免段错误
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')


def _get_whisper_path() -> Path:
    """获取 Whisper 路径"""
    current_file = Path(__file__).resolve()
    current = current_file.parent
    while current.name != 'backend' and len(current.parts) > 1:
        current = current.parent
    if current.name == 'backend':
        project_root = current.parent
    else:
        project_root = current_file.parent.parent.parent.parent.parent
    return project_root / "backend" / "externals" / "whisper"


def _get_ffmpeg_bin_dir() -> Path:
    """获取 FFmpeg bin 目录路径"""
    current_file = Path(__file__).resolve()
    current = current_file.parent
    while current.name != 'backend' and len(current.parts) > 1:
        current = current.parent
    if current.name == 'backend':
        project_root = current.parent
    else:
        project_root = current_file.parent.parent.parent.parent.parent
    return project_root / "backend" / "externals" / "ffmpeg" / "build" / "bin"


def _get_ffmpeg_lib_dir() -> Path:
    """获取 FFmpeg lib 目录路径"""
    ffmpeg_bin_dir = _get_ffmpeg_bin_dir()
    # lib 目录在 bin 目录的同一级
    return ffmpeg_bin_dir.parent / "lib"


def _setup_ffmpeg_path():
    """设置 FFmpeg 路径到环境变量 PATH 和 LD_LIBRARY_PATH 中，确保 Whisper 能找到 ffmpeg 及其共享库"""
    ffmpeg_bin_dir = _get_ffmpeg_bin_dir()
    ffmpeg_lib_dir = _get_ffmpeg_lib_dir()
    
    if ffmpeg_bin_dir.exists() and (ffmpeg_bin_dir / "ffmpeg").exists():
        # 设置 PATH，确保能找到 ffmpeg 可执行文件
        ffmpeg_bin_str = str(ffmpeg_bin_dir)
        current_path = os.environ.get('PATH', '')
        if ffmpeg_bin_str not in current_path:
            os.environ['PATH'] = f"{ffmpeg_bin_str}:{current_path}"
            logger.debug(f"已添加 FFmpeg 路径到 PATH: {ffmpeg_bin_str}")
        
        # 设置 LD_LIBRARY_PATH，确保能找到 FFmpeg 的共享库
        if ffmpeg_lib_dir.exists():
            ffmpeg_lib_str = str(ffmpeg_lib_dir)
            current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
            if ffmpeg_lib_str not in current_ld_path:
                os.environ['LD_LIBRARY_PATH'] = f"{ffmpeg_lib_str}:{current_ld_path}" if current_ld_path else ffmpeg_lib_str
                logger.debug(f"已添加 FFmpeg 库路径到 LD_LIBRARY_PATH: {ffmpeg_lib_str}")
        else:
            logger.warning(f"FFmpeg 库路径不存在: {ffmpeg_lib_dir}")
    else:
        logger.warning(f"FFmpeg 路径不存在: {ffmpeg_bin_dir}")


class WhisperProgressCapture:
    """捕获 Whisper 的 stderr 输出并解析进度，同时实时写入 SRT 文件"""
    
    def __init__(self, progress_callback: Optional[Callable[[str], None]], srt_file_path: Optional[Path] = None):
        """
        初始化进度捕获器
        
        Args:
            progress_callback: 进度回调函数，接收进度消息字符串
            srt_file_path: SRT 文件路径，如果提供则实时写入
        """
        self.progress_callback = progress_callback
        self.srt_file_path = srt_file_path
        self.srt_file = None
        self.srt_segment_count = 0
        self.srt_lock = threading.Lock()  # 文件写入锁
        self.buffer = StringIO()
        self.capture_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.original_stderr = None
        self.original_stdout = None
        self.last_pos = 0
        self.processed_segments = set()  # 记录已处理的段落（避免重复写入）
        self.processed_segments = set()  # 记录已处理的段落（避免重复写入）
    
    def __enter__(self):
        """进入上下文管理器"""
        # 保存原始 stderr 和 stdout（tqdm 可能使用 stdout）
        self.original_stderr = sys.stderr
        self.original_stdout = sys.stdout
        # 创建缓冲区（同时捕获 stdout 和 stderr）
        self.buffer = StringIO()
        # 重定向到缓冲区
        sys.stderr = self.buffer
        sys.stdout = self.buffer  # tqdm 使用 stdout
        # 重置位置
        self.last_pos = 0
        self.processed_segments = set()
        self.srt_segment_count = 0
        
        # 如果提供了 SRT 文件路径，打开文件准备写入
        if self.srt_file_path:
            try:
                # 确保目录存在
                self.srt_file_path.parent.mkdir(parents=True, exist_ok=True)
                # 以追加模式打开（如果文件已存在，清空它）
                self.srt_file = open(self.srt_file_path, 'w', encoding='utf-8')
                logger.debug(f"[Whisper 捕获] 已打开 SRT 文件准备实时写入: {self.srt_file_path}")
            except Exception as e:
                logger.warning(f"[Whisper 捕获] 无法打开 SRT 文件: {e}")
                self.srt_file = None
        
        # 启动后台线程读取缓冲区
        self.capture_thread = threading.Thread(
            target=self._read_buffer,
            daemon=True
        )
        self.capture_thread.start()
        logger.debug("[Whisper 捕获] 已启动 stdout/stderr 捕获")
        return self
    
    def __exit__(self, *args):
        """退出上下文管理器"""
        # 恢复原始 stderr 和 stdout
        if self.original_stderr:
            sys.stderr = self.original_stderr
        if self.original_stdout:
            sys.stdout = self.original_stdout
        # 停止读取线程
        self.stop_event.set()
        if self.capture_thread:
            self.capture_thread.join(timeout=1)
        # 读取剩余内容
        self._read_remaining()
        # 关闭 SRT 文件
        if self.srt_file:
            try:
                self.srt_file.flush()
                self.srt_file.close()
                logger.debug(f"[Whisper 捕获] 已关闭 SRT 文件: {self.srt_file_path}")
            except Exception as e:
                logger.warning(f"[Whisper 捕获] 关闭 SRT 文件时出错: {e}")
            finally:
                self.srt_file = None
        # 关闭 SRT 文件
        if self.srt_file:
            try:
                self.srt_file.flush()
                self.srt_file.close()
                logger.debug(f"[Whisper 捕获] 已关闭 SRT 文件: {self.srt_file_path}")
            except Exception as e:
                logger.warning(f"[Whisper 捕获] 关闭 SRT 文件时出错: {e}")
            finally:
                self.srt_file = None
    
    def _read_buffer(self):
        """后台线程读取缓冲区内容"""
        last_progress_time = time.time()
        check_count = 0
        while not self.stop_event.is_set():
            try:
                # 强制刷新缓冲区（确保内容被写入）
                if hasattr(self.buffer, 'flush'):
                    self.buffer.flush()
                
                content = self.buffer.getvalue()
                if len(content) > self.last_pos:
                    new_content = content[self.last_pos:]
                    # 处理 \r 覆盖：提取最后一行（tqdm 使用 \r 覆盖当前行）
                    # 如果包含 \r，只保留最后一个 \r 之后的内容
                    if '\r' in new_content:
                        # 找到最后一个 \r 之后的内容
                        lines = new_content.split('\r')
                        new_content = lines[-1] if lines else new_content
                        logger.debug(f"[Whisper 捕获] 检测到 \\r 覆盖，提取最后一行: {repr(new_content[:100])}")
                    
                    # 调试：打印捕获到的内容（使用 logger.info 确保能看到）
                    if new_content.strip():
                        logger.info(f"[Whisper 捕获] 新内容 (长度: {len(new_content)}): {repr(new_content[:500])}")
                    # 解析进度信息
                    progress_msg = self._parse_progress(new_content)
                    if progress_msg and self.progress_callback:
                        logger.info(f"[Whisper 进度] 解析成功: {progress_msg}")
                        self.progress_callback(progress_msg)
                        last_progress_time = time.time()  # 更新最后进度时间
                    elif new_content.strip():
                        logger.info(f"[Whisper 进度] 解析失败，原始内容: {repr(new_content[:500])}")
                    self.last_pos = len(content)
                
                # 定期打印调试信息（每10次检查打印一次）
                check_count += 1
                if check_count % 10 == 0:
                    total_content = self.buffer.getvalue()
                    logger.debug(f"[Whisper 捕获] 检查 #{check_count}, 缓冲区总长度: {len(total_content)}, 已读取: {self.last_pos}")
                
                # 如果超过15秒没有进度消息，发送心跳消息
                current_time = time.time()
                if (current_time - last_progress_time) >= 15.0 and self.progress_callback:
                    self.progress_callback("正在处理音频，请稍候...")
                    last_progress_time = current_time
                
                time.sleep(0.5)  # 每0.5秒检查一次
            except Exception as e:
                logger.warning(f"进度捕获错误: {e}", exc_info=True)
                break
    
    def _read_remaining(self):
        """读取剩余内容（在退出时调用）"""
        try:
            content = self.buffer.getvalue()
            if len(content) > self.last_pos:
                new_content = content[self.last_pos:]
                progress_msg = self._parse_progress(new_content)
                if progress_msg and self.progress_callback:
                    self.progress_callback(progress_msg)
        except Exception as e:
            logger.warning(f"读取剩余进度错误: {e}")
    
    def _parse_progress(self, content: str) -> Optional[str]:
        """解析 Whisper 进度输出
        
        Whisper 有两种输出格式：
        1. 进度条格式（verbose=False 时）：[00:00 > 00:05, 0.00x]
        2. 转录文本格式（verbose=True 时）：[00:00.000 --> 00:04.400] 文本内容
        
        Returns:
            格式化的进度消息，如果无法解析则返回 None
        """
        if not content:
            return None
        
        # 调试：打印原始内容
        logger.debug(f"[Whisper 解析] 尝试解析内容: {repr(content[:200])}")
        
        # 方法1：匹配进度条格式 [HH:MM > HH:MM, X.XXx]
        progress_patterns = [
            r'\[(\d{2}:\d{2})\s*>\s*(\d{2}:\d{2}),\s*([\d.]+)x',  # 标准格式
            r'\[(\d{1,2}:\d{2})\s*>\s*(\d{1,2}:\d{2}),\s*([\d.]+)x',  # 允许单数字小时
            r'\[(\d+:\d{2})\s*>\s*(\d+:\d{2}),\s*([\d.]+)x',  # 更灵活的格式
        ]
        
        for pattern in progress_patterns:
            matches = re.findall(pattern, content)
            if matches:
                logger.debug(f"[Whisper 解析] 使用进度条模式匹配成功: {pattern}, 匹配数: {len(matches)}")
                current_time, total_time, speed = matches[-1]
                try:
                    # 尝试计算百分比
                    current_min, current_sec = map(int, current_time.split(':'))
                    total_min, total_sec = map(int, total_time.split(':'))
                    current_total = current_min * 60 + current_sec
                    total_total = total_min * 60 + total_sec
                    
                    if total_total > 0:
                        percentage = min(100, (current_total / total_total) * 100)
                        result = f"转录进行中... [{current_time} / {total_time}, {speed}x, {percentage:.1f}%]"
                        logger.debug(f"[Whisper 解析] 生成进度消息: {result}")
                        return result
                    else:
                        result = f"转录进行中... [{current_time} / {total_time}, {speed}x]"
                        return result
                except (ValueError, ZeroDivisionError) as e:
                    logger.debug(f"[Whisper 解析] 计算百分比失败: {e}")
                    result = f"转录进行中... [{current_time} / {total_time}, {speed}x]"
                    return result
        
        # 方法2：从转录文本中提取时间戳（verbose=True 时的格式）
        # 格式：[00:00.000 --> 00:04.400] 文本
        # 完整格式：提取时间戳和文本内容
        transcript_pattern = r'\[(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2})\.(\d{3})\]\s*(.+)'
        transcript_matches = re.findall(transcript_pattern, content)
        
        if transcript_matches:
            # 处理每个匹配的段落
            for match in transcript_matches:
                start_h, start_m, start_ms, end_h, end_m, end_ms, text = match
                # 创建段落的唯一标识（基于时间戳）
                segment_key = (start_h, start_m, start_ms, end_h, end_m, end_ms)
                
                # 如果这个段落还没有处理过，写入 SRT 文件
                if segment_key not in self.processed_segments:
                    self.processed_segments.add(segment_key)
                    self._write_srt_segment(
                        int(start_h), int(start_m), int(start_ms),
                        int(end_h), int(end_m), int(end_ms),
                        text.strip()
                    )
            
            # 取最后一个时间戳的结束时间作为当前进度
            last_match = transcript_matches[-1]
            end_h, end_m, end_ms = map(int, last_match[3:6])
            end_seconds = end_h * 3600 + end_m * 60 + end_ms / 1000.0
            
            # 计算已转录的文本行数
            line_count = len(transcript_matches)
            
            # 格式化时间
            end_min = int(end_seconds // 60)
            end_sec = int(end_seconds % 60)
            time_str = f"{end_min:02d}:{end_sec:02d}"
            
            result = f"转录进行中... 已转录 {line_count} 段，当前时间: {time_str}"
            logger.debug(f"[Whisper 解析] 从转录文本提取进度: {result}")
            return result
        
        logger.debug(f"[Whisper 解析] 未找到匹配的进度格式")
        return None
    
    def _write_srt_segment(self, start_h: int, start_m: int, start_ms: int,
                          end_h: int, end_m: int, end_ms: int, text: str):
        """实时写入一个 SRT 段落到文件"""
        if not self.srt_file:
            return
        
        try:
            with self.srt_lock:
                self.srt_segment_count += 1
                # SRT 时间格式：HH:MM:SS,mmm
                # 从 Whisper 输出格式 [HH:MM.SSS --> HH:MM.SSS] 中提取的
                # 格式说明：HH:MM.SSS 表示 小时:分钟.秒.毫秒
                # 但正则表达式提取的是：HH, MM, SSS(毫秒部分，0-999)
                # 实际上，Whisper 输出中的格式是：MM:SS.mmm（分钟:秒.毫秒）
                # 所以 start_h 和 end_h 实际上是分钟，start_m 和 end_m 是秒，start_ms 和 end_ms 是毫秒
                # 但为了兼容，我们假设提取的是：HH(小时), MM(分钟), SSS(秒的整数部分*1000 + 毫秒)
                # 实际上，从正则表达式看：(\d{2}):(\d{2})\.(\d{3})
                # 第一个是小时或分钟，第二个是分钟或秒，第三个是毫秒
                # 查看 Whisper 源码，格式是 [HH:MM:SS.mmm --> HH:MM:SS.mmm] 或 [MM:SS.mmm --> MM:SS.mmm]
                # 为了安全，我们假设是 MM:SS.mmm 格式（更常见）
                # 所以：start_m 是分钟，start_ms 需要解析为秒和毫秒
                # 但正则表达式提取的第三个数字是3位数字，应该是毫秒（0-999）
                # 所以实际上：start_h=小时(可能为0), start_m=分钟, start_ms=毫秒(0-999)
                # 但 Whisper 输出可能是 [00:04.400] 格式，表示 0分4秒400毫秒
                # 所以：start_h=0(小时), start_m=0(分钟), start_ms=0(毫秒)
                # 但这样不对，应该是：start_h=0(小时), start_m=0(分钟), start_ms=0(毫秒)
                # 重新理解：从正则表达式 r'\[(\d{2}):(\d{2})\.(\d{3})' 提取
                # [00:04.400] -> start_h=00, start_m=04, start_ms=400
                # 这表示：0小时4分钟400毫秒？不对，应该是0分4秒400毫秒
                # 所以：start_h 实际上是分钟，start_m 是秒，start_ms 是毫秒
                # 但为了兼容 HH:MM:SS.mmm 格式，我们假设：
                # - 如果 start_h < 60，则 start_h 是分钟，start_m 是秒
                # - 否则，start_h 是小时，start_m 是分钟，需要从 start_ms 中提取秒
                # 简化：假设格式是 MM:SS.mmm（分钟:秒.毫秒）
                # 所以：start_h 是分钟，start_m 是秒，start_ms 是毫秒（0-999）
                # 转换为 SRT 格式：HH:MM:SS,mmm（小时:分钟:秒,毫秒）
                # 假设总时长不超过1小时，则：00:MM:SS,mmm
                start_str = f"00:{start_h:02d}:{start_m:02d},{start_ms:03d}"
                end_str = f"00:{end_h:02d}:{end_m:02d},{end_ms:03d}"
                
                self.srt_file.write(f"{self.srt_segment_count}\n")
                self.srt_file.write(f"{start_str} --> {end_str}\n")
                self.srt_file.write(f"{text}\n\n")
                self.srt_file.flush()  # 立即刷新到磁盘
                
                logger.debug(f"[Whisper 写入] 已写入段落 #{self.srt_segment_count}: {start_str} --> {end_str}")
        except Exception as e:
            logger.warning(f"[Whisper 写入] 写入 SRT 段落失败: {e}")


def _load_whisper_model(model_name: str = "base"):
    """加载 Whisper 模型"""
    whisper_path = _get_whisper_path()
    if not whisper_path.exists():
        raise ImportError(f"Whisper not found at {whisper_path}")
    
    if str(whisper_path) not in sys.path:
        sys.path.insert(0, str(whisper_path))
    
    # 尝试导入 whisper，如果失败则提供更详细的错误信息
    try:
        # 先尝试导入 torch（Whisper 的主要依赖）
        try:
            import torch
            logger.debug(f"PyTorch 已导入，版本: {torch.__version__}")
        except ImportError as torch_error:
            raise ImportError(
                f"Whisper 依赖未正确安装: PyTorch 未找到 ({torch_error})\n"
                f"请确保已安装 Whisper 及其依赖（包括 PyTorch）。\n"
                f"Whisper 路径: {whisper_path}\n"
                f"建议运行: pip install openai-whisper 或使用项目的 prepare-deps.sh 脚本"
            ) from torch_error
        
        # 然后导入 whisper
        import whisper
        logger.debug(f"Whisper 已导入，路径: {whisper_path}")
    except ImportError as e:
        error_msg = str(e)
        if 'torch' in error_msg.lower():
            raise ImportError(
                f"Whisper 依赖未正确安装: {error_msg}\n"
                f"请确保已安装 Whisper 及其依赖（包括 PyTorch）。\n"
                f"Whisper 路径: {whisper_path}\n"
                f"建议运行: pip install openai-whisper 或使用项目的 prepare-deps.sh 脚本"
            ) from e
        raise
    
    return whisper.load_model(model_name)


class WhisperTool(Tool):
    """Whisper 语音转文字工具 - 支持精确的时间戳"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="audio_file",
                type="string",
                description="音频文件路径（支持 mp3, wav, m4a, flac 等格式）",
                required=True
            ),
            ToolParameter(
                name="language",
                type="string",
                description="音频语言代码（如：zh, en, ja），如果为 'auto' 则自动检测",
                required=False,
                default="auto"
            ),
            ToolParameter(
                name="model",
                type="string",
                description="Whisper 模型大小：tiny, base, small, medium, large（越大越准确但越慢）",
                required=False,
                default="base",
                enum=["tiny", "base", "small", "medium", "large"]
            ),
            ToolParameter(
                name="output_file",
                type="string",
                description="输出 SRT 字幕文件路径（可选，如果不指定则自动生成，格式：{音频文件名}_transcription.srt）",
                required=False
            ),
        ]
        
        super().__init__(
            name="whisper",
            description=(
                "语音转文字工具，使用 OpenAI Whisper 模型进行高精度语音识别。"
                "支持多种音频格式（mp3, wav, m4a, flac 等），"
                "输出 SRT 字幕格式文件，包含精确的段落级别时间戳（精确到 0.01 秒），"
                "支持多语言识别和自动语言检测。"
                "\n\n重要：默认会转录完整的音频文件，除非明确指定了时间范围。"
                "输出格式：仅支持 SRT 字幕格式（.srt），包含时间戳和文本内容。"
                "注意：当前版本使用段落级别时间戳（已足够精确），"
                "单词级别时间戳在 macOS ARM 上会导致段错误，因此已禁用。"
            ),
            parameters=parameters
        )
    
    def _write_srt_from_result(self, result: dict, output_path: Path) -> Optional[Path]:
        """从转录结果中写入 SRT 文件（备用方案，如果实时写入失败）"""
        try:
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入 SRT 格式字幕文件
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, seg in enumerate(result['segments'], 1):
                    start = seg['start']
                    end = seg['end']
                    # SRT 时间格式：HH:MM:SS,mmm
                    start_str = f"{int(start//3600):02d}:{int((start%3600)//60):02d}:{int(start%60):02d},{int((start%1)*1000):03d}"
                    end_str = f"{int(end//3600):02d}:{int((end%3600)//60):02d}:{int(end%60):02d},{int((end%1)*1000):03d}"
                    f.write(f"{i}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{seg['text']}\n\n")
            
            logger.info(f"已从结果中保存 SRT 字幕文件: {output_path}")
            
            # 验证文件是否真的创建成功
            if not output_path.exists():
                raise FileNotFoundError(f"文件保存失败: {output_path} 不存在")
            
            return output_path
        except (IOError, OSError, PermissionError) as e:
            error_msg = f"保存 SRT 字幕文件失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None
    
    def execute(self, **kwargs) -> ToolResult:
        """执行语音转文字"""
        try:
            audio_file = kwargs.get("audio_file")
            if not audio_file:
                return ToolResult(
                    success=False,
                    error="缺少必需参数：audio_file"
                )
            
            # 解析参数
            audio_path = Path(audio_file).expanduser()
            if not audio_path.exists():
                return ToolResult(
                    success=False,
                    error=f"音频文件不存在: {audio_file}"
                )
            
            language = kwargs.get("language", "auto")
            if language == "auto":
                language = None
            
            model_name = kwargs.get("model", "base")
            output_file = kwargs.get("output_file")
            
            # 设置 FFmpeg 路径（Whisper 需要 ffmpeg 来加载音频文件）
            _setup_ffmpeg_path()
            
            # 加载模型
            logger.info(f"加载 Whisper 模型: {model_name}")
            self.report_progress(f"正在加载 Whisper 模型: {model_name}...")
            model = _load_whisper_model(model_name)
            self.report_progress(f"模型加载完成: {model_name}")
            
            # 获取音频文件时长（用于进度估算）
            try:
                from backend.core.agent.tools.builtin.ffmpeg_tool import FFmpegTool
                ffmpeg_tool = FFmpegTool()
                probe_result = ffmpeg_tool.execute(operation="probe", input_file=str(audio_path))
                if probe_result.success and probe_result.data:
                    duration_sec = float(probe_result.data.get('format', {}).get('duration', 0))
                    duration_min = int(duration_sec // 60)
                    duration_sec_remain = int(duration_sec % 60)
                    logger.info(f"音频文件时长: {duration_min:02d}:{duration_sec_remain:02d} ({duration_sec:.1f} 秒)")
            except Exception as e:
                logger.warning(f"无法获取音频时长: {e}")
                duration_sec = None
            
            # 创建进度报告线程
            progress_stop = threading.Event()
            progress_thread = None
            transcription_start_time = time.time()
            
            def report_progress():
                """定期报告进度（作为备用，如果 stderr 捕获失败）"""
                start_time = transcription_start_time
                last_report = start_time
                report_interval = 15  # 每15秒报告一次，保持连接活跃
                
                while not progress_stop.is_set():
                    elapsed = time.time() - start_time
                    elapsed_min = int(elapsed // 60)
                    elapsed_sec = int(elapsed % 60)
                    
                    if elapsed - last_report >= report_interval:
                        if duration_sec:
                            # 估算进度（基于时间，实际进度可能不同）
                            estimated_progress = min(100, (elapsed / (duration_sec * 0.1)) * 100)  # 假设处理速度是音频时长的10倍
                            progress_msg = f"转录进行中... 已用时: {elapsed_min:02d}:{elapsed_sec:02d}, 估算进度: {estimated_progress:.1f}%"
                            logger.info(progress_msg)
                            # 通过进度回调报告
                            if hasattr(self, 'report_progress'):
                                self.report_progress(progress_msg)
                        else:
                            progress_msg = f"转录进行中... 已用时: {elapsed_min:02d}:{elapsed_sec:02d}"
                            logger.info(progress_msg)
                            # 通过进度回调报告
                            if hasattr(self, 'report_progress'):
                                self.report_progress(progress_msg)
                        last_report = elapsed
                    
                    time.sleep(2)  # 每2秒检查一次
            
            # 启动进度报告线程（作为备用，如果 stderr 捕获失败）
            progress_thread = threading.Thread(target=report_progress, daemon=True)
            progress_thread.start()
            logger.info(f"开始转录: {audio_path}")
            
            # 确定输出文件路径（在转录开始前）
            output_path = None
            if output_file:
                output_path = Path(output_file).expanduser()
                # 确保扩展名是 .srt
                if output_path.suffix.lower() != '.srt':
                    output_path = output_path.with_suffix('.srt')
            else:
                # 自动生成输出文件名（SRT 格式）
                output_path = audio_path.parent / f"{audio_path.stem}_transcription.srt"
            
            try:
                # 创建进度捕获器（捕获 Whisper 的 stderr 输出，并实时写入 SRT 文件）
                progress_capture = WhisperProgressCapture(
                    progress_callback=lambda msg: self.report_progress(msg),
                    srt_file_path=output_path  # 传入 SRT 文件路径，实时写入
                )
                
                # 执行转录（启用 verbose 以获取更多信息）
                with progress_capture:
                    result = model.transcribe(
                        str(audio_path),
                        language=language,
                        word_timestamps=False,  # 禁用单词级别时间戳（避免段错误）
                        verbose=True,  # 启用详细输出以显示进度
                        fp16=False,
                        temperature=0.0,
                        best_of=1,
                        beam_size=1
                    )
                
                # 转录完成
                total_time = time.time() - transcription_start_time
                total_min = int(total_time // 60)
                total_sec = int(total_time % 60)
                completion_msg = f"转录完成！总用时: {total_min:02d}:{total_sec:02d}"
                logger.info(completion_msg)
                self.report_progress(completion_msg)
            finally:
                # 停止进度报告
                progress_stop.set()
                if progress_thread:
                    progress_thread.join(timeout=1)
            
            # 验证实时写入的文件（进度捕获器已经在转录过程中实时写入了）
            try:
                if not output_path.exists():
                    logger.warning(f"实时写入的 SRT 文件不存在，尝试从结果中写入: {output_path}")
                    output_path = self._write_srt_from_result(result, output_path)
                else:
                    # 检查文件是否有内容（可能实时写入失败）
                    file_size = output_path.stat().st_size
                    if file_size == 0:
                        logger.warning(f"实时写入的 SRT 文件为空，从结果中重新写入: {output_path}")
                        output_path = self._write_srt_from_result(result, output_path)
                    else:
                        logger.info(f"SRT 字幕文件已实时写入完成: {output_path} ({file_size} 字节)")
            except Exception as e:
                logger.warning(f"验证实时写入的 SRT 文件失败: {e}，从结果中重新写入")
                output_path = self._write_srt_from_result(result, output_path)
            
            # 构建结果摘要
            segments_info = []
            for i, seg in enumerate(result['segments'], 1):
                start = seg['start']
                end = seg['end']
                start_min = int(start // 60)
                start_sec = int(start % 60)
                end_min = int(end // 60)
                end_sec = int(end % 60)
                segments_info.append(
                    f"[{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}] {seg['text']}"
                )
            
            summary = (
                f"转录成功！\n"
                f"音频文件: {audio_path.name}\n"
                f"模型: {model_name}\n"
                f"语言: {result.get('language', 'auto')}\n"
                f"总文本长度: {len(result['text'])} 字符\n"
                f"段落数: {len(result['segments'])}\n"
                f"输出文件: {output_path}\n"
                f"\n段落时间戳（精确到 0.01 秒）：\n" + "\n".join(segments_info[:10])
            )
            
            if len(result['segments']) > 10:
                summary += f"\n... 还有 {len(result['segments']) - 10} 个段落"
            
            return ToolResult(
                success=True,
                data={
                    "text": result['text'],
                    "language": result.get('language', 'unknown'),
                    "segments_count": len(result['segments']),
                    "output_file": str(output_path),
                    "segments": result['segments'][:5],  # 只返回前5个段落作为示例
                    "summary": summary  # 将摘要放在 data 中
                }
            )
            
        except ImportError as e:
            error_msg = f"Whisper 未安装或路径错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # 提供详细的错误信息，明确告诉 LLM 不要创建模拟数据
            detailed_error = (
                f"Whisper 工具不可用: {str(e)}\n\n"
                f"⚠️  重要提示：\n"
                f"1. Whisper 工具当前不可用，无法执行语音转文字任务\n"
                f"2. 请勿创建模拟或虚假的转录数据\n"
                f"3. 如果任务需要语音转文字，请先修复 Whisper 工具：\n"
                f"   - 检查 Whisper 是否正确安装\n"
                f"   - 运行 prepare-deps.sh 安装依赖\n"
                f"   - 或手动安装: pip install openai-whisper\n\n"
                f"错误详情: {str(e)}"
            )
            return ToolResult(
                success=False,
                error=detailed_error
            )
        except Exception as e:
            error_msg = f"转录失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ToolResult(
                success=False,
                error=error_msg
            )

