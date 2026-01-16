"""直接打开浏览器访问百度（使用 Playwright）"""
from playwright.sync_api import sync_playwright
import time

print("=" * 60)
print("打开浏览器访问 www.baidu.com")
print("=" * 60)
print("⚠️  浏览器窗口将打开并访问 www.baidu.com")
print("   窗口将保持打开 15 秒，然后自动关闭")
print()

with sync_playwright() as p:
    # 启动浏览器（显示模式）
    browser = p.chromium.launch(headless=False)
    print("✅ 浏览器启动成功")
    
    # 创建新页面
    page = browser.new_page()
    print("✅ 新页面创建成功")
    
    # 访问百度
    print("正在访问 www.baidu.com...")
    page.goto('https://www.baidu.com')
    print("✅ 访问成功")
    
    # 获取页面信息
    title = page.title()
    url = page.url
    print(f"✅ 页面标题: {title}")
    print(f"✅ 当前 URL: {url}")
    
    print("\n" + "=" * 60)
    print("✅ 浏览器已打开，请查看浏览器窗口")
    print("   窗口将在 15 秒后自动关闭...")
    print("=" * 60)
    
    # 保持打开 15 秒
    time.sleep(15)
    
    browser.close()
    print("\n✅ 浏览器已关闭")


