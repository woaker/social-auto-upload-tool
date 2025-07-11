#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from playwright.async_api import async_playwright
import os
import json
import sys

async def test_connection():
    print("🔍 测试抖音连接...")
    
    # 获取cookie文件路径
    cookie_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                              "cookiesFile", "douyin_account.json")
    
    if not os.path.exists(cookie_file):
        print(f"❌ Cookie文件不存在: {cookie_file}")
        return False
    
    print(f"✅ 找到cookie文件: {cookie_file}")
    
    # 加载cookie
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookie_data = json.load(f)
        print("✅ Cookie文件加载成功")
    except Exception as e:
        print(f"❌ Cookie文件加载失败: {e}")
        return False
    
    # 启动浏览器
    async with async_playwright() as p:
        # 使用更多浏览器参数
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-gpu',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--no-sandbox',
                '--disable-extensions',
                '--disable-application-cache',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--metrics-recording-only',
                '--mute-audio',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
                '--ignore-certificate-errors',
                '--ignore-ssl-errors',
                '--ignore-certificate-errors-spki-list',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
            ]
        )
        
        # 创建新的上下文
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
        )
        
        # 添加cookie
        if 'cookies' in cookie_data:
            await context.add_cookies(cookie_data['cookies'])
        
        # 创建新页面
        page = await context.new_page()
        
        # 设置超时
        page.set_default_timeout(60000)  # 60秒超时
        
        # 尝试访问抖音创作者平台
        print("🌐 访问抖音创作者平台...")
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                print(f"尝试访问主页 (尝试 {attempt}/{max_retries})...")
                await page.goto("https://creator.douyin.com/", timeout=60000)
                print("✅ 访问成功!")
                
                # 截图保存
                screenshot_path = "douyin_connection_test.png"
                await page.screenshot(path=screenshot_path)
                print(f"✅ 截图已保存: {screenshot_path}")
                
                # 检查是否需要登录
                login_button = await page.query_selector('text="登录"')
                if login_button:
                    print("⚠️ 需要登录，Cookie可能已过期")
                    return False
                else:
                    print("✅ 已登录状态")
                    return True
                
            except Exception as e:
                print(f"⚠️ 访问失败，等待重试... ({attempt}/{max_retries})")
                print(f"错误信息: {e}")
                await asyncio.sleep(5)
        
        print("❌ 多次尝试后仍然无法访问抖音创作者平台")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    if result:
        print("✅ 连接测试成功，可以继续上传操作")
        sys.exit(0)
    else:
        print("❌ 连接测试失败，请检查网络和Cookie")
        sys.exit(1) 