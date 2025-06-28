#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书增强连接测试工具
专门用于诊断反自动化检测问题
"""

import asyncio
import json
import random
from pathlib import Path
from playwright.async_api import async_playwright
from douyin_config import get_browser_config, get_context_config, get_anti_detection_script, print_environment_info

# 配置信息
XHS_COOKIE_FILE = "ebd39c7e-4688-11f0-87bd-82265ec8d59d.json"  # 从用户输出中获取
XHS_URL = "https://creator.xiaohongshu.com/"

async def simulate_human_behavior(page):
    """模拟人类行为"""
    # 随机鼠标移动
    await page.mouse.move(random.randint(100, 500), random.randint(100, 400))
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    # 随机滚动
    await page.mouse.wheel(0, random.randint(-100, 100))
    await asyncio.sleep(random.uniform(0.3, 0.8))
    
    # 模拟阅读延迟
    await asyncio.sleep(random.uniform(1, 3))

async def check_login_status(page):
    """检查登录状态"""
    login_indicators = [
        'text="登录"',
        'text="手机号登录"', 
        'text="扫码登录"',
        'button:has-text("登录")',
        'a:has-text("登录")',
        '.login-btn',
        '[class*="login"]'
    ]
    
    for indicator in login_indicators:
        if await page.locator(indicator).count() > 0:
            return False, indicator
    return True, None

async def test_xiaohongshu_connection():
    """测试小红书连接和反检测能力"""
    print("🧪 小红书增强连接测试工具")
    print("=" * 50)
    
    # 检查cookie文件
    cookie_file = Path(XHS_COOKIE_FILE)
    if not cookie_file.exists():
        print(f"❌ 未找到cookie文件: {XHS_COOKIE_FILE}")
        return False
    
    print(f"✅ 找到小红书cookie文件: {XHS_COOKIE_FILE}")
    
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        print("✅ Cookie已加载")
    except Exception as e:
        print(f"❌ Cookie加载失败: {e}")
        return False
    
    # 打印环境信息
    print_environment_info()
    
    async with async_playwright() as playwright:
        # 获取浏览器配置
        launch_options, env = get_browser_config()
        
        try:
            browser = await playwright.chromium.launch(**launch_options)
            
            # 获取上下文配置
            context_config = get_context_config()
            context_config["storage_state"] = XHS_COOKIE_FILE
            
            # 创建上下文
            context = await browser.new_context(**context_config)
            
            # 添加增强反检测脚本
            await context.add_init_script("""
                // 最强反检测脚本
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                window.chrome = {runtime: {}};
                Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})});
                
                // 随机化各种检测点
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4});
                Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
                Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                
                // 时间随机化
                const originalDateNow = Date.now;
                Date.now = () => originalDateNow() + Math.floor(Math.random() * 1000);
                
                // 删除自动化痕迹
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                
                // 伪造触摸事件支持
                Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 1});
            """)
            
            page = await context.new_page()
            
            print("🚀 测试访问小红书创作者中心...")
            
            # 访问小红书创作者中心
            await page.goto(XHS_URL, wait_until="load", timeout=60000)
            
            # 模拟人类行为
            await simulate_human_behavior(page)
            
            # 检测页面状态
            title = await page.title()
            current_url = page.url
            
            print(f"📄 页面标题: {title}")
            print(f"🔗 当前URL: {current_url}")
            
            # 检查登录状态
            is_logged_in, login_indicator = await check_login_status(page)
            
            if not is_logged_in:
                print(f"❌ 检测到登录页面元素: {login_indicator}")
                await page.screenshot(path="xiaohongshu_test_login_detected.png", full_page=True)
                print("📸 已保存登录页面截图: xiaohongshu_test_login_detected.png")
                return False
            else:
                print("✅ 成功访问，未检测到登录页面")
                
                # 尝试访问发布页面
                try:
                    print("🎬 尝试访问发布页面...")
                    await page.goto("https://creator.xiaohongshu.com/publish/publish?from=homepage&target=video", 
                                   wait_until="load", timeout=30000)
                    
                    await simulate_human_behavior(page)
                    
                    # 再次检查登录状态
                    is_still_logged_in, login_indicator = await check_login_status(page)
                    
                    if not is_still_logged_in:
                        print(f"❌ 在访问发布页面时被登出: {login_indicator}")
                        await page.screenshot(path="xiaohongshu_test_publish_logout.png", full_page=True)
                        print("📸 已保存发布页面登出截图: xiaohongshu_test_publish_logout.png")
                        return False
                    else:
                        print("✅ 成功访问发布页面!")
                        
                        # 检查上传元素
                        upload_selectors = [
                            "input.upload-input",
                            "input[type='file'][accept*='video']",
                            "div[class*='upload'] input"
                        ]
                        
                        upload_found = False
                        for selector in upload_selectors:
                            if await page.locator(selector).count() > 0:
                                print(f"✅ 找到上传元素: {selector}")
                                upload_found = True
                                break
                        
                        if not upload_found:
                            print("⚠️  未找到上传元素，可能页面结构已变化")
                        
                        await page.screenshot(path="xiaohongshu_test_success.png", full_page=True)
                        print("📸 已保存成功状态截图: xiaohongshu_test_success.png")
                        return True
                        
                except Exception as e:
                    print(f"❌ 访问发布页面失败: {e}")
                    return False
                
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return False
        finally:
            try:
                await context.close()
                await browser.close()
            except:
                pass

def main():
    """主函数"""
    try:
        result = asyncio.run(test_xiaohongshu_connection())
        
        if result:
            print("\n🎉 测试成功! 小红书连接正常")
            print("💡 建议：可以尝试上传视频")
        else:
            print("\n❌ 测试失败! 小红书检测到了自动化行为")
            print("💡 建议：")
            print("   1. 重新获取Cookie")
            print("   2. 等待一段时间后再试")
            print("   3. 检查账号是否被限制")
            
    except KeyboardInterrupt:
        print("\n⚠️  测试被中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main() 