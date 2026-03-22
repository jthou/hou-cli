#!/usr/bin/env python3
"""
漫画生成功能集成测试脚本
测试两个场景：
1. TheTurbo.ai 代理模型（仅支持文本对话）
2. 百炼平台模型（通过 LiteLLM 代理支持）
"""

import asyncio
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


async def test_environment_setup():
    """测试环境配置"""
    print("=== 漫画生成环境配置测试 ===\n")

    # 导入并测试环境检查函数
    from backend.core.agent.skills.comic.skill import _check_env

    # 测试没有API密钥的情况
    print("1. 测试没有API密钥的环境检查...")
    # 临时清空环境变量
    orig_anthropic = os.environ.get('ANTHROPIC_API_KEY')
    orig_turbo = os.environ.get('TURBOGATEWAY_API_KEY')
    orig_dashscope = os.environ.get('DASHSCOPE_API_KEY')
    orig_bailian = os.environ.get('BAILIAN_API_KEY')

    # 临时清除
    os.environ.pop('ANTHROPIC_API_KEY', None)
    os.environ.pop('TURBOGATEWAY_API_KEY', None)
    os.environ.pop('DASHSCOPE_API_KEY', None)
    os.environ.pop('BAILIAN_API_KEY', None)

    success, msg = _check_env()
    if not success:
        print(f"   ✓ 未配置API密钥时正确返回错误: {msg}")
    else:
        print(f"   ✗ 未预期的成功: {msg}")

    # 恢复原值
    if orig_anthropic:
        os.environ['ANTHROPIC_API_KEY'] = orig_anthropic
    if orig_turbo:
        os.environ['TURBOGATEWAY_API_KEY'] = orig_turbo
    if orig_dashscope:
        os.environ['DASHSCOPE_API_KEY'] = orig_dashscope
    if orig_bailian:
        os.environ['BAILIAN_API_KEY'] = orig_bailian

    # 测试至少有一个API密钥的情况
    print("\n2. 测试有API密钥的环境检查...")
    has_anthropic = bool(orig_anthropic)
    has_turbo = bool(orig_turbo)
    has_dashscope = bool(orig_dashscope)
    has_bailian = bool(orig_bailian)

    if has_anthropic or has_turbo or has_dashscope or has_bailian:
        success, msg = _check_env()
        if success:
            print(f"   ✓ 有API密钥时环境检查通过")
            print(f"   - ANTHROPIC_API_KEY: {'✓' if has_anthropic else '✗'}")
            print(f"   - TURBOGATEWAY_API_KEY: {'✓' if has_turbo else '✗'}")
            print(f"   - DASHSCOPE_API_KEY/BAILIAN_API_KEY: {'✓' if (has_dashscope or has_bailian) else '✗'}")
        else:
            print(f"   ✗ 有API密钥时环境检查失败: {msg}")
    else:
        print("   - 没有发现API密钥，跳过环境检查测试")


async def test_model_detection():
    """测试模型检测逻辑"""
    print("\n=== 模型检测逻辑测试 ===\n")

    from backend.core.agent.skills.comic.skill import _is_bailian_comic_model

    # 测试不同的模型名称
    test_models = [
        ("qwen3-max", "应该是百炼模型"),
        ("qwen-plus-2025-12-01", "应该是百炼模型"),
        ("claude-3-5-sonnet-20241022", "应该不是百炼模型"),
        ("gpt-4o", "应该不是百炼模型"),
        ("non-existent-model", "应该不是百炼模型"),
    ]

    for model_name, expected_desc in test_models:
        is_bailian = _is_bailian_comic_model(model_name)
        print(f"   - {model_name}: {'✓ 百炼模型' if is_bailian else '✗ 非百炼模型'} ({expected_desc})")


async def test_build_comic_env():
    """测试环境变量构建逻辑"""
    print("\n=== 环境变量构建测试 ===\n")

    from backend.core.agent.skills.comic.skill import _build_comic_env

    # 测试普通TheTurbo模型环境
    print("1. 测试TheTurbo模型环境构建...")
    orig_base = os.environ.get('ANTHROPIC_BASE_URL')
    orig_key = os.environ.get('ANTHROPIC_API_KEY')
    orig_model = os.environ.get('ANTHROPIC_MODEL')

    # 清理相关变量
    os.environ.pop('ANTHROPIC_BASE_URL', None)
    os.environ.pop('ANTHROPIC_API_KEY', None)
    os.environ.pop('ANTHROPIC_MODEL', None)
    os.environ['TURBOGATEWAY_API_KEY'] = 'test-key'
    os.environ['TURBOGATEWAY_BASE_URL'] = 'https://test-gateway.com'

    env = _build_comic_env(model='claude-3-5-sonnet-20241022')
    print(f"   - ANTHROPIC_API_KEY: {env.get('ANTHROPIC_API_KEY', '未设置')}")
    print(f"   - ANTHROPIC_BASE_URL: {env.get('ANTHROPIC_BASE_URL', '未设置')}")
    print(f"   - ANTHROPIC_MODEL: {env.get('ANTHROPIC_MODEL', '未设置')}")

    # 恢复
    if orig_base:
        os.environ['ANTHROPIC_BASE_URL'] = orig_base
    if orig_key:
        os.environ['ANTHROPIC_API_KEY'] = orig_key
    if orig_model:
        os.environ['ANTHROPIC_MODEL'] = orig_model
    os.environ.pop('TURBOGATEWAY_API_KEY', None)
    os.environ.pop('TURBOGATEWAY_BASE_URL', None)

    print("\n2. 测试百炼模型环境构建（LiteLLM代理）...")
    # 清理相关变量
    os.environ.pop('ANTHROPIC_BASE_URL', None)
    os.environ.pop('ANTHROPIC_API_KEY', None)
    os.environ.pop('ANTHROPIC_MODEL', None)
    os.environ['LITELLM_COMIC_PROXY_URL'] = 'http://localhost:4000'

    env = _build_comic_env(model='qwen3-max')
    print(f"   - ANTHROPIC_API_KEY: {env.get('ANTHROPIC_API_KEY', '未设置')}")
    print(f"   - ANTHROPIC_BASE_URL: {env.get('ANTHROPIC_BASE_URL', '未设置')}")
    print(f"   - ANTHROPIC_MODEL: {env.get('ANTHROPIC_MODEL', '未设置')}")
    print(f"   - 代理URL: {env.get('ANTHROPIC_BASE_URL', '未设置')}")

    # 恢复
    os.environ.pop('LITELLM_COMIC_PROXY_URL', None)
    if orig_base:
        os.environ['ANTHROPIC_BASE_URL'] = orig_base
    if orig_key:
        os.environ['ANTHROPIC_API_KEY'] = orig_key
    if orig_model:
        os.environ['ANTHROPIC_MODEL'] = orig_model


async def test_mock_comic_execution():
    """测试漫画技能执行流程（mock执行）"""
    print("\n=== 漫画技能执行流程测试（mock） ===\n")

    from backend.core.agent.skills.comic.skill import ComicSkill
    from unittest.mock import patch, AsyncMock

    # 创建测试内容
    test_content = """# 测试漫画
## 第一格
这是一个测试内容。

## 第二格
用于验证漫画生成功能。
"""

    # Mock掉需要真实网络连接和长时间执行的部分
    with patch('backend.core.agent.skills.comic.skill._check_env', return_value=(True, "")), \
         patch('backend.core.agent.skills.comic.skill._ensure_baoyu_installed', new_callable=AsyncMock, return_value=(True, "")), \
         patch('backend.core.agent.skills.comic.skill._run_comic_agent', new_callable=AsyncMock, return_value=(True, "Test log output", "")):

        skill = ComicSkill()
        result = await skill.execute({
            "source": test_content,
            "art": "ligne-claire",
            "tone": "neutral",
            "output_dir": str(Path(tempfile.gettempdir()) / "comic_test")
        })

        print(f"   - 执行结果: {'✓ 成功' if result.success else '✗ 失败'}")
        if not result.success:
            print(f"   - 错误信息: {result.error}")
        else:
            print(f"   - 数据包含: {list(result.data.keys()) if result.data else 'None'}")


async def test_litellm_proxy_status():
    """测试LiteLLM代理状态"""
    print("\n=== LiteLLM代理状态测试 ===\n")

    import subprocess
    import psutil
    import requests

    # 检查是否有运行在4000端口的服务
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 4000))
        if result == 0:
            print("   ✓ 端口4000处于监听状态")
            sock.close()
        else:
            print("   - 端口4000未监听（这可能是正常的，如果没有启动代理）")
            sock.close()
    except Exception as e:
        print(f"   - 端口检查失败: {e}")

    # 检查环境变量
    has_dashscope = bool(os.environ.get('DASHSCOPE_API_KEY'))
    has_bailian = bool(os.environ.get('BAILIAN_API_KEY'))
    print(f"   - DASHSCOPE_API_KEY: {'✓' if has_dashscope else '✗'}")
    print(f"   - BAILIAN_API_KEY: {'✓' if has_bailian else '✗'}")

    # 检查配置文件
    proxy_cfg = ROOT / "config" / "litellm_comic_bailian.yaml"
    if proxy_cfg.exists():
        print(f"   - 代理配置文件: ✓ ({proxy_cfg})")
    else:
        print(f"   - 代理配置文件: ✗ (未找到 {proxy_cfg})")


async def main():
    print("漫画生成功能集成测试\n")
    print("此脚本将测试以下方面:")
    print("1. 环境配置（API密钥等）")
    print("2. 模型检测逻辑（TheTurbo vs 百炼）")
    print("3. 环境变量构建（为不同模型服务构建正确的请求参数）")
    print("4. 漫画技能执行流程（mock真实执行）")
    print("5. LiteLLM代理状态（支持百炼模型的代理服务）")
    print("-" * 60)

    await test_environment_setup()
    await test_model_detection()
    await test_build_comic_env()
    await test_mock_comic_execution()
    await test_litellm_proxy_status()

    print("\n=== 总结 ===")
    print("以上测试验证了漫画生成功能的技术架构，包括:")
    print("- TheTurbo.ai 代理支持（仅文本）")
    print("- 百炼平台模型支持（通过LiteLLM代理转换为Anthropic API格式）")
    print("- 模型检测与环境变量配置逻辑")
    print("\n下一步可以进行实际的集成测试:")
    print("1. 使用简单文本进行漫画生成测试")
    print("2. 测试TheTurbo模型（如果配置了）")
    print("3. 测试百炼模型配合LiteLLM代理（如果配置了）")


if __name__ == "__main__":
    asyncio.run(main())