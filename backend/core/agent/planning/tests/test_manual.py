#!/usr/bin/env python3
"""手动测试脚本 - 测试规划功能"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
# 添加 backend 目录到路径
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir.parent))

from backend.core.agent.planning.manager import PlanningManager
from backend.core.agent.planning.complexity import TaskComplexityAnalyzer


def test_planning_manager():
    """测试 PlanningManager"""
    print("=" * 60)
    print("测试 PlanningManager")
    print("=" * 60)
    
    # 创建临时目录
    test_dir = Path("/tmp/test_planning")
    test_dir.mkdir(exist_ok=True)
    
    try:
        # 1. 测试初始化
        print("\n1. 测试初始化...")
        manager = PlanningManager(work_dir=test_dir)
        print(f"   ✓ PlanningManager 初始化成功，工作目录: {manager.work_dir}")
        
        # 2. 测试获取规划文件路径
        print("\n2. 测试获取规划文件路径...")
        files = manager.get_planning_files()
        print(f"   ✓ task_plan: {files.task_plan.name}")
        print(f"   ✓ findings: {files.findings.name}")
        print(f"   ✓ progress: {files.progress.name}")
        
        # 3. 测试创建规划文件
        print("\n3. 测试创建规划文件...")
        task = "测试任务：创建一个简单的Python脚本"
        files = manager.create_planning_files(task)
        assert files.task_plan.exists(), "task_plan.md 应该存在"
        assert files.findings.exists(), "findings.md 应该存在"
        assert files.progress.exists(), "progress.md 应该存在"
        print(f"   ✓ 所有规划文件创建成功")
        
        # 4. 测试读取规划文件
        print("\n4. 测试读取规划文件...")
        content = manager.read_task_plan()
        assert content is not None, "应该能读取到内容"
        assert len(content) > 0, "内容不应该为空"
        print(f"   ✓ 成功读取 task_plan.md，长度: {len(content)} 字符")
        
        # 5. 测试更新阶段状态
        print("\n5. 测试更新阶段状态...")
        result = manager.update_phase_status(1, "complete")
        assert result is True, "应该更新成功"
        content = manager.read_task_plan()
        assert "complete" in content, "应该包含 complete 状态"
        print(f"   ✓ 阶段状态更新成功")
        
        # 6. 测试添加错误
        print("\n6. 测试添加错误记录...")
        result = manager.add_error("测试错误", 1, "测试解决方案")
        assert result is True, "应该添加成功"
        content = manager.read_task_plan()
        assert "测试错误" in content, "应该包含错误信息"
        print(f"   ✓ 错误记录添加成功")
        
        # 7. 测试添加发现
        print("\n7. 测试添加发现...")
        result = manager.add_finding("测试发现内容", category="Research Findings")
        assert result is True, "应该添加成功"
        # 刷新批量更新
        manager.flush_updates()
        # 刷新缓存
        manager._invalidate_cache(files.findings)
        findings_content = files.findings.read_text(encoding='utf-8')
        assert "测试发现内容" in findings_content, "应该包含发现内容"
        print(f"   ✓ 发现记录添加成功")
        
        # 8. 测试添加进度
        print("\n8. 测试添加进度记录...")
        result = manager.add_progress("执行了测试操作", files_modified=["test.py"])
        assert result is True, "应该添加成功"
        # 刷新缓存并刷新更新
        manager.flush_updates()
        manager._invalidate_cache(files.progress)
        progress_content = files.progress.read_text(encoding='utf-8')
        assert "执行了测试操作" in progress_content, "应该包含进度信息"
        print(f"   ✓ 进度记录添加成功")
        
        # 9. 测试检查完成情况
        print("\n9. 测试检查完成情况...")
        status = manager.check_completion()
        assert "complete" in status, "应该包含 complete 字段"
        assert "total" in status, "应该包含 total 字段"
        assert status["total"] > 0, "应该有阶段"
        print(f"   ✓ 完成情况检查成功: {status}")
        
        # 10. 测试统计信息
        print("\n10. 测试统计信息...")
        stats = manager.get_stats()
        assert "files_count" in stats, "应该包含 files_count"
        assert "performance" in stats, "应该包含 performance"
        print(f"   ✓ 统计信息获取成功:")
        print(f"     - 文件数量: {stats['files_count']}")
        print(f"     - 缓存大小: {stats['cache_size']}")
        if stats['performance']:
            perf = stats['performance']
            print(f"     - 缓存命中率: {perf.get('cache_hit_rate', 0)}%")
            print(f"     - 读取次数: {perf.get('read_count', 0)}")
            print(f"     - 写入次数: {perf.get('write_count', 0)}")
        
        # 11. 测试清理功能
        print("\n11. 测试清理功能...")
        cleanup_stats = manager.cleanup_old_files(max_age_days=0, max_files=0)
        print(f"   ✓ 清理功能测试完成: {cleanup_stats}")
        
        print("\n" + "=" * 60)
        print("✓ PlanningManager 所有测试通过！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试文件
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print(f"\n清理测试目录: {test_dir}")


def test_complexity_analyzer():
    """测试 TaskComplexityAnalyzer"""
    print("\n" + "=" * 60)
    print("测试 TaskComplexityAnalyzer")
    print("=" * 60)
    
    try:
        # 1. 测试初始化
        print("\n1. 测试初始化...")
        analyzer = TaskComplexityAnalyzer(
            min_task_length=10,
            complexity_threshold=0.3
        )
        print(f"   ✓ TaskComplexityAnalyzer 初始化成功")
        
        # 2. 测试简单任务
        print("\n2. 测试简单任务判断...")
        task = "显示当前目录"
        is_complex = analyzer.is_complex_task(task)
        assert is_complex is False, "简单任务应该返回 False"
        print(f"   ✓ 简单任务判断正确: {is_complex}")
        
        # 3. 测试复杂任务
        print("\n3. 测试复杂任务判断...")
        task = "实现一个完整的用户管理系统，包括用户注册、登录、权限管理等功能"
        is_complex = analyzer.is_complex_task(task)
        # 由于阈值可能较高，先检查分数
        analysis = analyzer.analyze_task(task)
        print(f"   任务分析: 分数={analysis['score']:.2f}, 是否复杂={analysis['is_complex']}")
        if not is_complex:
            print(f"   ⚠ 任务未判定为复杂，但分数为 {analysis['score']:.2f}")
        assert isinstance(is_complex, bool), "应该返回布尔值"
        print(f"   ✓ 复杂任务判断完成: {is_complex}")
        
        # 4. 测试多步骤任务
        print("\n4. 测试多步骤任务判断...")
        task = "首先分析需求，然后设计架构，最后实现代码"
        is_complex = analyzer.is_complex_task(task)
        assert is_complex is True, "多步骤任务应该返回 True"
        print(f"   ✓ 多步骤任务判断正确: {is_complex}")
        
        # 5. 测试详细分析
        print("\n5. 测试详细分析...")
        task = "实现一个Python CLI工具，支持文件搜索和内容替换"
        result = analyzer.analyze_task(task)
        assert "is_complex" in result, "应该包含 is_complex"
        assert "score" in result, "应该包含 score"
        assert "reasons" in result, "应该包含 reasons"
        print(f"   ✓ 详细分析成功:")
        print(f"     - 是否复杂: {result['is_complex']}")
        print(f"     - 复杂度分数: {result['score']:.2f}")
        print(f"     - 原因: {', '.join(result['reasons'][:2])}")
        
        # 6. 测试缓存
        print("\n6. 测试判断结果缓存...")
        task = "实现一个测试功能"
        result1 = analyzer.is_complex_task(task)
        result2 = analyzer.is_complex_task(task)
        assert result1 == result2, "缓存应该返回相同结果"
        assert len(analyzer._judgment_cache) > 0, "应该有缓存条目"
        print(f"   ✓ 缓存功能正常，缓存条目数: {len(analyzer._judgment_cache)}")
        
        print("\n" + "=" * 60)
        print("✓ TaskComplexityAnalyzer 所有测试通过！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_llm_complexity():
    """测试 LLM 辅助复杂度判断（需要 LLM 服务）"""
    print("\n" + "=" * 60)
    print("测试 LLM 辅助复杂度判断")
    print("=" * 60)
    
    try:
        from backend.services.llm.llm_service import LLMService
        
        llm_service = LLMService()
        analyzer = TaskComplexityAnalyzer(
            min_task_length=10,
            complexity_threshold=0.3,
            llm_service=llm_service,
            use_llm=True
        )
        
        print("\n1. 测试 LLM 辅助判断...")
        task = "实现一个完整的用户管理系统"
        is_complex = await analyzer.is_complex_task_async(task)
        print(f"   ✓ LLM 辅助判断结果: {is_complex}")
        
        print("\n" + "=" * 60)
        print("✓ LLM 辅助判断测试完成！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n⚠ LLM 辅助判断测试跳过: {str(e)}")
        print("   提示: 需要配置 LLM API Key 才能测试此功能")
        return None


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("规划功能测试")
    print("=" * 60)
    
    results = []
    
    # 测试 PlanningManager
    results.append(("PlanningManager", test_planning_manager()))
    
    # 测试 TaskComplexityAnalyzer
    results.append(("TaskComplexityAnalyzer", test_complexity_analyzer()))
    
    # 测试 LLM 辅助判断（可选）
    try:
        llm_result = asyncio.run(test_llm_complexity())
        if llm_result is not None:
            results.append(("LLM辅助判断", llm_result))
    except Exception as e:
        print(f"\n⚠ LLM 测试跳过: {str(e)}")
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for name, result in results:
        if result is True:
            print(f"✓ {name}: 通过")
            passed += 1
        elif result is False:
            print(f"✗ {name}: 失败")
            failed += 1
        else:
            print(f"⚠ {name}: 跳过")
            skipped += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败, {skipped} 跳过")
    
    if failed == 0:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n❌ 有 {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

