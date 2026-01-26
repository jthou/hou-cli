#!/usr/bin/env python3
"""测试写作博客文章Agent"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.core.agent.agents.writing_blog_agent import BlogWritingAgent
from backend.services.llm.llm_service import LLMService
from backend.core.agent.tools.registry import ToolRegistry


async def test_blog_agent():
    """测试博客写作Agent"""
    
    # 初始化LLM服务
    try:
        llm_service = LLMService()
        print('✅ LLM服务初始化成功')
    except Exception as e:
        print(f'⚠️  LLM服务初始化出现问题: {str(e)}')
        print('   正在创建最小化LLM服务用于测试')
        
        # 创建一个最小化的LLMService实例用于测试
        class MinimalLLMService:
            def __init__(self):
                self.model = 'deepseek-chat'
                self.provider = 'deepseek'
                self.temperature = 0.7
                self.max_tokens = 2000
            
            async def chat(
                self, messages=None, system_prompt=None, user_prompt=None
            ):
                # 对不同的提示返回不同的模拟响应
                if messages and isinstance(messages, list):
                    user_msg = ''
                    for msg in messages:
                        if msg.get('role') == 'user':
                            user_msg = msg.get('content', '')
                            break
                    
                    # 根据消息内容返回相应的模拟响应
                    if '分析' in user_msg or '提取' in user_msg:
                        return '''{
                            "topic": "我为什么对AI智能体如此乐观",
                            "target_audience": "对AI技术感兴趣的普通读者",
                            "article_type": "观点阐述",
                            "draft_points": ["AI智能体的工作效率提升", "复杂任务自动化", "人机协作新模式"],
                            "special_requirements": ["保持积极乐观的基调"]
                        }'''
                    elif '大纲' in user_msg:
                        return '''{
                            "title": "我为什么对AI智能体如此乐观",
                            "introduction": "AI智能体代表了人工智能发展的新阶段，它们不仅能够处理指令，还能主动规划、推理和使用工具...",
                            "sections": [
                                {"title": "AI智能体的核心优势", "description": "探讨AI智能体相比传统AI的主要优势", "content_hint": "可以从自主性、适应性、协作性等方面论述"},
                                {"title": "实际应用场景", "description": "AI智能体在现实世界中的应用", "content_hint": "举出具体案例，如办公助手、研究助理、创意伙伴等"},
                                {"title": "未来发展展望", "description": "AI智能体的发展趋势和潜力", "content_hint": "预测未来发展方向，包括更强大的认知能力、更好的人机协作等"}
                            ],
                            "conclusion": "AI智能体为我们带来了前所未有的机遇，值得我们保持乐观态度...",
                            "call_to_action": "继续关注和探索AI智能体技术的发展和应用"
                        }'''
                    elif '撰写引言' in user_msg or '引言' in user_msg:
                        return "在当今快速发展的AI时代，我们正见证着一种全新的智能形态——AI智能体的崛起。这些不仅能理解指令，更能主动规划、推理和使用工具的智能实体，正在重塑我们对人工智能的认知边界。我对AI智能体持乐观态度，因为它们代表了从被动响应到主动协助的根本转变。随着技术的不断进步，AI智能体不再仅仅是执行预设指令的程序，而是能够自主设定目标、规划步骤、甚至学习新技能的智能系统。这种能力的跃升，正是我对其未来充满信心的根本原因。"
                    elif '撰写结论' in user_msg or '结论' in user_msg:
                        return "总而言之，AI智能体代表了人工智能发展的一个重要里程碑。它们不仅能够高效处理复杂任务，还具备自主学习和适应能力，为各行各业带来了前所未有的机遇。尽管挑战依然存在，但我坚信，随着技术的不断完善和伦理框架的建立，AI智能体将成为推动社会进步的重要力量。让我们以开放的心态迎接这一智能革命，共同塑造一个更加智能、高效的未来。"
                    elif '行动号召' in user_msg or '后续思考' in user_msg:
                        return "如果您也对AI智能体的未来发展感兴趣，不妨持续关注这一领域的最新进展。同时，思考一下：在您的专业领域中，AI智能体将如何改变现有的工作模式？欢迎在评论区分享您的见解和想法。"
                    elif '章节' in user_msg:
                        if '核心优势' in user_msg:
                            return "AI智能体相较于传统AI程序具有显著优势。首先，它们具备自主性，能够在无人工干预的情况下主动采取行动达成目标。其次，它们展现出强大的适应性，能够根据环境变化调整行为策略。此外，AI智能体还能与其他智能体或人类进行有效协作，形成更复杂的智能系统。这些特性使得AI智能体在解决复杂问题时表现出了前所未有的灵活性和效率。"
                        elif '应用场景' in user_msg:
                            return "AI智能体的应用场景日益广泛。在办公环境中，AI助手可以自主安排会议、整理文档、跟踪项目进度；在科研领域，AI研究员可以自主查阅文献、设计实验、分析数据；在创意行业，AI伙伴可以辅助进行设计、写作、音乐创作等。这些应用不仅提高了工作效率，还释放了人类的创造力，使人们能够专注于更高层次的思维活动。"
                        elif '未来展望' in user_msg:
                            return "AI智能体的未来发展前景广阔。随着大模型技术的不断进步，AI智能体的认知能力将进一步增强，能够处理更加复杂的任务。同时，多模态技术的发展将使AI智能体能够理解和处理文本、图像、声音等多种信息形式。在人机协作方面，AI智能体将更好地理解人类意图，实现无缝协同。更重要的是，随着伦理和安全框架的完善，AI智能体将在确保安全的前提下发挥更大作用。"
                        else:
                            return "AI智能体在所讨论领域展现了巨大潜力，其自主学习和适应能力使其成为未来技术发展的重要推动力。"
                    elif '标签' in user_msg or '关键词' in user_msg:
                        return '["AI智能体", "人工智能", "未来科技", "智能助手", "自动化"]'
                    else:
                        return '这是一个模拟的响应，用于测试目的。'
                else:
                    return 'Mock response for testing purposes.'
        
        llm_service = MinimalLLMService()
    
    # 初始化工具注册表
    tool_registry = ToolRegistry()
    
    # 创建博客写作Agent
    blog_agent = BlogWritingAgent(llm_service, tool_registry)
    
    # 用户输入的主题和草稿
    user_topic = "我为什么对AI智能体如此乐观"
    user_draft = """
    AI智能体代表了人工智能发展的新阶段。
    它们不仅能够处理指令，还能主动规划、推理和使用工具。
    我认为AI智能体将在以下方面带来重大变革：
    1. 工作效率的极大提升
    2. 复杂任务的自动化处理
    3. 人机协作的新模式
    4. 个性化服务的普及
    5. 创新能力的增强
    """
    
    # 构造任务描述
    task_description = f"""
    请基于以下主题和草稿，写一篇结构清晰、内容丰富的博客文章：
    
    主题：{user_topic}
    
    草稿内容：
    {user_draft}
    
    要求：
    1. 面向对AI技术感兴趣的普通读者
    2. 包含具体的例子和应用场景
    3. 解释AI智能体的核心概念
    4. 提供对未来的展望
    5. 保持积极乐观的基调
    """
    
    # 执行博客写作任务
    print("🚀 开始执行博客写作任务...")
    print(f"主题: {user_topic}")
    print("-" * 60)
    
    try:
        # 构造符合基类接口的任务字典
        task_dict = {
            "task": task_description,
            "context": {
                "target_audience": "对AI技术感兴趣的普通读者",
                "article_type": "观点阐述",
                "desired_length": "medium"
            }
        }
        
        result = await blog_agent.execute(task_dict)
        
        if result["success"]:
            print("✅ 博客写作任务完成！")
            print()
            
            # 显示生成的大纲
            print("📋 生成的文章大纲:")
            outline = result["outline"]
            print(f"  标题: {outline.get('title', '无标题')}")
            print(f"  引言: {outline.get('introduction', '无引言')[:50]}...")
            
            sections = outline.get("sections", [])
            for i, section in enumerate(sections, 1):
                desc_preview = section.get('description', '无描述')
                preview = desc_preview[:50]
                content_line = f"  {i}. {section.get('title', f'第{i}部分')}: {preview}..."
                if len(content_line) > 79:
                    print(content_line[:79])
                else:
                    print(content_line)
            
            print(f"  结论: {outline.get('conclusion', '无结论')[:50]}...")
            print()
            
            # 显示完整文章
            article = result["article"]
            print("📝 生成的博客文章:")
            print("=" * 60)
            print(f"## {article['title']}")
            print()
            print(article["introduction"])
            print()
            
            for section in article["sections"]:
                print(f"### {section['title']}")
                print(section["content"])
                print()
            
            print("### 结论")
            print(article["conclusion"])
            print()
            print("### 后续思考")
            print(article["call_to_action"])
            print()
            
            # 显示文章统计信息
            metadata = article["metadata"]
            print("📊 文章统计信息:")
            print(f"  字数: {metadata.get('word_count', 0)}")
            print(f"  预计阅读时间: {metadata.get('reading_time_minutes', 0)} 分钟")
            print(f"  生成章节: {metadata.get('generated_sections', 0)}")
            print(f"  标签: {', '.join(metadata.get('tags', []))}")
            print()
            
            # 显示MediaWiki格式的内容
            print("🌐 MediaWiki格式内容:")
            mediawiki_content = result["mediawiki_content"]
            print(mediawiki_content)
            
        else:
            print("❌ 博客写作任务失败")
            
    except Exception as e:
        print(f"❌ 执行过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_blog_agent())