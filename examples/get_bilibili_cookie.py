#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import json
import uuid
from pathlib import Path
from playwright.async_api import async_playwright

# 添加父目录到模块搜索路径
sys.path.append(str(Path(__file__).parent.parent))

from conf import BASE_DIR

async def get_bilibili_cookie():
    """获取B站cookie"""
    print("🎬 开始获取B站Cookie...")
    print("=" * 50)
    
    try:
        async with async_playwright() as playwright:
            print("🔧 正在启动浏览器...")
            print("请在浏览器中完成B站登录")
            
            # 启动浏览器
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            # 访问B站登录页面
            await page.goto("https://passport.bilibili.com/login")
            print("📱 请扫码或账号密码登录B站")
            print("✅ 登录成功后，请点击浏览器调试器的继续按钮...")
            
            # 暂停等待用户手动登录
            await page.pause()
            
            # 检查是否登录成功
            try:
                await page.goto("https://space.bilibili.com")
                await page.wait_for_selector(".h-name", timeout=10000)
                print("✅ 检测到登录成功")
            except:
                print("❌ 未检测到登录状态，请重新登录")
                await browser.close()
                return False
            
            # 获取cookies
            cookies = await context.cookies()
            
            # 构建cookie数据
            cookie_data = build_bilibili_cookie_data(cookies)
            
            # 保存到cookiesFile目录
            cookie_filename = f"{uuid.uuid4()}.json"
            final_cookie_path = Path(BASE_DIR / "cookiesFile" / cookie_filename)
            
            with open(final_cookie_path, 'w', encoding='utf-8') as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ B站Cookie文件生成成功: {cookie_filename}")
            print(f"文件路径: {final_cookie_path}")
            print("现在可以使用B站平台进行上传了")
            
            await browser.close()
            return True
            
    except Exception as e:
        print(f"❌ 获取Cookie失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def build_bilibili_cookie_data(cookies):
    """构建B站cookie数据格式"""
    # 提取关键的cookie字段
    cookie_fields = ["SESSDATA", "bili_jct", "DedeUserID__ckMd5", "DedeUserID", "buvid3", "b_nut"]
    
    # 构建标准cookie格式
    standard_cookies = []
    cookie_info = {"cookies": []}
    cookie_dict = {}
    
    for cookie in cookies:
        if cookie['name'] in cookie_fields:
            # 添加到标准格式
            standard_cookies.append({
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': cookie.get('domain', '.bilibili.com'),
                'path': cookie.get('path', '/'),
                'expires': -1,
                'httpOnly': cookie.get('httpOnly', False),
                'secure': cookie.get('secure', False),
                'sameSite': cookie.get('sameSite', 'Lax')
            })
            
            # 添加到biliup格式（用于extract_keys_from_json函数）
            cookie_info["cookies"].append({
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': cookie.get('domain', '.bilibili.com'),
                'path': cookie.get('path', '/'),
                'expires': cookie.get('expires', -1),
                'httpOnly': cookie.get('httpOnly', False),
                'secure': cookie.get('secure', False),
                'sameSite': cookie.get('sameSite', 'Lax')
            })
            
            # 构建字典格式（用于B站上传器）
            cookie_dict[cookie['name']] = cookie['value']
    
    # 构建兼容的cookie格式
    return {
        'cookies': standard_cookies,
        'origins': [],
        # biliup格式，供extract_keys_from_json使用
        'cookie_info': cookie_info,
        'token_info': {},
        # 字典格式，供B站上传器直接使用
        'cookie_dict': cookie_dict
    }

if __name__ == '__main__':
    success = asyncio.run(get_bilibili_cookie())
    if success:
        print("\n🎉 B站Cookie获取完成！")
        print("现在可以运行以下命令进行B站视频上传：")
        print("python batch_upload_by_date.py --platform bilibili --date 2025-06-29 --no-schedule")
    else:
        print("\n❌ B站Cookie获取失败，请重试")
