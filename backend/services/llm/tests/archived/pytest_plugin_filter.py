"""Pytest 插件过滤器 - 过滤掉有问题的 ROS 插件"""
import sys
from pathlib import Path

def pytest_configure(config):
    """在 pytest 配置时过滤掉有问题的插件"""
    # 获取插件管理器
    plugin_manager = config.pluginmanager
    
    # 要过滤的插件名称
    problematic_plugins = [
        'launch_testing_ros_pytest_entrypoint',
        'launch_testing',
        'colcon_core',
        'ament_lint',
        'ament_xmllint',
        'ament_pep257',
        'ament_copyright',
        'ament_flake8',
    ]
    
    # 尝试取消注册有问题的插件
    for plugin_name in problematic_plugins:
        try:
            # 方法1: 通过名称取消注册
            if hasattr(plugin_manager, 'unregister'):
                # 查找插件
                for name, plugin in list(plugin_manager.list_name_plugin()):
                    if plugin_name in name.lower():
                        try:
                            plugin_manager.unregister(plugin)
                            print(f"✅ 已取消注册插件: {name}")
                        except Exception as e:
                            pass  # 忽略取消注册失败
        except Exception:
            pass
    
    # 方法2: 从 sys.modules 中移除有问题的模块
    modules_to_remove = []
    for module_name in sys.modules:
        if any(problematic in module_name.lower() for problematic in problematic_plugins):
            modules_to_remove.append(module_name)
    
    for module_name in modules_to_remove:
        try:
            del sys.modules[module_name]
        except Exception:
            pass

