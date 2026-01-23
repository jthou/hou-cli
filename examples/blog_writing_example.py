#!/usr/bin/env python3
"""博客写作Agent使用示例"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.agent.agents.writing_blog_agent import BlogWritingAgent
from backend.services.llm.llm_service import LLMService
from backend.core.agent.tools.registry import ToolRegistry


async def main():
    """主函数 - 演示博客写作Agent的使用"""
    
    # 初始化LLM服务
    llm_service = LLMService()
    
    # 初始化工具注册表
    tool_registry = ToolRegistry()
    
    # 创建博客写作Agent
    blog_agent = BlogWritingAgent(llm_service, tool_registry)
    
    # 示例：用户输入的主题和草稿
    user_topic = "Python异步编程详解"
    user_draft = """
    Python异步编程是现代Python开发的重要技能。
    主要涉及async/await关键字、事件循环、协程等概念。
    适用于I/O密集型任务，如网络请求、文件操作等。
    """
    
    # 构造任务描述
    task_description = f"""
    请基于以下主题和草稿，写一篇结构清晰、内容丰富的技术博客文章：
    
    主题：{user_topic}
    
    草稿内容：
    {user_draft}
    
    要求：
    1. 面向有一定Python基础的开发者
    2. 包含实际代码示例
    3. 解释异步编程的核心概念
    4. 提供最佳实践建议
    """
    
    # 执行博客写作任务
    print("🚀 开始执行博客写作任务...")
    print(f"主题: {user_topic}")
    print("-" * 50)
    
    try:
        result = await blog_agent.execute(
            task=task_description,
            context={
                "target_audience": "Python开发者",
                "article_type": "技术教程",
                "desired_length": "medium"
            }
        )
        
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
                desc = section.get('description', '无描述')
                preview = desc[:50]
                line = f"  {i}. {section.get('title', f'第{i}部分')}: {preview}..."
                print(line[:79])
            
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
            print("🌐 MediaWiki格式内容预览:")
            mediawiki_content = result["mediawiki_content"]
            content_preview = (
                mediawiki_content[:500] + "..."
                if len(mediawiki_content) > 500
                else mediawiki_content
            )
            print(content_preview)
            
        else:
            print("❌ 博客写作任务失败")
            
    except Exception as e:
        print(f"❌ 执行过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())