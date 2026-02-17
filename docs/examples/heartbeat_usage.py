"""心跳机制使用示例"""

# ===== 后端使用示例 =====

# 示例 1: 基本使用
async def backend_example():
    """后端心跳监控示例"""
    from backend.infrastructure.monitoring.heartbeat import get_heartbeat_monitor
    
    # 获取监控器（单例模式）
    monitor = get_heartbeat_monitor(interval=30)
    
    # 启动监控
    await monitor.start()
    
    # 获取状态
    status = monitor.get_status()
    print(f"心跳状态: {status}")
    
    # 检查是否健康
    is_healthy = monitor.is_healthy(max_silence_seconds=60)
    print(f"是否健康: {is_healthy}")
    
    # 停止监控
    await monitor.stop()


# ===== 前端使用示例 =====

# 示例 2: 基本使用
async def frontend_example():
    """前端健康监控示例"""
    from frontend.client.health_monitor import HealthMonitor
    
    # 创建监控器
    monitor = HealthMonitor(
        base_url="http://127.0.0.1:8000",
        interval=30,
        timeout=5.0,
        max_failures=3
    )
    
    # 设置回调
    async def on_unhealthy():
        print("后端服务不可用！")
    
    async def on_recovered():
        print("后端服务已恢复！")
    
    monitor.set_callbacks(
        on_unhealthy=on_unhealthy,
        on_recovered=on_recovered
    )
    
    # 启动监控
    await monitor.start()
    
    # 获取状态
    status = monitor.get_status()
    print(f"监控状态: {status}")
    
    # 停止监控
    await monitor.stop()


# 示例 3: 集成到前端主程序
async def frontend_integration_example():
    """前端集成示例"""
    from frontend.client.ipc_client import IPCClient
    from frontend.client.health_monitor import HealthMonitor
    from rich.console import Console
    
    console = Console()
    
    # 创建 IPC 客户端
    client = IPCClient()
    
    # 创建健康监控器
    monitor = HealthMonitor(
        base_url=client.base_url,
        interval=30,
        max_failures=3
    )
    
    # 设置回调
    async def on_unhealthy():
        console.print("[yellow]⚠ 后端服务不可用，尝试重新连接...[/yellow]")
        # 可以在这里实现重连逻辑
        # 例如：尝试重启后端服务
    
    async def on_recovered():
        console.print("[green]✓ 后端服务已恢复[/green]")
    
    monitor.set_callbacks(
        on_unhealthy=on_unhealthy,
        on_recovered=on_recovered
    )
    
    # 启动监控（在后台运行）
    await monitor.start()
    
    try:
        # 主循环
        while True:
            # 检查健康状态
            if not monitor.is_healthy():
                console.print("[red]后端服务不健康，请检查[/red]")
            
            # 执行其他操作...
            await asyncio.sleep(1)
    finally:
        # 停止监控
        await monitor.stop()


# 示例 4: 手动健康检查
def manual_health_check():
    """手动健康检查示例"""
    import httpx
    
    try:
        response = httpx.get("http://127.0.0.1:8000/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            print(f"后端健康: {data}")
            return True
        else:
            print(f"后端不健康: {response.status_code}")
            return False
    except Exception as e:
        print(f"健康检查失败: {e}")
        return False


# 示例 5: 获取心跳状态
def get_heartbeat_status():
    """获取心跳状态示例"""
    import httpx
    
    try:
        response = httpx.get(
            "http://127.0.0.1:8000/api/heartbeat/status",
            timeout=5.0
        )
        if response.status_code == 200:
            data = response.json()
            print(f"心跳状态: {data}")
            return data
        else:
            print(f"获取心跳状态失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"获取心跳状态失败: {e}")
        return None


if __name__ == "__main__":
    import asyncio
    
    # 运行示例
    # asyncio.run(backend_example())
    # asyncio.run(frontend_example())
    # asyncio.run(frontend_integration_example())
    
    # 手动检查
    # manual_health_check()
    # get_heartbeat_status()

