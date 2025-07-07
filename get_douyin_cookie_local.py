#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地运行的抖音cookie获取脚本
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def get_douyin_cookie_local():
    """本地获取抖音cookie"""
    
    # 创建保存目录
    current_dir = Path(__file__).parent
    cookies_dir = current_dir / "cookiesFile"
    cookies_dir.mkdir(exist_ok=True)
    
    # 统一使用cookiesFile目录
    cookie_file = cookies_dir / "douyin_account.json"
    
    async with async_playwright() as p:
        # 启动浏览器（有头模式）
        browser = await p.chromium.launch(headless=False)
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        try:
            print("🚀 正在打开抖音创作者中心...")
            await page.goto('https://creator.douyin.com/')
            
            print("📱 请在打开的浏览器中登录您的抖音账号")
            print("   登录完成后，按Enter键继续...")
            input()
            
            print("✅ 正在保存cookie...")
            
            # 获取所有cookie
            cookies = await context.cookies()
            
            # 保存cookie到文件
            cookie_data = {
                'cookies': cookies,
                'user_agent': await page.evaluate('navigator.userAgent'),
                'timestamp': asyncio.get_event_loop().time()
            }
            
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Cookie已保存到: {cookie_file}")
            print("🎉 抖音账号配置完成！")
            
            return True
                
        except Exception as e:
            print(f"❌ 获取cookie失败: {e}")
            return False
            
        finally:
            await browser.close()

if __name__ == '__main__':
    print("🤖 抖音Cookie获取工具 (本地版)")
    print("=" * 50)
    
    result = asyncio.run(get_douyin_cookie_local())
    
    if result:
        print("\n✅ 设置完成！")
        print("请将cookiesFile/douyin_account.json文件上传到云服务器")
    else:
        print("\n❌ 设置失败，请重试") 