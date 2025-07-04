#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云服务器版本的抖音cookie获取脚本
使用无头模式，通过二维码登录
"""

import asyncio
import qrcode
from pathlib import Path
from playwright.async_api import async_playwright

from config import BASE_DIR

async def get_douyin_cookie_headless():
    """无头模式获取抖音cookie"""
    
    # 创建保存目录
    cookies_dir = Path(BASE_DIR) / "cookiesFile"
    cookies_dir.mkdir(exist_ok=True)
    
    cookie_file = cookies_dir / "douyin_account.json"
    
    async with async_playwright() as p:
        # 启动无头模式浏览器
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-blink-features=AutomationControlled',  # 禁用自动化检测
                '--disable-infobars',  # 禁用信息栏
                '--window-size=1920,1080',  # 设置窗口大小
                '--start-maximized',  # 最大化窗口
                '--disable-extensions',  # 禁用扩展
                '--disable-popup-blocking',  # 禁用弹窗拦截
                '--disable-setuid-sandbox',
                '--no-zygote',
                '--no-first-run',
                '--disable-notifications'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            geolocation={'latitude': 39.9042, 'longitude': 116.4074},  # 北京坐标
            permissions=['geolocation']
        )
        
        # 添加反检测脚本
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
        """)
        
        page = await context.new_page()
        
        try:
            print("🚀 正在访问抖音创作者中心...")
            
            # 先访问主页
            await page.goto('https://www.douyin.com', wait_until='networkidle')
            await asyncio.sleep(3)  # 等待3秒
            
            # 再访问创作者中心
            await page.goto('https://creator.douyin.com/', wait_until='networkidle')
            
            # 保存页面截图以便调试
            await page.screenshot(path='douyin_login_page.png')
            print("📸 已保存登录页面截图到 douyin_login_page.png")
            
            # 等待二维码出现
            print("⏳ 等待二维码加载...")
            
            # 尝试多个可能的二维码选择器
            qr_selectors = [
                '.semi-modal-content img',
                'img[src*="qrcode"]',
                'img[class*="qrcode"]',
                'img[alt*="qrcode"]',
                '.login-qrcode img'
            ]
            
            qr_img = None
            for selector in qr_selectors:
                try:
                    qr_img = await page.wait_for_selector(selector, timeout=10000)
                    if qr_img:
                        print(f"✅ 找到二维码元素: {selector}")
                        break
                except:
                    continue
            
            if not qr_img:
                print("❌ 未找到二维码元素，尝试其他登录方式...")
                # 尝试点击扫码登录按钮
                try:
                    scan_button = await page.get_by_text('扫码登录').click()
                    await asyncio.sleep(2)
                    # 重新尝试获取二维码
                    for selector in qr_selectors:
                        try:
                            qr_img = await page.wait_for_selector(selector, timeout=10000)
                            if qr_img:
                                print(f"✅ 点击扫码登录后找到二维码元素: {selector}")
                                break
                        except:
                            continue
                except:
                    print("❌ 无法切换到扫码登录")
            
            if qr_img:
                qr_src = await qr_img.get_attribute('src')
                print("📱 请使用抖音APP扫描以下二维码登录:")
                print(f"   二维码链接: {qr_src}")
                
                # 如果可以，生成二维码到终端
                try:
                    import requests
                    response = requests.get(qr_src)
                    if response.status_code == 200:
                        qr = qrcode.QRCode()
                        qr.add_data(qr_src)
                        qr.print_ascii()
                except Exception as e:
                    print(f"   无法显示二维码: {e}")
                    print("   请访问上面的链接")
            else:
                raise Exception("无法获取登录二维码")
            
            # 等待登录成功
            print("⏳ 等待登录成功...")
            print("   请使用抖音APP扫描二维码完成登录")
            
            # 检测登录成功的标志
            success = False
            max_wait = 300  # 最多等待5分钟
            wait_time = 0
            
            while wait_time < max_wait:
                try:
                    # 保存当前页面截图
                    if wait_time % 30 == 0:
                        await page.screenshot(path=f'douyin_login_progress_{wait_time}.png')
                    
                    # 检查是否登录成功
                    current_url = page.url
                    if 'creator.douyin.com' in current_url and 'login' not in current_url:
                        # 检查是否有用户相关元素
                        user_elements = await page.query_selector_all('.avatar, .username, .user-info')
                        if user_elements:
                            success = True
                            break
                    
                    await asyncio.sleep(2)
                    wait_time += 2
                    
                    if wait_time % 30 == 0:
                        print(f"   仍在等待登录... ({wait_time}/{max_wait}秒)")
                        
                except Exception as e:
                    print(f"   检查登录状态时出错: {e}")
                    await asyncio.sleep(2)
                    wait_time += 2
            
            if success:
                print("✅ 登录成功！正在保存cookie...")
                
                # 获取所有cookie
                cookies = await context.cookies()
                
                # 保存cookie到文件
                import json
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
                
            else:
                print("❌ 登录超时，请重新运行脚本")
                return False
                
        except Exception as e:
            print(f"❌ 获取cookie失败: {e}")
            # 保存错误页面截图
            try:
                await page.screenshot(path='douyin_error.png')
                print("📸 已保存错误页面截图到 douyin_error.png")
                # 保存页面内容以便调试
                content = await page.content()
                with open('douyin_error.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                print("📄 已保存错误页面源码到 douyin_error.html")
            except:
                pass
            return False
            
        finally:
            await browser.close()

if __name__ == '__main__':
    print("🤖 抖音Cookie获取工具 (云服务器版)")
    print("=" * 50)
    
    result = asyncio.run(get_douyin_cookie_headless())
    
    if result:
        print("\n✅ 设置完成！现在可以运行批量上传命令:")
        print("python3 batch_upload_by_date.py --platform douyin --date 2025-06-28 --no-schedule")
    else:
        print("\n❌ 设置失败，请检查网络连接后重试") 