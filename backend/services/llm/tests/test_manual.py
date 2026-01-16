"""手动测试脚本 - 用于验证 LLM 连接（不依赖 pytest）"""
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
# 从当前文件位置向上查找项目根目录
current_file = Path(__file__).resolve()
PROJECT_ROOT = current_file.parent.parent.parent.parent
env_path = PROJECT_ROOT / '.env'

if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"✅ 已加载 .env 文件: {env_path}\n")
else:
    # 尝试当前目录
    cwd_env = Path.cwd() / '.env'
    if cwd_env.exists():
        load_dotenv(cwd_env, override=True)
        print(f"✅ 已加载 .env 文件: {cwd_env}\n")
    else:
        print(f"⚠️  未找到 .env 文件（尝试了 {env_path} 和 {cwd_env}）\n")
        load_dotenv()

# 添加项目根目录到路径
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 确保当前工作目录是项目根目录
os.chdir(PROJECT_ROOT)

async def test_llm(provider: str, model: str, api_key_env: str, service_name: str):
    """测试 LLM 连接"""
    api_key = os.getenv(api_key_env)
    if not api_key:
        print(f"⚠️  {service_name}: {api_key_env} 未设置，跳过测试")
        return False
    
    try:
        from backend.services.llm.llm_service import LLMService
        
        print(f"测试 {service_name} ({model})...")
        llm_service = LLMService(provider=provider, model=model)
        
        # 测试非流式
        user_prompt = "hello，你是什么模型？"
        print(f"  非流式测试: {user_prompt}")
        response = await llm_service.chat(user_prompt=user_prompt)
        
        if response and isinstance(response, str) and len(response) > 0:
            print(f"  ✅ 非流式响应成功: {response[:100]}...")
        else:
            print(f"  ❌ 非流式响应失败: {response}")
            return False
        
        # 测试流式
        print(f"  流式测试: {user_prompt}")
        chunks = []
        async for chunk in llm_service.stream_chat(user_prompt=user_prompt):
            chunks.append(chunk)
        
        if len(chunks) > 0:
            full_response = "".join(chunks)
            print(f"  ✅ 流式响应成功 ({len(chunks)} 个块): {full_response[:100]}...")
            return True
        else:
            print(f"  ❌ 流式响应失败: 未收到数据块")
            return False
            
    except ImportError as e:
        print(f"  ❌ 导入错误: {e}")
        print(f"  提示: 请安装依赖: pip install -r requirements-dev.txt")
        return False
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """运行所有测试"""
    print("=" * 60)
    print("LLM 连接测试")
    print("=" * 60)
    print()
    
    tests = [
        # DeepSeek
        ("deepseek", "deepseek-chat", "DEEPSEEK_API_KEY", "DeepSeek"),
        
        # OpenAI 模型（TheTurbo.ai 网关）
        ("theturbogateway", "gpt-5.2", "TURBOGATEWAY_API_KEY", "OpenAI GPT-5.2"),
        ("theturbogateway", "gpt-5.1", "TURBOGATEWAY_API_KEY", "OpenAI GPT-5.1"),
        ("theturbogateway", "gpt-5", "TURBOGATEWAY_API_KEY", "OpenAI GPT-5"),
        ("theturbogateway", "gpt-5.1-codex", "TURBOGATEWAY_API_KEY", "OpenAI GPT-5.1-Codex"),
        ("theturbogateway", "o1-preview", "TURBOGATEWAY_API_KEY", "OpenAI O1 Preview"),
        ("theturbogateway", "o3", "TURBOGATEWAY_API_KEY", "OpenAI O3"),
        ("theturbogateway", "o3-mini-2025-01-31", "TURBOGATEWAY_API_KEY", "OpenAI O3 Mini (2025-01-31)"),
        
        # Anthropic Claude 模型（TheTurbo.ai 网关）
        ("theturbogateway", "claude-opus-4-5-20251101", "TURBOGATEWAY_API_KEY", "Anthropic Claude Opus 4.5"),
        ("theturbogateway", "claude-sonnet-4-5-20250929", "TURBOGATEWAY_API_KEY", "Anthropic Claude Sonnet 4.5"),
        ("theturbogateway", "claude-haiku-4-5-20251001", "TURBOGATEWAY_API_KEY", "Anthropic Claude Haiku 4.5"),
        ("theturbogateway", "claude-3-5-haiku-20241022", "TURBOGATEWAY_API_KEY", "Anthropic Claude 3.5 Haiku"),
        
        # Google Gemini 模型（TheTurbo.ai 网关）
        ("theturbogateway", "gemini-3-pro-preview", "TURBOGATEWAY_API_KEY", "Google Gemini 3 Pro Preview"),
        ("theturbogateway", "gemini-3-pro-image-preview", "TURBOGATEWAY_API_KEY", "Google Gemini 3 Pro Image Preview"),
        ("theturbogateway", "gemini-2.5-flash-image", "TURBOGATEWAY_API_KEY", "Google Gemini 2.5 Flash Image"),
        ("theturbogateway", "gemini-2.5-flash", "TURBOGATEWAY_API_KEY", "Google Gemini 2.5 Flash"),
        ("theturbogateway", "gemini-2.5-pro", "TURBOGATEWAY_API_KEY", "Google Gemini 2.5 Pro"),
        
        # Perplexity Sonar 模型（TheTurbo.ai 网关）
        ("theturbogateway", "sonar", "TURBOGATEWAY_API_KEY", "Perplexity Sonar"),
        ("theturbogateway", "sonar-pro", "TURBOGATEWAY_API_KEY", "Perplexity Sonar Pro"),
        ("theturbogateway", "sonar-reasoning-pro", "TURBOGATEWAY_API_KEY", "Perplexity Sonar Reasoning Pro"),
        
        # 百炼平台 - 文本模型
        ("bailian", "qwen-turbo", "BAILIAN_API_KEY", "百炼平台 Qwen Turbo"),
        ("bailian", "qwen-turbo-latest", "BAILIAN_API_KEY", "百炼平台 Qwen Turbo Latest"),
        ("bailian", "qwen-plus-2025-12-01", "BAILIAN_API_KEY", "百炼平台 Qwen Plus"),
        ("bailian", "qwen3-max", "BAILIAN_API_KEY", "百炼平台 Qwen3 Max"),
        ("bailian", "qwen3-coder-flash", "BAILIAN_API_KEY", "百炼平台 Qwen3 Coder Flash"),
        ("bailian", "qwen3-coder-plus-2025-09-23", "BAILIAN_API_KEY", "百炼平台 Qwen3 Coder Plus"),
        ("bailian", "deepseek-v3.2", "BAILIAN_API_KEY", "百炼平台 DeepSeek V3.2"),
        ("bailian", "qwq-plus", "BAILIAN_API_KEY", "百炼平台 QwQ Plus"),
        ("bailian", "kimi-k2-thinking", "BAILIAN_API_KEY", "百炼平台 Kimi K2 Thinking"),
        
        # 百炼平台 - 视觉模型
        ("bailian", "qwen-vl-max-2025-08-13", "BAILIAN_API_KEY", "百炼平台 Qwen-VL Max (视觉)"),
        ("bailian", "qwen3-vl-plus-2025-12-19", "BAILIAN_API_KEY", "百炼平台 Qwen3-VL Plus (视觉)"),
        ("bailian", "qwen3-vl-flash-2025-10-15", "BAILIAN_API_KEY", "百炼平台 Qwen3-VL Flash (视觉)"),
        ("bailian", "qwen-vl-plus-latest", "BAILIAN_API_KEY", "百炼平台 Qwen-VL Plus Latest (视觉)"),
    ]
    
    results = []
    for provider, model, api_key_env, service_name in tests:
        result = await test_llm(provider, model, api_key_env, service_name)
        results.append((service_name, result))
        print()
    
    # 总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for service_name, result in results:
        status = "✅ 通过" if result else "❌ 失败/跳过"
        print(f"{status}: {service_name}")
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == 0:
        print("\n提示: 如果所有测试都失败，请检查:")
        print("  1. 是否安装了依赖: pip install -r requirements-dev.txt")
        print("  2. .env 文件中的 API Key 是否正确配置")
        print("  3. API Key 是否有效")

if __name__ == "__main__":
    asyncio.run(main())

