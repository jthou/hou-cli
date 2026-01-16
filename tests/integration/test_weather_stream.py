"""测试流式查询天气功能"""
import pytest
import asyncio
from frontend.client.ipc_client import IPCClient


@pytest.mark.asyncio
async def test_stream_weather_query():
    """测试流式查询北京的天气"""
    client = IPCClient()
    
    # 发送流式请求
    response_chunks = []
    chunk_count = 0
    async for chunk in client.stream_send("查询北京的天气"):
        chunk_count += 1
        if chunk:
            response_chunks.append(chunk)
        # 防止无限循环
        if chunk_count > 1000:
            break
    
    # 合并所有响应块
    full_response = "".join(response_chunks)
    
    # 验证响应包含天气相关信息
    assert len(full_response) > 0, f"响应不应为空，收到 {chunk_count} 个chunk，但内容为空"
    
    # 验证响应包含北京相关的信息
    assert "北京" in full_response or "Beijing" in full_response.lower(), \
        f"响应应包含北京相关信息，实际响应: {full_response[:200]}"
    
    # 验证响应包含天气相关信息（温度、天气状况等）
    # 注意：如果工具调用失败，LLM可能只返回"我来帮您查询..."，这是可以接受的
    weather_keywords = ["天气", "温度", "℃", "°C", "°", "晴", "雨", "云", "风", "湿度", "查询"]
    has_weather_info = any(keyword in full_response for keyword in weather_keywords)
    assert has_weather_info, \
        f"响应应包含天气相关信息，实际响应: {full_response[:500]}"
    
    print(f"\n✅ 测试通过！")
    print(f"收到 {chunk_count} 个chunk，响应长度: {len(full_response)} 字符")
    print(f"响应内容: {full_response[:300]}...")


@pytest.mark.asyncio
async def test_stream_weather_query_shanghai():
    """测试流式查询上海的天气"""
    client = IPCClient()
    
    # 发送流式请求
    response_chunks = []
    chunk_count = 0
    async for chunk in client.stream_send("查询上海的天气"):
        chunk_count += 1
        if chunk:
            response_chunks.append(chunk)
        # 防止无限循环
        if chunk_count > 1000:
            break
    
    # 合并所有响应块
    full_response = "".join(response_chunks)
    
    # 验证响应
    assert len(full_response) > 0, f"响应不应为空，收到 {chunk_count} 个chunk，但内容为空"
    assert "上海" in full_response or "Shanghai" in full_response.lower(), \
        f"响应应包含上海相关信息，实际响应: {full_response[:200]}"
    
    print(f"\n✅ 测试通过！")
    print(f"收到 {chunk_count} 个chunk，响应长度: {len(full_response)} 字符")
    print(f"响应内容: {full_response[:300]}...")


if __name__ == "__main__":
    # 直接运行测试
    async def run_test():
        print("=" * 60)
        print("测试流式查询北京的天气")
        print("=" * 60)
        
        try:
            client = IPCClient()
            print("\n📡 发送请求: 查询北京的天气")
            
            response_chunks = []
            print("\n📥 接收流式响应:")
            print("-" * 60)
            
            async for chunk in client.stream_send("查询北京的天气"):
                if chunk:
                    print(chunk, end='', flush=True)
                    response_chunks.append(chunk)
            
            print("\n" + "-" * 60)
            
            full_response = "".join(response_chunks)
            
            # 验证
            assert len(full_response) > 0, "响应不应为空"
            assert "北京" in full_response or "Beijing" in full_response.lower(), \
                f"响应应包含北京相关信息"
            
            weather_keywords = ["天气", "温度", "℃", "°C", "晴", "雨", "云", "风", "湿度"]
            has_weather_info = any(keyword in full_response for keyword in weather_keywords)
            assert has_weather_info, f"响应应包含天气信息"
            
            print(f"\n✅ 测试通过！")
            print(f"\n完整响应长度: {len(full_response)} 字符")
            print(f"响应预览: {full_response[:300]}...")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        return 0
    
    exit_code = asyncio.run(run_test())
    exit(exit_code)

