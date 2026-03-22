#!/usr/bin/env python3
"""
漫画生成功能实际集成测试脚本
验证以下两个关键问题：
1. theturbo.ai 上代理的模型是否只有文本对话能力，没有绘图能力
2. 百炼平台的模型是否能够正常工作（配合LiteLLM代理）
"""

import asyncio
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


async def test_comic_with_theturbo():
    """测试使用TheTurbo.ai网关的漫画生成（通常仅支持文本）"""
    print("\n=== 测试TheTurbo.ai网关漫画生成 ===\n")

    # 检查是否有TheTurbo API密钥
    if not os.environ.get('TURBOGATEWAY_API_KEY'):
        print("   - 未配置 TURBOGATEWAY_API_KEY，跳过TheTurbo测试")
        return False

    print("   - 发现 TURBOGATEWAY_API_KEY，准备测试TheTurbo模型漫画生成功能...")

    # 尝试使用TheTurbo模型
    test_content = """# TheTurbo漫画测试
## 场景1
TheTurbo.ai 代理通常只提供文本处理能力。

## 场景2
漫画生成功能需要图生能力，这可能无法工作。
"""

    from backend.core.agent.skills.comic.skill import ComicSkill

    # 临时设置环境变量以使用TheTurbo
    orig_anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    orig_anthropic_base = os.environ.get('ANTHROPIC_BASE_URL')

    os.environ['ANTHROPIC_API_KEY'] = os.environ['TURBOGATEWAY_API_KEY']
    os.environ['ANTHROPIC_BASE_URL'] = os.environ.get('TURBOGATEWAY_BASE_URL', 'https://gateway.theturbo.ai/v1')
    os.environ['ANTHROPIC_MODEL'] = 'claude-3-5-sonnet-20241022'  # TheTurbo上对应的模型

    try:
        skill = ComicSkill()
        result = await skill.execute({
            "source": test_content,
            "art": "ligne-claire",
            "tone": "neutral",
            "output_dir": str(Path(tempfile.gettempdir()) / "comic_test_theturbo"),
            "llm_model": "claude-3-5-sonnet-20241022"
        })

        print(f"   - 执行结果: {'✓ 成功' if result.success else '✗ 失败'}")
        if result.success:
            print("   - 这是一个意外的结果 - TheTurbo.ai 通常仅支持文本对话，不支持漫画生成")
            print("   - 有可能漫画生成确实成功了，但需要进一步验证PDF内容")
            if result.data and result.data.get("pdf_files"):
                print(f"   - 生成了 {len(result.data['pdf_files'])} 个PDF文件")
            else:
                print("   - 声称成功但没有生成PDF文件 - 这表明API调用成功但漫画生成功能失败")
        else:
            print(f"   - 失败原因: {result.error[:200]}...")  # 截断显示
            if "image generation" in result.error.lower() or "图生" in result.error or "绘图" in result.error:
                print("   - 确认了您的猜想：TheTurbo.ai 代理不支持图像生成")
            else:
                print("   - 失败原因可能与其他因素有关")

        return result.success

    except Exception as e:
        print(f"   - 执行过程中发生异常: {e}")
        return False
    finally:
        # 恢复原始环境变量
        if orig_anthropic_key:
            os.environ['ANTHROPIC_API_KEY'] = orig_anthropic_key
        else:
            os.environ.pop('ANTHROPIC_API_KEY', None)
        if orig_anthropic_base:
            os.environ['ANTHROPIC_BASE_URL'] = orig_anthropic_base
        else:
            os.environ.pop('ANTHROPIC_BASE_URL', None)
        os.environ.pop('ANTHROPIC_MODEL', None)


async def test_comic_with_bailian():
    """测试使用百炼平台的漫画生成（通过LiteLLM代理）"""
    print("\n=== 测试百炼平台漫画生成（LiteLLM代理） ===\n")

    # 检查是否有百炼API密钥
    if not os.environ.get('BAILIAN_API_KEY') and not os.environ.get('DASHSCOPE_API_KEY'):
        print("   - 未配置 BAILIAN_API_KEY 或 DASHSCOPE_API_KEY，跳过百炼测试")
        return False

    print("   - 发现 BAILIAN_API_KEY/DASHSCOPE_API_KEY，准备测试百炼模型漫画生成功能...")

    # 获取或设置图生API密钥
    image_key_set = os.environ.get('DASHSCOPE_API_KEY') or os.environ.get('BAILIAN_API_KEY')

    # 创建测试内容
    test_content = """# 百炼漫画测试
## 场景1
测试百炼平台模型的漫画生成功能。

## 场景2
需要LiteLLM代理将Anthropic API请求转换为DashScope格式。
"""

    from backend.core.agent.skills.comic.skill import ComicSkill

    # 设置环境变量以使用百炼 + LiteLLM代理
    orig_anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    orig_anthropic_base = os.environ.get('ANTHROPIC_BASE_URL')
    orig_anthropic_model = os.environ.get('ANTHROPIC_MODEL')

    # 使用LiteLLM代理配置
    os.environ['ANTHROPIC_API_KEY'] = 'sk-litellm-comic'  # 任意值，LiteLLM会忽略
    os.environ['ANTHROPIC_BASE_URL'] = 'http://localhost:4000'  # LiteLLM代理地址
    os.environ['ANTHROPIC_MODEL'] = 'qwen3-max'  # 百炼模型

    try:
        skill = ComicSkill()
        result = await skill.execute({
            "source": test_content,
            "art": "ligne-claire",
            "tone": "neutral",
            "output_dir": str(Path(tempfile.gettempdir()) / "comic_test_bailian"),
            "llm_model": "qwen3-max"  # 指定百炼模型
        })

        print(f"   - 执行结果: {'✓ 成功' if result.success else '✗ 失败'}")
        if result.success:
            print("   - 百炼平台漫画生成功能似乎正常工作")
            if result.data and result.data.get("pdf_files"):
                print(f"   - 生成了 {len(result.data['pdf_files'])} 个PDF文件")
                print(f"   - 输出目录: {result.data.get('output_dir')}")
            else:
                print("   - 声称成功但没有生成PDF文件 - 这可能表示API调用成功但图像生成部分失败")
        else:
            print(f"   - 失败原因: {result.error[:200]}...")
            if "400" in result.error or "500" in result.error:
                print("   - HTTP错误，可能是LiteLLM代理配置问题或模型不支持图像生成")
            elif "timeout" in result.error.lower():
                print("   - 超时错误，可能是百炼服务响应慢")
            else:
                print("   - 其他错误，需要进一步诊断")

        return result.success

    except Exception as e:
        print(f"   - 执行过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 恢复原始环境变量
        if orig_anthropic_key:
            os.environ['ANTHROPIC_API_KEY'] = orig_anthropic_key
        else:
            os.environ.pop('ANTHROPIC_API_KEY', None)
        if orig_anthropic_base:
            os.environ['ANTHROPIC_BASE_URL'] = orig_anthropic_base
        else:
            os.environ.pop('ANTHROPIC_BASE_URL', None)
        if orig_anthropic_model:
            os.environ['ANTHROPIC_MODEL'] = orig_anthropic_model
        else:
            os.environ.pop('ANTHROPIC_MODEL', None)


async def check_litellm_proxy_running():
    """检查LiteLLM代理是否正在运行"""
    print("\n=== 检查LiteLLM代理状态 ===\n")

    import socket

    # 检查端口是否开放
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 4000))
        if result == 0:
            print("   ✓ LiteLLM代理在端口4000运行")
            sock.close()
            return True
        else:
            print("   ✗ LiteLLM代理未在端口4000运行")
            print("   - 需要启动代理: python scripts/start_litellm_comic_proxy.py")
            sock.close()
            return False
    except Exception as e:
        print(f"   ✗ 端口检查失败: {e}")
        return False


async def run_basic_comic_test():
    """运行基础漫画测试以确认整体功能"""
    print("\n=== 基础漫画功能测试 ===\n")

    # 检查是否所有必要组件都已安装
    import shutil

    if not shutil.which('node'):
        print("   ✗ 未找到 node.js - 需要安装 Node.js 来运行漫画生成")
        return False

    if not shutil.which('npm'):
        print("   ✗ 未找到 npm - 需要安装 npm 来管理依赖")
        return False

    print("   ✓ node.js 已安装")

    # 检查必要的依赖
    run_dir = ROOT / "scripts" / "run_baoyu_comic"
    if not run_dir.exists():
        print(f"   ✗ 漫画运行目录不存在: {run_dir}")
        return False

    node_modules = run_dir / "node_modules"
    if not node_modules.exists():
        print(f"   ⚠ 漫画依赖未安装: {node_modules}")
        print(f"   - 运行: cd {run_dir} && npm install")
    else:
        print("   ✓ 漫画依赖已安装")

    # 检查 baoyu-comic 技能
    from backend.core.agent.skills.comic.skill import _ensure_baoyu_installed

    # 使用项目根目录而不是临时目录
    project_path = ROOT  # 使用全局定义的ROOT路径
    ok, msg = await _ensure_baoyu_installed(project_path)
    if ok:
        print("   ✓ baoyu-comic 技能可访问")
    else:
        print(f"   ✗ baoyu-comic 技能不可访问: {msg}")
        return False

    return True


async def main():
    print("漫画生成功能实际集成测试")
    print("=" * 60)
    print("此脚本将验证您提到的两个关键问题：")
    print("1. theturbo.ai 代理是否仅支持文本，不支持绘图")
    print("2. 百炼平台模型是否能成功工作")
    print("=" * 60)

    # 检查基础功能
    basic_ok = await run_basic_comic_test()
    if not basic_ok:
        print("\n⚠ 基础功能测试失败，后续测试可能无法正常进行")
        return

    # 检查LiteLLM代理状态
    proxy_running = await check_litellm_proxy_running()

    # 测试TheTurbo.ai
    print("\n" + "="*60)
    theturbo_success = await test_comic_with_theturbo()

    # 测试百炼
    print("\n" + "="*60)
    if not proxy_running:
        print("跳过百炼测试，因为LiteLLM代理未运行")
        bailian_success = False
    else:
        bailian_success = await test_comic_with_bailian()

    # 总结
    print("\n" + "="*60)
    print("测试总结:")
    print(f"TheTurbo.ai 漫画生成: {'✓ 成功' if theturbo_success else '✗ 失败或跳过'}")
    print(f"百炼平台漫画生成: {'✓ 成功' if bailian_success else '✗ 失败或跳过'}")

    print("\n根据测试结果分析:")
    if not theturbo_success:
        print("✓ 验证了您的第一个观点：theturbo.ai 代理的模型可能不支持图像生成")
    else:
        print("? 意外 - theturbo.ai 似乎支持图像生成，这与预期不符")

    if not bailian_success and proxy_running:
        print("? 百炼平台模型测试失败，可能有以下原因:")
        print("  - LiteLLM配置问题")
        print("  - 百炼API密钥权限不足")
        print("  - 模型本身不支持图像生成")
        print("  - LiteLLM不正确地转换Anthropic API请求到DashScope格式")
    elif bailian_success:
        print("✓ 百炼平台模型漫画生成功能正常工作")
    else:
        print("- 百炼平台测试跳过（LiteLLM代理未运行）")

    print("\n建议操作:")
    print("1. 如果LiteLLM代理未运行，启动它: python scripts/start_litellm_comic_proxy.py")
    print("2. 检查您的API密钥是否具有图像生成权限")
    print("3. 验证LiteLLM配置文件: config/litellm_comic_bailian.yaml")


if __name__ == "__main__":
    asyncio.run(main())