#!/usr/bin/env python3
"""集成测试 - 测试规划功能与 Orchestrator 的集成"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ["ENABLE_PLANNING"] = "true"
os.environ["PLANNING_WORK_DIR"] = "/tmp/test_planning_integration"
os.environ["PLANNING_COMPLEXITY_THRESHOLD"] = "0.2"  # 降低阈值以便测试


def test_orchestrator_integration():
    """测试 Orchestrator 集成"""
    print("=" * 60)
    print("测试 Orchestrator 集成")
    print("=" * 60)
    
    try:
        from backend.core.agent.orchestrator import Orchestrator
        
        # 创建 Orchestrator 实例
        print("\n1. 初始化 Orchestrator...")
        orchestrator = Orchestrator()
        
        # 检查规划功能是否启用
        assert orchestrator.enable_planning is True, "规划功能应该启用"
        assert orchestrator.planning_manager is not None, "应该有 PlanningManager"
        assert orchestrator.complexity_analyzer is not None, "应该有 TaskComplexityAnalyzer"
        print("   ✓ Orchestrator 初始化成功，规划功能已启用")
        
        # 检查工作目录
        work_dir = orchestrator.planning_manager.work_dir
        print(f"   ✓ 规划文件工作目录: {work_dir}")
        
        # 测试复杂任务检测
        print("\n2. 测试复杂任务检测...")
        complex_task = "实现一个完整的用户管理系统，包括用户注册、登录、权限管理、数据统计等功能"
        is_complex = orchestrator.complexity_analyzer.is_complex_task(complex_task)
        print(f"   ✓ 任务复杂度判断: {is_complex}")
        
        if is_complex:
            # 测试创建规划文件
            print("\n3. 测试创建规划文件...")
            session_id = "test_integration_session"
            files = orchestrator.planning_manager.create_planning_files(
                complex_task, 
                session_id=session_id
            )
            assert files.task_plan.exists(), "task_plan.md 应该存在"
            assert files.findings.exists(), "findings.md 应该存在"
            assert files.progress.exists(), "progress.md 应该存在"
            print(f"   ✓ 规划文件创建成功")
            
            # 测试读取规划文件
            print("\n4. 测试读取规划文件...")
            content = orchestrator.planning_manager.read_task_plan(session_id=session_id)
            assert content is not None, "应该能读取到内容"
            assert complex_task[:20] in content or "用户管理系统" in content, "应该包含任务描述"
            print(f"   ✓ 规划文件读取成功，长度: {len(content)} 字符")
            
            # 测试更新操作
            print("\n5. 测试更新操作...")
            orchestrator.planning_manager.add_progress(
                "测试集成操作",
                files_modified=["test.py"],
                session_id=session_id
            )
            orchestrator.planning_manager.flush_updates()
            print(f"   ✓ 更新操作成功")
            
            # 测试统计信息
            print("\n6. 测试统计信息...")
            stats = orchestrator.planning_manager.get_stats()
            print(f"   ✓ 统计信息获取成功:")
            print(f"     - 文件数量: {stats['files_count']}")
            print(f"     - 缓存大小: {stats['cache_size']}")
            if stats.get('performance'):
                perf = stats['performance']
                print(f"     - 读取次数: {perf.get('read_count', 0)}")
                print(f"     - 写入次数: {perf.get('write_count', 0)}")
        
        print("\n" + "=" * 60)
        print("✓ Orchestrator 集成测试通过！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ 集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试文件
        import shutil
        test_dir = Path("/tmp/test_planning_integration")
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print(f"\n清理测试目录: {test_dir}")


def test_batch_update():
    """测试批量更新机制"""
    print("\n" + "=" * 60)
    print("测试批量更新机制")
    print("=" * 60)
    
    try:
        from backend.core.agent.planning.manager import PlanningManager
        import time
        
        test_dir = Path("/tmp/test_batch_update")
        test_dir.mkdir(exist_ok=True)
        
        manager = PlanningManager(work_dir=test_dir)
        session_id = "test_batch"
        
        # 创建规划文件
        manager.create_planning_files("测试批量更新", session_id=session_id)
        
        # 添加多个更新（应该触发批量更新）
        print("\n1. 添加多个更新操作...")
        for i in range(7):  # 超过批量大小 5
            manager.add_progress(f"操作 {i+1}", session_id=session_id)
            manager.add_finding(f"发现 {i+1}", session_id=session_id)
        
        print(f"   ✓ 添加了 14 个更新操作（7个进度 + 7个发现）")
        print(f"   ✓ 待更新队列长度: {len(manager._pending_updates)}")
        
        # 手动刷新
        print("\n2. 刷新批量更新...")
        manager.flush_updates()
        print(f"   ✓ 批量更新完成，待更新队列长度: {len(manager._pending_updates)}")
        
        # 验证更新
        print("\n3. 验证更新结果...")
        manager._invalidate_cache(manager.get_planning_files(session_id).progress)
        progress_content = manager.get_planning_files(session_id).progress.read_text(encoding='utf-8')
        assert "操作 1" in progress_content, "应该包含第一个操作"
        assert "操作 7" in progress_content, "应该包含最后一个操作"
        print(f"   ✓ 所有更新都已写入文件")
        
        print("\n" + "=" * 60)
        print("✓ 批量更新机制测试通过！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ 批量更新测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        import shutil
        test_dir = Path("/tmp/test_batch_update")
        if test_dir.exists():
            shutil.rmtree(test_dir)


def test_cache_mechanism():
    """测试缓存机制"""
    print("\n" + "=" * 60)
    print("测试缓存机制")
    print("=" * 60)
    
    try:
        from backend.core.agent.planning.manager import PlanningManager
        import time
        
        test_dir = Path("/tmp/test_cache")
        test_dir.mkdir(exist_ok=True)
        
        manager = PlanningManager(work_dir=test_dir)
        session_id = "test_cache"
        
        # 创建规划文件
        manager.create_planning_files("测试缓存", session_id=session_id)
        
        # 第一次读取（应该从文件读取）
        print("\n1. 第一次读取（应该从文件读取）...")
        start_time = time.time()
        content1 = manager.read_task_plan(session_id=session_id)
        time1 = time.time() - start_time
        print(f"   ✓ 读取时间: {time1*1000:.2f}ms")
        
        # 第二次读取（应该从缓存读取）
        print("\n2. 第二次读取（应该从缓存读取）...")
        start_time = time.time()
        content2 = manager.read_task_plan(session_id=session_id)
        time2 = time.time() - start_time
        print(f"   ✓ 读取时间: {time2*1000:.2f}ms")
        
        assert content1 == content2, "内容应该相同"
        assert time2 < time1, "缓存读取应该更快"
        print(f"   ✓ 缓存命中，速度提升: {(time1-time2)/time1*100:.1f}%")
        
        # 检查缓存统计
        stats = manager.get_stats()
        if stats.get('performance'):
            perf = stats['performance']
            print(f"\n3. 缓存统计:")
            print(f"   - 缓存命中: {perf.get('cache_hits', 0)}")
            print(f"   - 缓存未命中: {perf.get('cache_misses', 0)}")
            print(f"   - 缓存命中率: {perf.get('cache_hit_rate', 0)}%")
        
        print("\n" + "=" * 60)
        print("✓ 缓存机制测试通过！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ 缓存测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        import shutil
        test_dir = Path("/tmp/test_cache")
        if test_dir.exists():
            shutil.rmtree(test_dir)


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("规划功能集成测试")
    print("=" * 60)
    
    results = []
    
    # 测试 Orchestrator 集成
    results.append(("Orchestrator集成", test_orchestrator_integration()))
    
    # 测试批量更新
    results.append(("批量更新机制", test_batch_update()))
    
    # 测试缓存机制
    results.append(("缓存机制", test_cache_mechanism()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    
    for name, result in results:
        if result is True:
            print(f"✓ {name}: 通过")
        else:
            print(f"✗ {name}: 失败")
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n🎉 所有集成测试通过！")
        return 0
    else:
        print(f"\n❌ 有 {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

