#!/usr/bin/env python3
"""使用 video_summary skill 摘要 Tim 小时候成长的故事"""
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import re

# 加载环境变量
env_path = Path(__file__).parent.parent.parent.parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    user_env = Path.home() / '.config' / 'hou-cli' / '.env'
    if user_env.exists():
        load_dotenv(user_env)

# 添加项目根目录到路径
script_path = Path(__file__).resolve()
current = script_path.parent
while current.name != 'backend' and len(current.parts) > 1:
    current = current.parent
if current.name == 'backend':
    project_root = current.parent
else:
    project_root = script_path.parent.parent.parent.parent.parent.parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.chdir(project_root)

from backend.core.agent.skills.executor import SkillExecutor
from backend.core.agent.tools.registry import ToolRegistry
from backend.services.llm.llm_service import LLMService

# 输出文件路径
USER_HOME = Path.home()
OUTPUT_BASE_DIR = USER_HOME / "hou-cli" / "test_outputs"
OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
OUTPUT_FILE = OUTPUT_BASE_DIR / f"tim_childhood_summary_{timestamp}.txt"

def log_output(message: str):
    """输出消息"""
    print(message, end='')

async def summarize_tim_childhood():
    """使用 video_summary skill 摘要 Tim 小时候成长的故事"""
    
    log_output("=" * 80 + "\n")
    log_output("使用 Video Summary Skill 摘要 Tim 小时候成长的故事\n")
    log_output("=" * 80 + "\n\n")
    
    # 初始化
    tool_registry = ToolRegistry()
    llm_service = LLMService()
    executor = SkillExecutor(tool_registry, llm_service)
    
    # 注册必要的工具
    from backend.core.agent.tools.builtin.code_executor_tool import CodeExecutorTool
    try:
        tool_registry.register(CodeExecutorTool())
    except ValueError:
        pass
    
    # 字幕文件路径
    subtitle_path = Path(__file__).parent.parent / "assets" / "test_subtitles.srt"
    
    if not subtitle_path.exists():
        log_output(f"❌ 字幕文件不存在: {subtitle_path}\n")
        return
    
    log_output(f"📄 字幕文件: {subtitle_path}\n")
    log_output(f"📊 文件大小: {subtitle_path.stat().st_size} 字节\n\n")
    
    # 步骤 1: 读取字幕文件
    log_output("📖 步骤 1: 读取字幕文件...\n")
    
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
    formatted_segments = []
    
    for match in matches:
        index, timestamp, text = match
        text = text.strip()
        segments.append({{
            'index': int(index),
            'timestamp': timestamp,
            'text': text
        }})
        full_text.append(text)
        
        # 格式化：提取开始时间
        start_time = timestamp.split(' --> ')[0].split(',')[0]
        formatted_segments.append(f"[{{start_time}}] {{text}}")
    
    # 生成时间戳索引（纯文本格式）
    timestamp_index_lines = []
    timestamp_index_lines.append("=== TIMESTAMP_INDEX ===")
    for seg in segments:
        timestamp_index_lines.append(f"{{seg['index']}}|{{seg['timestamp']}}|{{seg['text']}}")
    
    return {{
        'segments': segments,
        'full_text': ' '.join(full_text),
        'segment_count': len(segments),
        'total_length': len(' '.join(full_text)),
        'formatted_segments': '\\n'.join(formatted_segments),
        'timestamp_index': '\\n'.join(timestamp_index_lines)
    }}

subtitle_path = r"{subtitle_path}"
result = parse_srt(subtitle_path)

# 输出格式（纯文本，容错率高）
output_lines = []
output_lines.append("=== SUBTITLE_DATA ===")
output_lines.append(f"SEGMENT_COUNT: {{result['segment_count']}}")
output_lines.append(f"TOTAL_LENGTH: {{result['total_length']}}")
output_lines.append("")
output_lines.append("=== SEGMENTS ===")
for seg in result['segments']:
    output_lines.append(f"{{seg['index']}}|{{seg['timestamp']}}|{{seg['text']}}")
output_lines.append("")
output_lines.append("=== FORMATTED_SEGMENTS ===")
output_lines.append(result['formatted_segments'])
output_lines.append("")
output_lines.append("=== TIMESTAMP_INDEX ===")
output_lines.append(result['timestamp_index'])

print('\\n'.join(output_lines))
'''
    
    step_config = {
        'code': code_content,
        'language': 'python'
    }
    
    tool_result = None
    try:
        code_executor = tool_registry.get_tool('execute_code')
        # code_executor.execute 是同步方法，不需要 await
        tool_result = code_executor.execute(**step_config)
        
        if not tool_result.success:
            log_output(f"❌ 字幕读取失败: {tool_result.error}\n")
            return
        
        # 解析输出
        output = tool_result.data.get('output', '') or tool_result.data.get('stdout', '')
        
        # 提取数据
        subtitle_data = {}
        if 'SEGMENT_COUNT:' in output:
            segment_count_match = re.search(r'SEGMENT_COUNT:\s*(\d+)', output)
            total_length_match = re.search(r'TOTAL_LENGTH:\s*(\d+)', output)
            if segment_count_match:
                subtitle_data['segment_count'] = int(segment_count_match.group(1))
            if total_length_match:
                subtitle_data['total_length'] = int(total_length_match.group(1))
        
        # 提取格式化段落
        if '=== FORMATTED_SEGMENTS ===' in output:
            formatted_start = output.find('=== FORMATTED_SEGMENTS ===') + len('=== FORMATTED_SEGMENTS ===')
            formatted_end = output.find('=== TIMESTAMP_INDEX ===', formatted_start)
            if formatted_end > formatted_start:
                subtitle_data['segments'] = output[formatted_start:formatted_end].strip()
        
        # 提取完整文本
        if '=== SEGMENTS ===' in output:
            segments_start = output.find('=== SEGMENTS ===')
            formatted_start = output.find('=== FORMATTED_SEGMENTS ===')
            if formatted_start > segments_start:
                segments_text = output[segments_start:formatted_start]
                # 提取所有文本内容
                text_parts = []
                for line in segments_text.split('\n'):
                    if '|' in line and not line.startswith('==='):
                        parts = line.split('|', 2)
                        if len(parts) >= 3:
                            text_parts.append(parts[2])
                subtitle_data['full_text'] = ' '.join(text_parts)
        
        log_output(f"✅ 字幕读取成功\n")
        log_output(f"📊 段落数: {subtitle_data.get('segment_count', 0)}\n")
        log_output(f"📏 总长度: {subtitle_data.get('total_length', 0)} 字符\n\n")
        
    except Exception as e:
        log_output(f"❌ 执行出错: {e}\n")
        import traceback
        traceback.print_exc()
        return
    
    # 步骤 2: 生成摘要
    log_output("🤖 步骤 2: 生成摘要（重点关注 Tim 小时候成长的故事）...\n")
    log_output("-" * 80 + "\n\n")
    
    user_query = """摘要出Tim聊他小时候成长的故事，包括：
1. 童年时期的经历和感受（包括被冤枉偷窃模型飞机等事件）
2. 家庭环境和教育背景
3. 求学过程（包括国内学习和英国留学经历）
4. 如何走上影像创作道路的转折点（高中毕业典礼视频制作）
5. 这些经历对他后来创业的影响

请从多个角度分析这些内容，包括：
- 角色视角：Tim本人的感受和动机
- 情感维度：这些经历带来的情感变化
- 成长维度：个人成长轨迹
- 价值提取：可借鉴的经验和可思考的问题"""
    
    prompt = f"""基于以下视频字幕内容，从多个角度生成一个详细的结构化摘要（约 2000 字），重点关注 Tim 聊他小时候成长的故事。

**重要**：这是一个完整的视频（共 {subtitle_data.get('segment_count', 0)} 个字幕段落，总长度 {subtitle_data.get('total_length', 0)} 字符），请确保分析整个视频的全部内容，特别是 Tim 讲述童年和成长经历的部分。

**核心目标**：从多个角度提取有价值的信息，全面分析 Tim 的成长故事。

用户问题/需求：{user_query}

## 分析要求：

### 1. 多角度分析（核心要求）
请从以下多个角度深入分析 Tim 的成长故事，每个角度都要提取关键信息和时间戳：

#### 角度一：角色视角分析
- **Tim 本人视角**：他表达了什么观点、经历、感受？动机是什么？
- **主持人视角**：提出了哪些关键问题？引导了哪些讨论方向？
- **观众/听众视角**：哪些内容最有价值？哪些容易产生共鸣？

#### 角度二：维度分析
- **情感/个人成长维度**：体现了哪些情感变化？个人成长轨迹如何？
- **家庭/教育维度**：家庭环境和教育背景如何影响他的成长？
- **社会/文化维度**：反映了什么社会文化现象？

#### 角度三：信息层次分析
- **表面信息**：明确说了什么？直接表达的经历和事实
- **深层洞察**：为什么这么说？背后的逻辑、原因、动机
- **潜在含义**：暗示了什么？未明说的内容、弦外之音

#### 角度四：价值提取
- **可学习的方法**：有哪些可以学习、借鉴的成长经验？
- **可思考的问题**：提出了哪些值得深入思考的问题？
- **可应用的场景**：这些经历可以应用到哪些实际场景？

### 2. 重点关注内容
- 童年时期的经历（包括被冤枉偷窃模型飞机等事件）
- 家庭环境和教育背景
- 求学过程（国内学习和英国留学）
- 走上影像创作道路的转折点（高中毕业典礼视频制作）
- 这些经历对后来创业的影响

### 3. 时间戳标注
**重要**：在摘要中为每个关键点标注对应的时间戳（格式：[HH:MM:SS]），时间戳应准确对应字幕中的时间位置。

## 字幕内容：

**视频总信息**：
- 总段落数：{subtitle_data.get('segment_count', 0)} 段
- 总文本长度：{subtitle_data.get('total_length', 0)} 字符
- 请确保分析整个视频的所有内容，特别是 Tim 讲述童年和成长经历的部分

字幕内容（带时间戳，完整内容）：
{subtitle_data.get('segments', '')[:50000]}...

完整文本（用于理解完整内容）：
{subtitle_data.get('full_text', '')[:100000]}...

## 输出格式：

请按照以下结构输出，确保从多个角度分析：

# Tim 小时候成长的故事摘要（多角度分析）

## 一、多角度分析（核心部分）

### 1. 角色视角分析
#### Tim 本人视角 [时间戳]
[分析 Tim 的观点、经历、感受、动机等]

#### 主持人视角 [时间戳]
[分析主持人提出的关键问题和引导方向]

#### 观众/听众视角 [时间戳]
[分析哪些内容最有价值、容易产生共鸣]

### 2. 维度分析
#### 情感/个人成长维度 [时间戳]
[分析情感变化、个人成长轨迹]

#### 家庭/教育维度 [时间戳]
[分析家庭环境和教育背景的影响]

#### 社会/文化维度 [时间戳]
[分析反映的社会文化现象]

### 3. 信息层次分析
#### 表面信息 [时间戳]
[明确表达的经历和事实]

#### 深层洞察 [时间戳]
[背后的逻辑、原因、动机]

#### 潜在含义 [时间戳]
[暗示的内容、弦外之音]

### 4. 价值提取
#### 可学习的方法 [时间戳]
[可以学习、借鉴的成长经验]

#### 可思考的问题 [时间戳]
[提出的值得深入思考的问题]

#### 可应用的场景 [时间戳]
[可以应用到哪些实际场景]

## 二、成长故事时间线

### 童年时期 [时间戳]
[童年经历，包括被冤枉偷窃模型飞机等事件]

### 求学阶段 [时间戳]
[国内学习和英国留学经历]

### 转折点 [时间戳]
[高中毕业典礼视频制作，走上影像创作道路]

### 影响与启示 [时间戳]
[这些经历对后来创业的影响]

## 三、亮点总结（多角度）
1. [亮点1] [时间戳]
   [详细描述，说明从哪个角度体现，说明了什么，如何应用]

2. [亮点2] [时间戳]
   [详细描述，说明从哪个角度体现，说明了什么，如何应用]

...

## 四、核心观点（多角度综合）
[从多个角度综合总结 Tim 成长故事的核心观点和启示，标注关键时间戳]

---

**注意**：
- 每个关键点后必须标注时间戳，例如："Tim 讲述被冤枉偷窃模型飞机的经历 [00:05:30]"
- 时间戳格式：[HH:MM:SS] 或 [MM:SS]
- 确保时间戳准确对应字幕中的时间位置
- 内容要详细、有深度，不要过于简单
- 重点关注 Tim 的成长故事，其他内容可以简要提及
"""
    
    try:
        # 使用 LLMService 的正确接口
        response = await llm_service.chat(
            system_prompt="你是一个专业的AI助手，请根据用户的要求完成任务。",
            user_prompt=prompt
        )
        
        summary = response if isinstance(response, str) else (response.text if hasattr(response, 'text') else str(response))
        
        # 保存摘要到文件
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("Tim 小时候成长的故事摘要\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"字幕文件: {subtitle_path}\n")
            f.write(f"用户查询: {user_query}\n")
            f.write("\n" + "=" * 80 + "\n\n")
            f.write(summary)
            f.write("\n\n" + "=" * 80 + "\n")
        
        log_output("✅ 摘要生成成功！\n\n")
        log_output("📋 生成的摘要：\n")
        log_output("-" * 80 + "\n")
        log_output(summary)
        log_output("\n" + "-" * 80 + "\n\n")
        log_output(f"💾 摘要已保存到: {OUTPUT_FILE}\n")
        
        # 统计信息
        word_count = len(summary)
        timestamp_count = len(re.findall(r'\[\d{2}:\d{2}:\d{2}\]', summary))
        log_output(f"📊 摘要统计: {word_count} 字符, 约 {timestamp_count} 个时间戳标注\n")
        
    except Exception as e:
        log_output(f"❌ 摘要生成失败: {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(summarize_tim_childhood())
