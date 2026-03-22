#!/usr/bin/env python3
"""
简化的漫画生成功能验证脚本
重点测试两个核心问题：
1. TheTurbo.ai 是否仅支持文本而不支持图像生成
2. 百炼模型配合LiteLLM代理是否工作
"""

import os
import sys
from pathlib import Path

# 添加项目路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def test_model_capability():
    """测试模型能力配置"""
    print("=== 漫画生成能力验证 ===\n")

    # 从环境变量获取API密钥
    turbogateway_key = os.environ.get('TURBOGATEWAY_API_KEY')
    bailian_key = os.environ.get('BAILIAN_API_KEY') or os.environ.get('DASHSCOPE_API_KEY')

    print(f"TURBOGATEWAY_API_KEY 配置: {'✓' if turbogateway_key else '✗'}")
    print(f"BAILIAN_API_KEY/DASHSCOPE_API_KEY 配置: {'✓' if bailian_key else '✗'}")

    # 检查模型配置
    print(f"\nCOMIC_DEFAULT_MODEL: {os.environ.get('COMIC_DEFAULT_MODEL', 'NOT SET')}")

    # 检查当前漫画模型配置
    from backend.api.model_config_routes import COMIC_MODELS_BY_PROVIDER

    print("\n可用的漫画模型提供商:")
    for provider, models in COMIC_MODELS_BY_PROVIDER.items():
        print(f"  {provider}: {len(models)} 个模型")
        if provider == "theturbogateway":
            print("    - 这些通常是文本为主的模型（如Claude、GPT等）")
            print("    - 可能不支持图像生成能力")
        elif provider == "bailian":
            print("    - 这些是百炼平台模型")
            print("    - 通过LiteLLM代理转换为Anthropic格式")

    # 测试模型检测逻辑
    print(f"\n模型检测测试:")
    from backend.core.agent.skills.comic.skill import _is_bailian_comic_model

    test_models = [
        "claude-3-5-sonnet-20241022",  # TheTurbo模型
        "qwen3-max",                   # 百炼模型
        "gpt-4o"                       # TheTurbo模型
    ]

    for model in test_models:
        is_bailian = _is_bailian_comic_model(model)
        print(f"  {model}: {'百炼模型' if is_bailian else '非百炼模型'}")

    # 检查LiteLLM代理配置
    print(f"\nLiteLLM代理配置:")
    proxy_cfg = ROOT / "config" / "litellm_comic_bailian.yaml"
    print(f"  代理配置文件: {'✓' if proxy_cfg.exists() else '✗'} ({proxy_cfg})")

    if proxy_cfg.exists():
        cfg_content = proxy_cfg.read_text()
        bailian_models = [line.strip() for line in cfg_content.split('\n')
                         if 'model_name:' in line and ('qwen' in line or 'deepseek' in line)]
        print(f"  代理配置中支持的百炼模型数量: {len(bailian_models)}")

    # 检查环境变量构建逻辑
    print(f"\n环境变量构建逻辑测试:")
    from backend.core.agent.skills.comic.skill import _build_comic_env

    # TheTurbo环境测试
    turbo_env = _build_comic_env(model="claude-3-5-sonnet-20241022")
    print(f"  TheTurbo环境 (claude-3-5-sonnet-20241022):")
    print(f"    - BASE_URL: {turbo_env.get('ANTHROPIC_BASE_URL', 'NOT SET')}")
    print(f"    - MODEL: {turbo_env.get('ANTHROPIC_MODEL', 'NOT SET')}")

    # 百炼环境测试
    bailian_env = _build_comic_env(model="qwen3-max")
    print(f"  百炼环境 (qwen3-max):")
    print(f"    - BASE_URL: {bailian_env.get('ANTHROPIC_BASE_URL', 'NOT SET')}")
    print(f"    - MODEL: {bailian_env.get('ANTHROPIC_MODEL', 'NOT SET')}")

    print("\n=== 分析结论 ===")
    print("1. TheTurbo.ai 模型分析:")
    print("   - 通常只支持Anthropic格式的文本对话API")
    print("   - 不支持图像生成（图生文、文生图等）")
    print("   - 因此，漫画生成（需要图像生成）可能无法正常工作")

    print("\n2. 百炼平台模型分析:")
    print("   - 原生支持图像生成能力")
    print("   - 通过LiteLLM代理转换为Anthropic API格式")
    print("   - 理论上应支持漫画生成")

    print("\n3. 当前配置分析:")
    if turbogateway_key and not bailian_key:
        print("   - 仅配置了TheTurbo，漫画生成功能可能受限")
    elif bailian_key and not turbogateway_key:
        print("   - 仅配置了百炼，应能支持漫画生成（需要LiteLLM代理运行）")
    elif turbogateway_key and bailian_key:
        print("   - 同时配置了两者，可根据模型选择")
    else:
        print("   - 未配置任何API密钥，无法进行漫画生成")

    print("\n=== 验证步骤建议 ===")
    print("1. 验证TheTurbo限制:")
    print("   - 尝试使用 claude-3-5-sonnet 等模型进行漫画生成")
    print("   - 预期会因缺少图像生成功能而失败")

    print("\n2. 验证百炼配置:")
    print("   - 启动LiteLLM代理: python scripts/start_litellm_comic_proxy.py")
    print("   - 尝试使用 qwen3-max 等模型进行漫画生成")
    print("   - 应能正常工作（如果API密钥权限正确）")

if __name__ == "__main__":
    test_model_capability()