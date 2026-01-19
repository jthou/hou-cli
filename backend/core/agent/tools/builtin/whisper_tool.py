"""Whisper 语音转文字工具"""
import logging
import sys
import os
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable
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


def _load_whisper_model(model_name: str = "base"):
    """加载 Whisper 模型"""
    whisper_path = _get_whisper_path()
    if not whisper_path.exists():
        raise ImportError(f"Whisper not found at {whisper_path}")
    
    if str(whisper_path) not in sys.path:
        sys.path.insert(0, str(whisper_path))
    
    import whisper
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
                name="output_format",
                type="string",
                description="输出格式：json（完整信息）、text（纯文本）、srt（字幕文件）",
                required=False,
                default="json",
                enum=["json", "text", "srt"]
            ),
            ToolParameter(
                name="output_file",
                type="string",
                description="输出文件路径（可选，如果不指定则自动生成）",
                required=False
            ),
        ]
        
        super().__init__(
            name="whisper",
            description=(
                "语音转文字工具，使用 OpenAI Whisper 模型进行高精度语音识别。"
                "支持多种音频格式（mp3, wav, m4a, flac 等），"
                "提供精确的段落级别时间戳（精确到 0.01 秒），"
                "支持多语言识别和自动语言检测。"
                "\n\n"
                "**重要功能**："
                "- 可以生成字幕文件（SRT格式），用于视频字幕制作"
                "- 支持从音频文件生成带时间戳的字幕"
                "- 适用于视频字幕提取、语音转字幕、音频转字幕等场景"
                "\n\n"
                "使用场景："
                "- 为视频生成字幕文件（subtitle generation）"
                "- 从音频提取字幕（audio to subtitle）"
                "- 语音转文字并生成字幕（speech to text with subtitles）"
                "\n\n"
                "重要：默认会转录完整的音频文件，除非明确指定了时间范围。"
                "注意：当前版本使用段落级别时间戳（已足够精确），"
                "单词级别时间戳在 macOS ARM 上会导致段错误，因此已禁用。"
            ),
            parameters=parameters
        )
    
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
            output_format = kwargs.get("output_format", "json")
            output_file = kwargs.get("output_file")
            
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
                """定期报告进度"""
                start_time = transcription_start_time
                last_report = start_time
                report_interval = 30  # 每30秒报告一次
                
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
                    
                    time.sleep(5)  # 每5秒检查一次
            
            # 启动进度报告线程
            progress_thread = threading.Thread(target=report_progress, daemon=True)
            progress_thread.start()
            logger.info(f"开始转录: {audio_path}")
            
            try:
                # 执行转录（启用 verbose 以获取更多信息）
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
            
            # 处理输出
            output_path = None
            if output_file:
                output_path = Path(output_file).expanduser()
            else:
                # 自动生成输出文件名
                output_path = audio_path.parent / f"{audio_path.stem}_transcription"
            
            # 保存结果
            if output_format == "json":
                json_file = output_path.with_suffix(".json")
                import json
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                output_path = json_file
            elif output_format == "srt":
                srt_file = output_path.with_suffix(".srt")
                with open(srt_file, 'w', encoding='utf-8') as f:
                    for i, seg in enumerate(result['segments'], 1):
                        start = seg['start']
                        end = seg['end']
                        start_str = f"{int(start//3600):02d}:{int((start%3600)//60):02d}:{int(start%60):02d},{int((start%1)*1000):03d}"
                        end_str = f"{int(end//3600):02d}:{int((end%3600)//60):02d}:{int(end%60):02d},{int((end%1)*1000):03d}"
                        f.write(f"{i}\n")
                        f.write(f"{start_str} --> {end_str}\n")
                        f.write(f"{seg['text']}\n\n")
                output_path = srt_file
            else:  # text
                txt_file = output_path.with_suffix(".txt")
                with open(txt_file, 'w', encoding='utf-8') as f:
                    f.write(result['text'])
                output_path = txt_file
            
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
            logger.error(error_msg)
            return ToolResult(
                success=False,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"转录失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ToolResult(
                success=False,
                error=error_msg
            )

