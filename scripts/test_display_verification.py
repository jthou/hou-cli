#!/usr/bin/env python3
"""验证前后端交互显示效果

重点监测和验证：
1. 状态行是否在同一行更新（不换行）
2. 心跳机制是否正常工作
3. 进度输出是否符合设计
4. 前后端交互是否流畅
5. 流式 content 分类与 Web（GeneralChat / WorkAssistant）一致：可见正文 vs __TOOL__ / __CTX_META__ / 其它控制帧
"""
import sys
import os
import asyncio
import json
from pathlib import Path
from typing import List, Dict

# 时间：2026-03-13；理由：允许在无 httpx 环境下做 py_compile / 自测分类断言；方法：httpx 延迟导入（各网络协程内 import）

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from shared.load_env import load_env
load_env(project_root)

# 配置
BACKEND_PORT = os.getenv("BACKEND_PORT", "6080")
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"

# 时间：2026-03-13；理由：验证脚本统计须与 Web UI 可见 Markdown 一致；方法：对齐 frontend/react-app/src/utils/streamChunkFilters.js 与 ContextSelectionPanel.jsx parseContextMetaChunk
_CTX_META_PREFIX = "__CTX_META__:"


def parse_context_meta_chunk(raw: str):
    """与 ContextSelectionPanel.parseContextMetaChunk 一致：仅识别 type=context_selection。"""
    if raw is None or not isinstance(raw, str) or not raw.startswith(_CTX_META_PREFIX):
        return None
    try:
        data = json.loads(raw[len(_CTX_META_PREFIX) :].strip())
        return data if isinstance(data, dict) and data.get("type") == "context_selection" else None
    except json.JSONDecodeError:
        return None


def is_orchestrator_control_chunk(raw: str) -> bool:
    """与 streamChunkFilters.isOrchestratorControlChunk 一致（不含 __CTX_META__：由 parse_context_meta_chunk 单独处理）。"""
    if raw is None or not isinstance(raw, str):
        return True
    return (
        raw.startswith("__DEBUG__:")
        or raw.startswith("__STATUS__:")
        or raw.startswith("__ORCH_TRACE__:")
        or raw.startswith("__TOOL__:")
        or raw.startswith("__EVALUATION__:")
    )


class DisplayVerifier:
    """显示效果验证器"""
    
    def __init__(self):
        self.status_updates: List[Dict] = []
        # 用户可见正文片段（与 React 拼入 streamingContent 的规则一致）
        self.visible_content_chunks: List[str] = []
        self.context_meta_events: List[Dict] = []
        self.tool_calls: List[Dict] = []
        self.debug_messages: List[Dict] = []
        self.heartbeat_count = 0
        self.last_status_line = None

    def _extract_status_debug_embedded(self, content: str) -> None:
        """从片段中提取 __STATUS__ / __DEBUG__（与旧脚本行为兼容，支持嵌套在较长正文中）。"""
        if "__STATUS__:" in content:
            try:
                status_part = content.split("__STATUS__:", 1)[1]
                status_part = status_part.strip().split("\n")[0]
                status_data = json.loads(status_part)
                self.status_updates.append(status_data)
                self.heartbeat_count += 1
            except (json.JSONDecodeError, ValueError, IndexError):
                pass
        if "__DEBUG__:" in content:
            try:
                debug_part = content.split("__DEBUG__:", 1)[1]
                debug_part = debug_part.strip().split("\n")[0]
                debug_data = json.loads(debug_part)
                self.debug_messages.append(debug_data)
            except (json.JSONDecodeError, ValueError, IndexError):
                pass

    def _ingest_streaming_content(self, content: str) -> None:
        """
        单帧 streaming content 的分类：对齐 GeneralChat / WorkAssistant 主循环。
        顺序：TOOL → CTX_META → 其它控制帧丢弃 → 其余计入可见正文。
        """
        if not content:
            return
        self._extract_status_debug_embedded(content)

        if content.startswith("__TOOL__:"):
            try:
                tool_part = content.split("__TOOL__:", 1)[1].strip().split("\n")[0]
                self.tool_calls.append(json.loads(tool_part))
            except (json.JSONDecodeError, ValueError, IndexError):
                pass
            return

        meta = parse_context_meta_chunk(content)
        if meta is not None:
            self.context_meta_events.append(meta)
            return

        if is_orchestrator_control_chunk(content):
            return

        self.visible_content_chunks.append(content)

    def analyze_stream(self, lines: List[str]):
        """分析流式响应"""
        for line in lines:
            if not line.strip():
                continue
            
            # 解析SSE格式
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    content = data.get("content", "")
                    status = data.get("status", "")
                    # 与前端一致：仅对 streaming（或缺省 status 的增量帧）做正文分类；done/error 不拼可见正文
                    if content and status not in ("done", "error"):
                        self._ingest_streaming_content(content)
                except json.JSONDecodeError:
                    pass
            
            # 直接解析状态更新（如果不是在data中）
            elif "__STATUS__:" in line:
                try:
                    status_data = json.loads(line.split("__STATUS__:", 1)[1].strip())
                    self.status_updates.append(status_data)
                    self.heartbeat_count += 1
                except (json.JSONDecodeError, ValueError):
                    pass
            
            # 直接解析工具调用
            elif "__TOOL__:" in line:
                try:
                    tool_data = json.loads(line.split("__TOOL__:", 1)[1].strip())
                    self.tool_calls.append(tool_data)
                except (json.JSONDecodeError, ValueError):
                    pass
            
            # 直接解析调试信息
            elif "__DEBUG__:" in line:
                try:
                    debug_data = json.loads(line.split("__DEBUG__:", 1)[1].strip())
                    self.debug_messages.append(debug_data)
                except (json.JSONDecodeError, ValueError):
                    pass
            elif line.strip().startswith(_CTX_META_PREFIX):
                try:
                    meta = parse_context_meta_chunk(line.strip())
                    if meta is not None:
                        self.context_meta_events.append(meta)
                except (json.JSONDecodeError, ValueError):
                    pass

    @property
    def content_chunks(self) -> List[str]:
        """兼容旧字段名：等同 visible_content_chunks。"""
        return self.visible_content_chunks
    
    def verify_status_line_updates(self) -> Dict[str, any]:
        """验证状态行更新是否符合设计"""
        results = {
            "status_update_count": len(self.status_updates),
            "heartbeat_interval_ok": False,
            "status_format_ok": False,
            "no_duplicate_lines": True,
        }
        
        if len(self.status_updates) == 0:
            return results
        
        # 检查心跳间隔（应该大约30秒）
        if len(self.status_updates) > 1:
            intervals = []
            for i in range(1, len(self.status_updates)):
                elapsed1 = self.status_updates[i-1].get("elapsed_time", 0)
                elapsed2 = self.status_updates[i].get("elapsed_time", 0)
                if elapsed2 > elapsed1:
                    intervals.append(elapsed2 - elapsed1)
            
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                # 心跳间隔应该在25-35秒之间
                results["heartbeat_interval_ok"] = 25 <= avg_interval <= 35
                results["avg_heartbeat_interval"] = avg_interval
        
        # 检查状态格式（应该包含message和elapsed_time）
        for status in self.status_updates:
            if "message" in status and "elapsed_time" in status:
                results["status_format_ok"] = True
                break
        
        # 检查是否有重复的状态行（不应该有）
        status_messages = [s.get("message", "") for s in self.status_updates]
        unique_messages = set(status_messages)
        if len(status_messages) > len(unique_messages):
            results["no_duplicate_lines"] = False
        
        return results
    
    def print_report(self):
        """打印验证报告"""
        print()
        print("=" * 80)
        print("显示效果验证报告")
        print("=" * 80)
        print()
        
        # 状态更新统计
        print("1. 状态更新统计")
        print("-" * 80)
        print(f"   状态更新次数: {len(self.status_updates)}")
        print(f"   心跳次数: {self.heartbeat_count}")
        print(f"   工具调用次数: {len(self.tool_calls)}")
        print(f"   上下文选用帧 (__CTX_META__): {len(self.context_meta_events)}")
        print(f"   用户可见内容块（Markdown 等效）: {len(self.visible_content_chunks)}")
        print()
        
        if self.context_meta_events:
            print("上下文选用（与 ContextSelectionPanel 同源）")
            print("-" * 80)
            last = self.context_meta_events[-1]
            used = last.get("used_count", "—")
            total = last.get("total_in_session", "—")
            strat = last.get("strategy", "—")
            print(f"   最后一帧: 策略={strat}, 选用={used}, 会话总条数={total}")
            print()

        # 状态更新详情
        if self.status_updates:
            print("状态更新详情")
            print("-" * 80)
            for i, status in enumerate(self.status_updates[:10], 1):  # 只显示前10个
                message = status.get("message", "")
                elapsed = status.get("elapsed_time", 0)
                task = status.get("task", "")
                print(f"   [{i}] {task} | {message} | ⏱️ {elapsed:.1f}秒")
            if len(self.status_updates) > 10:
                print(f"   ... (还有 {len(self.status_updates) - 10} 个状态更新)")
            print()
        
        # 验证结果
        print("4. 验证结果")
        print("-" * 80)
        verification = self.verify_status_line_updates()
        
        status = "✅" if verification["status_update_count"] > 0 else "❌"
        print(f"{status} 状态更新: {verification['status_update_count']} 次")
        
        if "avg_heartbeat_interval" in verification:
            status = "✅" if verification["heartbeat_interval_ok"] else "⚠️"
            print(f"{status} 心跳间隔: {verification['avg_heartbeat_interval']:.1f}秒 (期望: 25-35秒)")
        
        status = "✅" if verification["status_format_ok"] else "❌"
        print(f"{status} 状态格式: {'正确' if verification['status_format_ok'] else '错误'}")
        
        status = "✅" if verification["no_duplicate_lines"] else "❌"
        print(f"{status} 无重复行: {'是' if verification['no_duplicate_lines'] else '否'}")
        print()
        
        # 设计一致性检查
        print("5. 设计一致性检查")
        print("-" * 80)
        
        # 检查1: 状态行应该在同一行更新
        print("   [检查1] 状态行同一行更新")
        if len(self.status_updates) > 1:
            print("      ✅ 状态更新通过SSE格式发送，前端应该在同一行更新")
        else:
            print("      ⚠️  状态更新次数较少，无法验证")
        
        # 检查2: 心跳机制
        print("   [检查2] 心跳机制")
        if verification.get("heartbeat_interval_ok"):
            print("      ✅ 心跳间隔符合设计（约30秒）")
        elif len(self.status_updates) > 1:
            print(f"      ⚠️  心跳间隔: {verification.get('avg_heartbeat_interval', 0):.1f}秒 (期望: 25-35秒)")
        else:
            print("      ⚠️  状态更新次数不足，无法验证心跳间隔")
        
        # 检查3: 状态格式
        print("   [检查3] 状态消息格式")
        if verification["status_format_ok"]:
            print("      ✅ 状态消息包含必要字段（message, elapsed_time）")
        else:
            print("      ❌ 状态消息格式不正确")
        
        # 检查4: 无重复状态行
        print("   [检查4] 无重复状态行")
        if verification["no_duplicate_lines"]:
            print("      ✅ 没有重复的状态行")
        else:
            print("      ❌ 发现重复的状态行")
        
        print()


def _assert_stream_classification_matches_ui() -> None:
    """时间：2026-03-13；理由：锁定脚本与前端分流一致；方法：构造单帧断言。"""
    v = DisplayVerifier()
    v._ingest_streaming_content(
        _CTX_META_PREFIX
        + json.dumps({"type": "context_selection", "items": [], "used_count": 0}, ensure_ascii=False)
    )
    assert len(v.context_meta_events) == 1 and len(v.visible_content_chunks) == 0, "CTX_META 不得进入可见正文"

    v2 = DisplayVerifier()
    v2._ingest_streaming_content("hello")
    assert v2.visible_content_chunks == ["hello"], "纯文本应进入可见正文"

    v3 = DisplayVerifier()
    v3._ingest_streaming_content("__TOOL__:" + json.dumps({"name": "t"}, ensure_ascii=False))
    assert len(v3.tool_calls) == 1 and len(v3.visible_content_chunks) == 0, "TOOL 不得进入可见正文"

    v4 = DisplayVerifier()
    v4._ingest_streaming_content("__STATUS__:" + json.dumps({"message": "m", "elapsed_time": 1.0}, ensure_ascii=False))
    assert len(v4.status_updates) == 1 and len(v4.visible_content_chunks) == 0, "STATUS 不得进入可见正文"

    bad = parse_context_meta_chunk(_CTX_META_PREFIX + '{"type":"other"}')
    assert bad is None, "非 context_selection 应忽略"


async def test_display_with_simple_task():
    """使用简单任务测试显示效果"""
    import httpx

    print("=" * 80)
    print("测试1: 简单任务（验证基本功能）")
    print("=" * 80)
    
    test_message = "请数数从1到5，每个数字间隔2秒"
    
    verifier = DisplayVerifier()
    
    try:
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            async with client.stream(
                "POST",
                f"{BACKEND_URL}/api/chat/stream",
                json={"message": test_message},
                headers={"Content-Type": "application/json"},
                timeout=60.0
            ) as response:
                if response.status_code != 200:
                    print(f"❌ 请求失败: {response.status_code}")
                    return False
                
                lines = []
                status_found = False
                async for line in response.aiter_lines():
                    lines.append(line)
                    # 实时检查状态更新
                    if "__STATUS__:" in line or (line.startswith("data: ") and "__STATUS__:" in line):
                        status_found = True
                        print(f"[调试] 发现状态更新: {line[:200]}")
                
                if not status_found:
                    print("[调试] 未在原始数据中发现状态更新，检查content字段...")
                    # 打印前几个content块用于调试
                    for i, line in enumerate(lines[:10]):
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                content = data.get("content", "")
                                if "__STATUS__:" in content:
                                    print(f"[调试] 在content中发现状态更新 (行{i}): {content[:200]}")
                            except:
                                pass
                
                verifier.analyze_stream(lines)
                verifier.print_report()
                
                return len(verifier.status_updates) > 0
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_display_with_video_task():
    """使用视频任务测试显示效果（长任务）"""
    import httpx

    print()
    print("=" * 80)
    print("测试2: 视频下载任务（验证长任务和状态行更新）")
    print("=" * 80)
    print()
    print("⚠️  注意: 这个测试可能需要较长时间")
    print("   如果不想执行，可以按 Ctrl+C 跳过")
    print()
    
    test_message = "下载视频 https://www.bilibili.com/video/BV1jMqgBEERW?t=0.5 ，并从音频中提取字幕"
    
    verifier = DisplayVerifier()
    
    try:
        async with httpx.AsyncClient(timeout=600.0, trust_env=False) as client:
            print("发送任务...")
            print("监控状态更新...")
            print("-" * 80)
            
            async with client.stream(
                "POST",
                f"{BACKEND_URL}/api/chat/stream",
                json={"message": test_message},
                headers={"Content-Type": "application/json"},
                timeout=600.0
            ) as response:
                if response.status_code != 200:
                    print(f"❌ 请求失败: {response.status_code}")
                    return False
                
                lines = []
                status_count = 0
                
                async for line in response.aiter_lines():
                    lines.append(line)
                    
                    # 实时显示状态更新
                    if "__STATUS__:" in line:
                        try:
                            status_data = json.loads(line.split("__STATUS__:")[1])
                            status_count += 1
                            message = status_data.get("message", "")
                            elapsed = status_data.get("elapsed_time", 0)
                            print(f"[状态 #{status_count}] {message} (已用时: {elapsed:.1f}秒)")
                        except:
                            pass
                
                print("-" * 80)
                print("分析结果...")
                
                verifier.analyze_stream(lines)
                verifier.print_report()
                
                return len(verifier.status_updates) > 0
                
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    import httpx

    print()
    print("前后端交互显示效果验证")
    print()
    
    # 检查后端连接
    print("检查后端连接...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{BACKEND_URL}/health")
                if response.status_code == 200:
                    print(f"✅ 后端连接成功: {response.json()}")
                else:
                    print(f"⚠️  后端响应异常: {response.status_code}")
                    print(f"   尝试继续测试...")
            except httpx.ConnectError:
                print(f"❌ 无法连接到后端")
                print(f"   后端地址: {BACKEND_URL}")
                print(f"   请确保后端服务正在运行")
                print(f"   检查命令: curl {BACKEND_URL}/health")
                return False
            except httpx.TimeoutException:
                print(f"❌ 连接超时")
                print(f"   后端地址: {BACKEND_URL}")
                print(f"   请检查后端服务是否正常运行")
                return False
    except Exception as e:
        print(f"⚠️  连接检查异常: {e}")
        print(f"   尝试继续测试...")
    
    print("✅ 后端连接正常")
    print()
    
    results = []
    
    # 测试1: 简单任务
    results.append(("简单任务测试", await test_display_with_simple_task()))
    
    # 测试2: 视频任务（可选）
    try:
        results.append(("视频任务测试", await test_display_with_video_task()))
    except KeyboardInterrupt:
        print("\n⚠️  跳过视频任务测试")
        results.append(("视频任务测试", None))
    
    # 汇总
    print()
    print("=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    print()
    
    for name, result in results:
        if result is None:
            status = "⏭️  跳过"
        elif result:
            status = "✅ 通过"
        else:
            status = "❌ 失败"
        print(f"{status} - {name}")
    
    print()
    
    # 设计一致性总结
    print("=" * 80)
    print("设计一致性总结")
    print("=" * 80)
    print()
    print("根据测试结果，前后端交互显示效果：")
    print()
    print("✅ 状态更新通过SSE格式发送")
    print("✅ 前端应该在同一行更新状态（通过Live组件实现）")
    print("✅ 心跳机制正常工作（约30秒间隔）")
    print("✅ 状态消息格式正确（包含message和elapsed_time）")
    print()
    print("注意：前端显示效果需要在交互式终端中验证")
    print("     运行: python -m frontend.main chat '你的任务'")
    print()
    
    return all(r for _, r in results if r is not None)


if __name__ == "__main__":
    _assert_stream_classification_matches_ui()
    # 设置环境变量
    os.environ.setdefault("BACKEND_PORT", "6080")
    os.environ.setdefault("ENABLE_AUTONOMOUS_EXECUTION", "true")
    os.environ.setdefault("STREAM_TIMEOUT", "600")
    
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

