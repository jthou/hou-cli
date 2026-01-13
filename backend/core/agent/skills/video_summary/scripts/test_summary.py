#!/usr/bin/env python3
"""测试视频摘要技能 - 摘要相关功能"""
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
env_path = Path(__file__).parent.parent.parent.parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从用户配置目录加载
    user_env = Path.home() / '.config' / 'hou-cli' / '.env'
    if user_env.exists():
        load_dotenv(user_env)

# 添加项目根目录到路径
script_path = Path(__file__).resolve()
# 向上查找项目根目录（包含 backend 目录的父目录）
current = script_path.parent
while current.name != 'backend' and len(current.parts) > 1:
    current = current.parent
if current.name == 'backend':
    project_root = current.parent
else:
    # 如果找不到，使用向上7级的方式
    project_root = script_path.parent.parent.parent.parent.parent.parent.parent

# 确保项目根目录在路径中
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 设置工作目录
os.chdir(project_root)

from backend.core.agent.skills.video_summary import VideoSummarySkill
from backend.core.agent.skills.executor import SkillExecutor
from backend.core.agent.tools.registry import ToolRegistry
from backend.services.llm.llm_service import LLMService

# 输出文件路径 - 使用用户目录下的 hou-cli 目录
USER_HOME = Path.home()
OUTPUT_BASE_DIR = USER_HOME / "hou-cli" / "test_outputs"
OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_BASE_DIR / f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# 创建输出文件处理器
output_file_handle = None

def log_output(message: str, to_file: bool = True):
    """同时输出到终端和文件"""
    print(message, end='')
    if to_file and output_file_handle:
        output_file_handle.write(message)
        output_file_handle.flush()

async def test_subtitle_reading():
    """测试字幕读取功能"""
    log_output("=" * 60 + "\n")
    log_output("测试 1: 字幕文件读取和时间戳提取\n")
    log_output("=" * 60 + "\n")
    
    # 初始化
    tool_registry = ToolRegistry()
    llm_service = LLMService()
    executor = SkillExecutor(tool_registry, llm_service)
    
    # 注册必要的工具（如果尚未注册）
    from backend.core.agent.tools.builtin.code_executor_tool import CodeExecutorTool
    try:
        tool_registry.register(CodeExecutorTool())
    except ValueError:
        # 工具已注册，忽略
        pass
    
    # 字幕文件路径
    subtitle_path = Path(__file__).parent.parent / "assets" / "test_subtitles.srt"
    
    if not subtitle_path.exists():
        log_output(f"❌ 字幕文件不存在: {subtitle_path}\n")
        return
    
    log_output(f"📄 字幕文件: {subtitle_path}\n")
    log_output(f"📊 文件大小: {subtitle_path.stat().st_size} 字节\n\n")
    
    # 构建代码字符串（使用原始字符串，避免转义问题）
    code_content = f'''import re
from pathlib import Path

def parse_srt(file_path):
    """解析 SRT 字幕文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # SRT 格式：序号、时间戳、文本
    pattern = r'(\\d+)\\n(\\d{{2}}:\\d{{2}}:\\d{{2}},\\d{{3}} --> \\d{{2}}:\\d{{2}}:\\d{{2}},\\d{{3}})\\n(.*?)(?=\\n\\d+\\n|\\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    segments = []
    full_text = []
    for match in matches:
        index, timestamp, text = match
        text = text.strip()
        segments.append({{
            'index': int(index),
            'timestamp': timestamp,
            'text': text
        }})
        full_text.append(text)
    
    return {{
        'segments': segments,
        'full_text': ' '.join(full_text),
        'segment_count': len(segments),
        'total_length': len(' '.join(full_text))
    }}

def timestamp_to_seconds(ts):
    """将时间戳转换为秒数"""
    h, m, s_ms = ts.split(':')
    s, ms = s_ms.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

subtitle_path = r"{subtitle_path}"
result = parse_srt(subtitle_path)

# 生成时间戳索引（纯文本格式）
timestamp_index_lines = []
timestamp_index_lines.append("=== TIMESTAMP_INDEX ===")

for seg in result['segments']:
    timestamp = seg['timestamp']
    start_time, end_time = timestamp.split(' --> ')
    start_seconds = timestamp_to_seconds(start_time)
    end_seconds = timestamp_to_seconds(end_time)
    duration = end_seconds - start_seconds
    
    text_preview = seg['text'][:50].replace('\\n', ' ').replace('|', ' ')
    timestamp_index_lines.append(
        f"{{seg['index']}}|{{start_time}}|{{end_time}}|{{start_seconds:.3f}}|{{end_seconds:.3f}}|{{duration:.3f}}|{{text_preview}}"
    )

# 输出结果（纯文本格式）
print("=== SUBTITLE_DATA ===")
print(f"SEGMENT_COUNT: {{result['segment_count']}}")
print(f"TOTAL_LENGTH: {{result['total_length']}}")
print("\\n=== SEGMENTS ===")
for seg in result['segments']:
    print(f"{{seg['index']}}|{{seg['timestamp']}}|{{seg['text']}}")

print("\\n" + "\\n".join(timestamp_index_lines))
'''
    
    step_config = {
        'name': 'read_subtitle',
        'type': 'code_executor',
        'code': code_content,
        'outputs': {
            'subtitle_data': '${result.output}'
        }
    }
    
    context = {
        'input': {},
        'config': {},
        'step_results': []
    }
    
    try:
        result = await executor._execute_code_step(step_config, context)
        
        log_output("✅ 字幕读取成功\n\n")
        log_output("📋 执行结果：\n")
        log_output("-" * 60 + "\n")
        log_output(f"结果键: {list(result.keys())}\n")
        
        # 尝试从不同位置获取输出
        subtitle_data = result.get('subtitle_data') or result.get('output') or result.get('stdout')
        
        if subtitle_data:
            # 保存完整数据到文件
            subtitle_output_file = OUTPUT_BASE_DIR / f"subtitle_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(subtitle_output_file, 'w', encoding='utf-8') as f:
                f.write(subtitle_data)
            log_output(f"💾 完整字幕数据已保存到: {subtitle_output_file}\n")
            
            # 显示前 500 字符
            preview = subtitle_data[:500] if len(subtitle_data) > 500 else subtitle_data
            log_output(preview)
            if len(subtitle_data) > 500:
                log_output(f"\n... (共 {len(subtitle_data)} 字符)\n")
            
            # 解析关键信息
            if "SEGMENT_COUNT:" in subtitle_data:
                for line in subtitle_data.split('\n'):
                    if line.startswith("SEGMENT_COUNT:"):
                        count = line.split(":")[1].strip()
                        log_output(f"\n📊 段落数量: {count}\n")
                    elif line.startswith("TOTAL_LENGTH:"):
                        length = line.split(":")[1].strip()
                        log_output(f"📏 总长度: {length} 字符\n")
        else:
            log_output("⚠️  字幕数据未找到，但执行成功\n")
            log_output(f"结果内容: {result}\n")
        log_output("-" * 60 + "\n")
            
    except Exception as e:
        log_output(f"❌ 字幕读取失败: {e}\n")
        import traceback
        traceback.print_exc(file=output_file_handle if output_file_handle else sys.stderr)


async def test_summary_generation():
    """测试摘要生成功能"""
    log_output("\n" + "=" * 60 + "\n")
    log_output("测试 2: 摘要生成（带时间戳）\n")
    log_output("=" * 60 + "\n")
    
    # 初始化
    tool_registry = ToolRegistry()
    llm_service = LLMService()
    executor = SkillExecutor(tool_registry, llm_service)
    
    # 注册必要的工具（如果尚未注册）
    from backend.core.agent.tools.builtin.code_executor_tool import CodeExecutorTool
    try:
        tool_registry.register(CodeExecutorTool())
    except ValueError:
        # 工具已注册，忽略
        pass
    
    # 先读取字幕
    subtitle_path = Path(__file__).parent.parent / "assets" / "test_subtitles.srt"
    
    # 读取字幕数据（简化版，直接读取文件内容）
    with open(subtitle_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 简单解析获取文本
    import re
    pattern = r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n(.*?)(?=\n\d+\n|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    segments = []
    full_text_parts = []
    for i, match in enumerate(matches, 1):
        text = match.strip()
        segments.append({
            'index': i,
            'text': text
        })
        full_text_parts.append(text)
    
    full_text = ' '.join(full_text_parts)
    
    log_output(f"📄 字幕文本长度: {len(full_text)} 字符\n")
    log_output(f"📊 段落数量: {len(segments)}\n\n")
    
    # 格式化字幕段落（带时间戳）
    formatted_segments = []
    timestamp_pattern = r'(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})'
    for line in content.split('\n'):
        match = re.match(timestamp_pattern, line)
        if match:
            timestamp = match.group(1)
            start_time = timestamp.split(' --> ')[0].split(',')[0]
            # 找到对应的文本（下一行）
            idx = content.split('\n').index(line)
            if idx + 1 < len(content.split('\n')):
                text = content.split('\n')[idx + 1].strip()
                formatted_segments.append(f"[{start_time}] {text}")
    
    # 取更多段落作为示例（覆盖整个视频）
    # 为了确保覆盖整个视频，我们取多个时间段的样本
    total_segments = len(formatted_segments)
    # 如果视频很长，采样多个时间点
    if total_segments > 100:
        # 采样策略：开头、1/4、1/2、3/4、结尾
        sample_indices = [
            0,  # 开头
            total_segments // 4,
            total_segments // 2,
            total_segments * 3 // 4,
            total_segments - 1  # 结尾
        ]
        sample_segments = [formatted_segments[i] for i in sample_indices if i < total_segments]
        # 每个采样点前后各取 10 个段落
        expanded_samples = []
        for idx in sample_indices:
            if idx < total_segments:
                start = max(0, idx - 10)
                end = min(total_segments, idx + 10)
                expanded_samples.extend(formatted_segments[start:end])
        sample_segments = expanded_samples[:200]  # 最多 200 个段落
    else:
        sample_segments = formatted_segments
    
    log_output(f"📊 采样段落数: {len(sample_segments)} / {total_segments}\n")
    
    # 执行 LLM 调用生成摘要
    prompt = f"""基于以下视频字幕内容，从多个角度生成一个详细的结构化摘要（约 800-1200 字）。

**重要**：这是一个完整的视频（共 {total_segments} 个字幕段落），请确保分析整个视频的全部内容，不要只关注开头部分。

**核心目标**：从多个角度提取有价值的信息，全面分析视频内容。

## 分析要求：

### 1. 多角度分析（核心要求）
请从以下多个角度深入分析视频内容，每个角度都要提取关键信息和时间戳：

#### 角度一：角色视角分析
- **主讲人/嘉宾视角**：他/她表达了什么观点、经历、感受？动机是什么？
- **主持人视角**：提出了哪些关键问题？引导了哪些讨论方向？
- **观众/听众视角**：哪些内容最有价值？哪些容易产生共鸣？
- **行业观察者视角**：反映了什么行业趋势、现象、问题？

#### 角度二：维度分析
- **技术/专业维度**：涉及哪些技术、方法、专业知识？有何创新或突破？
- **商业/商业模式维度**：商业模式是什么？如何盈利？商业逻辑如何？
- **情感/个人成长维度**：体现了哪些情感变化？个人成长轨迹如何？
- **社会/行业影响维度**：对行业、社会有何影响？反映了什么趋势？
- **方法论/实践维度**：提供了哪些可操作的方法、工具、流程？

#### 角度三：信息层次分析
- **表面信息**：明确说了什么？直接表达的观点和事实
- **深层洞察**：为什么这么说？背后的逻辑、原因、动机
- **潜在含义**：暗示了什么？未明说的内容、弦外之音、隐藏信息

#### 角度四：价值提取
- **可学习的方法**：有哪些可以学习、模仿的方法和技巧？
- **可借鉴的经验**：有哪些成功或失败的经验值得借鉴？
- **可思考的问题**：提出了哪些值得深入思考的问题？
- **可应用的场景**：这些内容可以应用到哪些实际场景？

### 2. 内容分类
将内容按照主题进行分类，每个分类标注时间戳：
- 背景介绍
- 核心观点
- 案例分析
- 经验分享
- 争议话题
- 总结展望

### 3. 分阶段描述
按照时间顺序或逻辑顺序，将内容分为多个阶段，每个阶段标注时间戳：
- 阶段一：[时间戳] 标题
- 阶段二：[时间戳] 标题
- ...

### 4. 总结亮点
从多个角度提取视频中的亮点内容，包括：
- 独特观点（从哪个角度体现？）
- 精彩案例（说明了什么？）
- 深刻洞察（揭示了什么？）
- 实用建议（如何应用？）

### 5. 总结冲突点
识别并总结视频中的：
- 争议话题（不同观点是什么？）
- 不同观点（为什么不同？）
- 矛盾之处（矛盾的本质是什么？）
- 未解决的问题（问题的核心是什么？）

### 6. 时间戳标注
**重要**：在摘要中为每个关键点标注对应的时间戳（格式：[HH:MM:SS]），时间戳应准确对应字幕中的时间位置。

## 字幕内容：

**视频总信息**：
- 总段落数：{total_segments} 段
- 总文本长度：{len(full_text)} 字符
- 请确保分析整个视频的所有内容，包括开头、中间和结尾部分

字幕内容（带时间戳，采样段落，覆盖整个视频）：
{chr(10).join(sample_segments)}

完整文本（用于理解完整内容）：
{full_text}

## 输出格式：

请按照以下结构输出，确保从多个角度分析：

# 视频摘要（多角度分析）

## 一、多角度分析（核心部分）

### 1. 角色视角分析
#### 主讲人/嘉宾视角 [时间戳]
[分析主讲人的观点、经历、动机等]

#### 主持人视角 [时间戳]
[分析主持人提出的关键问题和引导方向]

#### 观众/听众视角 [时间戳]
[分析哪些内容最有价值、容易产生共鸣]

#### 行业观察者视角 [时间戳]
[分析反映的行业趋势、现象、问题]

### 2. 维度分析
#### 技术/专业维度 [时间戳]
[分析涉及的技术、方法、专业知识、创新点]

#### 商业/商业模式维度 [时间戳]
[分析商业模式、盈利方式、商业逻辑]

#### 情感/个人成长维度 [时间戳]
[分析情感变化、个人成长轨迹]

#### 社会/行业影响维度 [时间戳]
[分析对行业、社会的影响和反映的趋势]

#### 方法论/实践维度 [时间戳]
[分析可操作的方法、工具、流程]

### 3. 信息层次分析
#### 表面信息 [时间戳]
[明确表达的观点和事实]

#### 深层洞察 [时间戳]
[背后的逻辑、原因、动机]

#### 潜在含义 [时间戳]
[暗示的内容、弦外之音、隐藏信息]

### 4. 价值提取
#### 可学习的方法 [时间戳]
[可以学习、模仿的方法和技巧]

#### 可借鉴的经验 [时间戳]
[成功或失败的经验，值得借鉴的地方]

#### 可思考的问题 [时间戳]
[提出的值得深入思考的问题]

#### 可应用的场景 [时间戳]
[可以应用到哪些实际场景]

## 二、内容分类
[按主题分类的内容概述，每个分类标注时间戳]

## 三、分阶段描述
### 阶段一：[时间戳] 标题
[该阶段的主要内容，从多个角度分析]

### 阶段二：[时间戳] 标题
[该阶段的主要内容，从多个角度分析]

...

## 四、亮点总结（多角度）
1. [亮点1] [时间戳]
   [详细描述，说明从哪个角度体现，说明了什么，如何应用]

2. [亮点2] [时间戳]
   [详细描述，说明从哪个角度体现，说明了什么，如何应用]

...

## 五、冲突点总结（多角度）
1. [冲突点1] [时间戳]
   [详细描述，包括不同观点、为什么不同、矛盾的本质]

2. [冲突点2] [时间戳]
   [详细描述，包括不同观点、为什么不同、矛盾的本质]

...

## 六、核心观点（多角度综合）
[从多个角度综合总结视频的核心观点和结论，标注关键时间戳]

---

**注意**：
- 每个关键点后必须标注时间戳，例如："视频介绍了 Python 异步编程 [00:05:30]"
- 时间戳格式：[HH:MM:SS] 或 [MM:SS]
- 确保时间戳准确对应字幕中的时间位置
- 内容要详细、有深度，不要过于简单
"""
    
    log_output("🤖 调用 LLM 生成摘要...\n\n")
    
    try:
        response = await llm_service.chat(
            system_prompt="你是一个专业的AI助手，请根据用户的要求完成任务。",
            user_prompt=prompt
        )
        
        # 保存摘要到文件
        summary_output_file = OUTPUT_BASE_DIR / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(summary_output_file, 'w', encoding='utf-8') as f:
            f.write(response)
        log_output(f"💾 摘要已保存到: {summary_output_file}\n")
        
        log_output("✅ 摘要生成成功\n\n")
        log_output("📋 生成的摘要：\n")
        log_output("-" * 60 + "\n")
        log_output(response)
        log_output("\n" + "-" * 60 + "\n")
        
        # 检查是否包含时间戳
        import re
        timestamp_pattern = r'\[\d{1,2}:\d{2}:\d{2}\]'
        timestamps = re.findall(timestamp_pattern, response)
        if timestamps:
            log_output(f"\n✅ 检测到 {len(timestamps)} 个时间戳标注\n")
            for ts in timestamps:
                log_output(f"   - {ts}\n")
        else:
            log_output("\n⚠️  未检测到时间戳标注\n")
            
    except Exception as e:
        log_output(f"❌ 摘要生成失败: {e}\n")
        import traceback
        traceback.print_exc(file=output_file_handle if output_file_handle else sys.stderr)


async def test_timestamp_extraction():
    """测试时间戳提取功能"""
    log_output("\n" + "=" * 60 + "\n")
    log_output("测试 3: 从摘要中提取时间戳映射\n")
    log_output("=" * 60 + "\n")
    
    # 模拟摘要文本（包含时间戳）
    sample_summary = """视频介绍了 Python 异步编程 [00:05:30]，包括 async/await 语法 [00:08:15] 和实际应用 [00:12:00]。
主要内容包括：
1. 异步编程基础概念 [00:05:30]
2. async/await 语法详解 [00:08:15]
3. 实际应用案例 [00:12:00]
"""
    
    log_output("📄 示例摘要：\n")
    log_output("-" * 60 + "\n")
    log_output(sample_summary)
    log_output("-" * 60 + "\n")
    
    # 执行时间戳提取步骤
    tool_registry = ToolRegistry()
    llm_service = LLMService()
    executor = SkillExecutor(tool_registry, llm_service)
    
    from backend.core.agent.tools.builtin.code_executor_tool import CodeExecutorTool
    try:
        tool_registry.register(CodeExecutorTool())
    except ValueError:
        pass
    
    # 创建模拟的时间戳索引
    timestamp_index_text = """=== TIMESTAMP_INDEX ===
1|00:00:00,000|00:00:05,400|0.000|5.400|5.400|这是第一段字幕内容
2|00:00:05,400|00:00:10,800|5.400|10.800|5.400|这是第二段字幕内容
10|00:05:30,000|00:05:35,000|330.000|335.000|5.000|Python 异步编程介绍
11|00:05:35,000|00:05:40,000|335.000|340.000|5.000|async/await 语法
13|00:08:15,000|00:08:20,000|495.000|500.000|5.000|语法详解
18|00:12:00,000|00:12:05,000|720.000|725.000|5.000|实际应用案例
"""
    
    step_config = {
        'name': 'extract_timestamp_mapping',
        'type': 'code_executor',
        'code': f'''
import re

def timestamp_to_seconds(timestamp_str: str) -> float:
    """将时间戳字符串转换为秒数"""
    parts = timestamp_str.split(':')
    if len(parts) == 3:
        h, m, s = map(int, parts)
        return h * 3600 + m * 60 + s
    elif len(parts) == 2:
        m, s = map(int, parts)
        return m * 60 + s
    return 0.0

def parse_timestamp_index(timestamp_index_text: str) -> dict:
    """解析时间戳索引（纯文本格式）"""
    timestamp_index = {{}}
    lines = timestamp_index_text.strip().split('\\n')
    
    for line in lines:
        if not line or line.startswith('==='):
            continue
        # 格式：索引|开始时间|结束时间|开始秒数|结束秒数|时长|文本预览
        parts = line.split('|', 6)
        if len(parts) >= 6:
            try:
                index = int(parts[0])
                start_time = parts[1]
                end_time = parts[2]
                start_seconds = float(parts[3])
                end_seconds = float(parts[4])
                duration = float(parts[5])
                
                timestamp_index[index] = {{
                    'index': index,
                    'start_time': start_time,
                    'end_time': end_time,
                    'start_seconds': start_seconds,
                    'end_seconds': end_seconds,
                    'duration': duration
                }}
            except (ValueError, IndexError):
                continue
    
    return timestamp_index

def extract_timestamps_from_summary(summary_text: str, timestamp_index: dict) -> list:
    """从摘要文本中提取时间戳，并映射到原始字幕段落"""
    # 匹配时间戳格式：[HH:MM:SS] 或 [MM:SS] 或 [HH:MM:SS-HH:MM:SS]
    timestamp_pattern = r'\\[(\\d{{1,2}}):(\\d{{2}}):(\\d{{2}})(?:-(\\d{{1,2}}):(\\d{{2}}):(\\d{{2}}))?\\]'
    matches = list(re.finditer(timestamp_pattern, summary_text))
    
    key_points = []
    for i, match in enumerate(matches):
        # 提取时间戳
        start_h, start_m, start_s = map(int, match.groups()[:3])
        start_seconds = start_h * 3600 + start_m * 60 + start_s
        
        # 计算结束时间
        if match.groups()[3]:
            end_h, end_m, end_s = map(int, match.groups()[3:6])
            end_seconds = end_h * 3600 + end_m * 60 + end_s
        else:
            # 默认持续 30 秒，或到下一个时间戳
            if i + 1 < len(matches):
                next_start_h, next_start_m, next_start_s = map(int, matches[i+1].groups()[:3])
                end_seconds = next_start_h * 3600 + next_start_m * 60 + next_start_s
            else:
                end_seconds = start_seconds + 30
        
        # 查找对应的字幕段落
        matching_segments = []
        for seg in timestamp_index.values():
            # 检查时间段是否重叠
            if not (seg['end_seconds'] < start_seconds or seg['start_seconds'] > end_seconds):
                matching_segments.append(seg['index'])
        
        # 提取关键点文本（时间戳前后的内容）
        start_pos = match.start()
        end_pos = match.end()
        # 向前查找句子开始
        text_start = summary_text.rfind('.', 0, start_pos) + 1
        if text_start == 0:
            text_start = summary_text.rfind('。', 0, start_pos) + 1
        if text_start == 0:
            text_start = max(0, start_pos - 50)
        
        # 向后查找句子结束
        text_end = summary_text.find('.', end_pos)
        if text_end == -1:
            text_end = summary_text.find('。', end_pos)
        if text_end == -1:
            text_end = min(len(summary_text), end_pos + 50)
        
        point_text = summary_text[text_start:text_end].strip().replace('\\n', ' ').replace('|', ' ')
        
        key_points.append({{
            'point': point_text,
            'timestamp': match.group(),
            'start_time': f"{{start_h:02d}}:{{start_m:02d}}:{{start_s:02d}}",
            'end_time': f"{{int(end_seconds//3600):02d}}:{{int((end_seconds%3600)//60):02d}}:{{int(end_seconds%60):02d}}",
            'start_seconds': start_seconds,
            'end_seconds': end_seconds,
            'duration': end_seconds - start_seconds,
            'segment_indices': matching_segments
        }})
    
    return key_points

summary_text = """{sample_summary}"""
timestamp_index_text = """{timestamp_index_text}"""

# 解析时间戳索引
timestamp_index = parse_timestamp_index(timestamp_index_text)

# 提取时间戳
key_points = extract_timestamps_from_summary(summary_text, timestamp_index)

# 输出纯文本格式
print("=== TIMESTAMP_MAPPING ===")
print(f"TOTAL_KEY_POINTS: {{len(key_points)}}")
print("\\n=== KEY_POINTS ===")
for i, point in enumerate(key_points, 1):
    segments_str = ','.join(map(str, point['segment_indices']))
    point_text_clean = point['point'].replace('\\n', ' ').replace('|', ' ')[:100]
    print(f"{{i}}|{{point['timestamp']}}|{{point['start_time']}}|{{point['end_time']}}|"
          f"{{point['start_seconds']:.3f}}|{{point['end_seconds']:.3f}}|{{point['duration']:.3f}}|"
          f"{{segments_str}}|{{point_text_clean}}")
''',
        'outputs': {
            'timestamp_mapping_data': '${result.output}'
        }
    }
    
    context = {
        'input': {},
        'config': {},
        'step_results': []
    }
    
    try:
        result = await executor._execute_code_step(step_config, context)
        
        if 'timestamp_mapping_data' in result:
            mapping_data = result['timestamp_mapping_data']
            
            # 保存时间戳映射到文件
            mapping_output_file = OUTPUT_BASE_DIR / f"timestamp_mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(mapping_output_file, 'w', encoding='utf-8') as f:
                f.write(mapping_data)
            log_output(f"💾 时间戳映射已保存到: {mapping_output_file}\n")
            
            log_output("✅ 时间戳映射提取成功\n\n")
            log_output("📋 时间戳映射数据：\n")
            log_output("-" * 60 + "\n")
            log_output(mapping_data)
            log_output("\n" + "-" * 60 + "\n")
        else:
            log_output("❌ 时间戳映射数据未找到\n")
            
    except Exception as e:
        log_output(f"❌ 时间戳提取失败: {e}\n")
        import traceback
        traceback.print_exc(file=output_file_handle if output_file_handle else sys.stderr)


async def main():
    """主测试函数"""
    global output_file_handle
    
    # 打开输出文件
    output_file_handle = open(OUTPUT_FILE, 'w', encoding='utf-8')
    
    try:
        log_output("\n" + "=" * 60 + "\n")
        log_output("视频摘要技能 - 摘要相关功能测试\n")
        log_output("=" * 60 + "\n")
        log_output(f"📝 测试输出文件: {OUTPUT_FILE}\n")
        log_output(f"📁 输出目录: {OUTPUT_BASE_DIR}\n\n")
        
        # 测试 1: 字幕读取
        await test_subtitle_reading()
        
        # 测试 2: 摘要生成
        await test_summary_generation()
        
        # 测试 3: 时间戳提取
        await test_timestamp_extraction()
        
        log_output("\n" + "=" * 60 + "\n")
        log_output("测试完成\n")
        log_output("=" * 60 + "\n")
        log_output(f"\n✅ 所有测试输出已保存到: {OUTPUT_FILE}\n")
        log_output(f"📁 详细数据文件保存在: {OUTPUT_BASE_DIR}\n")
        
    finally:
        if output_file_handle:
            output_file_handle.close()


if __name__ == "__main__":
    asyncio.run(main())
