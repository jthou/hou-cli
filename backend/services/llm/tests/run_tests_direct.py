#!/usr/bin/env python3
"""直接运行测试 - 不依赖 pytest 插件系统"""
import sys
import os
import asyncio
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from shared.load_env import load_env
load_env(PROJECT_ROOT)

# 添加项目根目录到路径
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 确保当前工作目录是项目根目录
os.chdir(PROJECT_ROOT)

async def run_test(provider: str, model: str, api_key_env: str, service_name: str):
    """运行单个测试"""
    api_key = os.getenv(api_key_env)
    if not api_key:
        print(f"⚠️  {service_name}: {api_key_env} 未设置，跳过测试")
        return ("skip_no_key", api_key_env)  # 返回跳过原因和需要的 API Key
    
    try:
        from backend.services.llm.llm_service import LLMService
        
        print(f"\n{'='*60}")
        print(f"测试 {service_name} ({model})")
        print(f"{'='*60}")
        
        llm_service = LLMService(provider=provider, model=model)
        
        user_prompt = "hello，你是什么模型？"
        non_streaming_ok = False
        streaming_ok = False
        
        # 测试非流式（某些模型可能只支持流式）
        print(f"\n[非流式测试]")
        print(f"问题: {user_prompt}")
        try:
            response = await llm_service.chat(user_prompt=user_prompt)
            
            if response and isinstance(response, str) and len(response) > 0:
                print(f"✅ 非流式响应成功")
                print(f"响应: {response[:200]}...")
                non_streaming_ok = True
            else:
                print(f"❌ 非流式响应失败: {response}")
        except Exception as e:
            error_str = str(e)
            # 检查是否是"只支持流式"的错误
            if ("only support stream" in error_str.lower() or 
                ("stream mode" in error_str.lower() and "only" in error_str.lower()) or
                ("stream parameter" in error_str.lower() and "only" in error_str.lower())):
                print(f"⚠️  该模型只支持流式模式，跳过非流式测试")
                non_streaming_ok = None  # None 表示跳过
            else:
                # 其他错误，重新抛出
                raise
        
        # 测试流式
        print(f"\n[流式测试]")
        print(f"问题: {user_prompt}")
        chunks = []
        async for chunk in llm_service.stream_chat(user_prompt=user_prompt):
            chunks.append(chunk)
        
        if len(chunks) > 0:
            full_response = "".join(chunks)
            print(f"✅ 流式响应成功 ({len(chunks)} 个块)")
            print(f"响应: {full_response[:200]}...")
            streaming_ok = True
        else:
            print(f"❌ 流式响应失败: 未收到数据块")
            return False
        
        # 总结测试结果
        if non_streaming_ok is None:
            # 只支持流式的模型
            print(f"\n✅ {service_name} 测试通过（非流式: ⏭️ 跳过, 流式: ✅）")
        elif non_streaming_ok and streaming_ok:
            print(f"\n✅ {service_name} 测试通过（非流式: ✅, 流式: ✅）")
        else:
            print(f"\n⚠️  {service_name} 部分测试通过（非流式: {'✅' if non_streaming_ok else '❌'}, 流式: ✅）")
        
        return True
            
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        # 检查是否是配置问题（模型未启用、权限不足等）
        error_str = str(e)
        error_type = type(e).__name__
        
        # 检查是否是"只支持流式"的错误（400 BadRequestError）
        if ("400" in error_str or "BadRequestError" in error_type):
            if ("only support stream" in error_str.lower() or 
                ("stream mode" in error_str.lower() and "only" in error_str.lower()) or
                ("stream parameter" in error_str.lower() and "only" in error_str.lower())):
                # 这是"只支持流式"的错误，已经在非流式测试中处理了
                # 如果流式测试也失败，才会到这里
                print(f"⚠️  该模型只支持流式模式，但流式测试也失败")
                print(f"   错误信息: {error_str[:200]}...")
                return False
        
        # 检查是否是配置问题（模型未启用、权限不足等）
        if ("403" in error_str or "PermissionDenied" in error_str or 
            "not enabled" in error_str.lower() or 
            "do not have access" in error_str.lower()):
            print(f"⚠️  配置问题: 模型可能未启用或权限不足")
            print(f"   错误信息: {error_str[:200]}...")
            return ("skip_permission", api_key_env)  # 返回跳过原因和需要的 API Key
        
        # 其他错误视为测试失败
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_default_models():
    """测试默认模型配置（对话、编码、推理、视觉）"""
    print("\n" + "=" * 60)
    print("默认模型配置测试")
    print("=" * 60)
    
    try:
        from backend.services.llm.model_config import get_model_config_manager
        from backend.services.llm.llm_service import LLMService
        
        config_manager = get_model_config_manager()
        llm_service = LLMService()
        
        # 测试默认模型配置
        default_models = {
            "chat": config_manager.get_chat_model(),
            "code": config_manager.get_code_model(),
            "reasoning": config_manager.get_reasoning_model(),
        }
        
        # 视觉模型（从环境变量获取）
        vision_model = os.getenv("BROWSER_TOOL_VISION_MODEL", 
                                  "qwen-vl-max-2025-08-13")
        default_models["vision"] = vision_model
        
        print(f"\n📋 默认模型配置:")
        for model_type, model_name in default_models.items():
            print(f"  {model_type.upper()}: {model_name}")
        
        # 测试每个默认模型
        results = {}
        for model_type, model_name in default_models.items():
            print(f"\n{'='*60}")
            print(f"测试默认 {model_type.upper()} 模型: {model_name}")
            print(f"{'='*60}")
            
            try:
                # 获取模型配置
                if model_type == "vision":
                    config = config_manager.get_model_config(model_name)
                    api_key_env = config.api_key_env
                else:
                    config = config_manager.get_model_config_by_type(model_type)
                    api_key_env = config.api_key_env
                
                api_key = os.getenv(api_key_env)
                if not api_key:
                    print(f"⚠️  {api_key_env} 未设置，跳过测试")
                    results[model_type] = ("skip_no_key", api_key_env)
                    continue
                
                # 设置模型并测试
                llm_service.set_model(model_name, provider=config.provider)
                
                # 测试流式聊天
                user_prompt = (f"你好，请简单介绍一下你自己"
                              f"（作为{model_type}模型）。")
                print(f"\n[流式测试]")
                print(f"问题: {user_prompt}")
                
                chunks = []
                async for chunk in llm_service.stream_chat(
                        user_prompt=user_prompt):
                    chunks.append(chunk)
                
                if len(chunks) > 0:
                    full_response = "".join(chunks)
                    print(f"✅ 流式响应成功 ({len(chunks)} 个块)")
                    print(f"响应: {full_response[:150]}...")
                    results[model_type] = True
                else:
                    print(f"❌ 流式响应失败: 未收到数据块")
                    results[model_type] = False
                    
            except Exception as e:
                error_str = str(e)
                if "403" in error_str or "PermissionDenied" in error_str:
                    print(f"⚠️  配置问题: 模型可能未启用或权限不足")
                    results[model_type] = ("skip_permission", api_key_env)
                else:
                    print(f"❌ 测试失败: {e}")
                    results[model_type] = False
        
        # 测试模型推荐功能
        print(f"\n{'='*60}")
        print("模型推荐功能测试")
        print(f"{'='*60}")
        
        task_types = ["chat", "code", "reasoning", "vision"]
        for task_type in task_types:
            try:
                recommendations = llm_service.recommend_models(task_type)
                if recommendations:
                    print(f"\n📋 {task_type.upper()} 任务推荐模型 "
                          f"({len(recommendations)} 个):")
                    for i, rec in enumerate(recommendations[:5], 1):
                        provider = rec.get('provider', 'unknown')
                        model = rec.get('model', 'unknown')
                        model_name = f"{provider}-{model}"
                        desc = rec.get('description', '无描述')
                        print(f"  {i}. {model_name}: {desc[:50]}...")
                else:
                    print(f"\n⚠️  {task_type.upper()} 任务：无推荐模型")
            except Exception as e:
                print(f"\n❌ {task_type.upper()} 任务推荐失败: {e}")
        
        # 总结默认模型测试结果
        print(f"\n{'='*60}")
        print("默认模型测试总结")
        print(f"{'='*60}")
        for model_type, result in results.items():
            if result is True:
                status = "✅ 通过"
            elif isinstance(result, tuple):
                if result[0] == "skip_no_key":
                    status = f"⚠️  跳过（{result[1]} 未设置）"
                else:
                    status = f"⚠️  跳过（{result[1]} 权限不足）"
            else:
                status = "❌ 失败"
            model_name = default_models[model_type]
            print(f"{status}: {model_type.upper()} 模型 ({model_name})")
        
    except Exception as e:
        print(f"❌ 默认模型测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("LLM 连接测试（直接运行）")
    print("=" * 60)
    
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
        result = await run_test(provider, model, api_key_env, service_name)
        results.append((service_name, result))
    
    # 添加默认模型配置测试
    await test_default_models()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(1 for _, result in results if result is True)
    skipped_no_key = sum(1 for _, result in results 
                         if isinstance(result, tuple) and result[0] == "skip_no_key")
    skipped_permission = sum(1 for _, result in results 
                             if isinstance(result, tuple) and result[0] == "skip_permission")
    skipped = skipped_no_key + skipped_permission
    failed = sum(1 for _, result in results if result is False)
    total = len(results)
    
    # 按状态分组显示
    for service_name, result in results:
        if result is True:
            status = "✅ 通过"
        elif isinstance(result, tuple):
            if result[0] == "skip_no_key":
                status = f"⚠️  跳过（{result[1]} 未设置）"
            elif result[0] == "skip_permission":
                status = f"⚠️  跳过（{result[1]} 权限不足或模型未启用）"
            else:
                status = "⚠️  跳过"
        else:
            status = "❌ 失败"
        print(f"{status}: {service_name}")
    
    print(f"\n总计: {passed} 通过, {skipped} 跳过, {failed} 失败 / {total} 个测试")
    
    # 按 API Key 分组显示跳过的模型
    if skipped > 0:
        print(f"\n{'='*60}")
        print("跳过原因分析")
        print(f"{'='*60}")
        
        # 收集需要不同 API Key 的模型
        api_key_groups = {}
        for service_name, result in results:
            if isinstance(result, tuple) and result[0] == "skip_no_key":
                api_key = result[1]
                if api_key not in api_key_groups:
                    api_key_groups[api_key] = []
                api_key_groups[api_key].append(service_name)
        
        for api_key, services in api_key_groups.items():
            print(f"\n需要设置 {api_key} 的模型 ({len(services)} 个):")
            for service in services:
                print(f"  - {service}")
        
        if skipped_permission > 0:
            print(f"\n⚠️  另外 {skipped_permission} 个测试因权限不足或模型未启用而跳过")
    
    if passed > 0:
        print(f"\n✅ {passed} 个测试通过！")
    if failed > 0:
        print(f"\n❌ {failed} 个测试失败，请检查错误信息（可能是代码问题）")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)

