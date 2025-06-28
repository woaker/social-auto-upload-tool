#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音增强连接测试工具
支持代理配置和反检测功能测试
"""

import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# 配置信息
DOUYIN_COOKIE_FILE = "douyin_account.json"
DOUYIN_URL = "https://creator.douyin.com/"

# 代理配置示例（如果需要）
PROXY_CONFIG = {
    # "server": "http://proxy-server:port",
    # "username": "username",  # 可选
    # "password": "password"   # 可选
}

async def test_douyin_connection(use_proxy=False):
    """测试抖音连接"""
    print("🧪 抖音增强连接测试工具")
    print("=" * 50)
    
    # 检查cookie文件
    cookie_file = Path(DOUYIN_COOKIE_FILE)
    if not cookie_file.exists():
        print(f"❌ 未找到cookie文件: {DOUYIN_COOKIE_FILE}")
        return False
    
    print(f"✅ 找到抖音cookie文件: {DOUYIN_COOKIE_FILE}")
    
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        print("✅ Cookie已加载")
    except Exception as e:
        print(f"❌ Cookie加载失败: {e}")
        return False
    
    async with async_playwright() as playwright:
        # 浏览器启动配置
        launch_options = {
            "headless": False,  # 设为True可无头运行
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--exclude-switches=enable-automation", 
                "--disable-extensions-except=",
                "--disable-extensions",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding"
            ]
        }
        
        # 如果启用代理
        if use_proxy and PROXY_CONFIG.get("server"):
            launch_options["proxy"] = PROXY_CONFIG
            print(f"🌐 使用代理: {PROXY_CONFIG['server']}")
        
        try:
            browser = await playwright.chromium.launch(**launch_options)
            
            # 创建上下文
            context = await browser.new_context(
                storage_state=DOUYIN_COOKIE_FILE,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.6533.120 Safari/537.36',
                viewport={"width": 1920, "height": 1080},
                extra_http_headers={
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            # 添加反检测脚本
            await context.add_init_script("""
                // 隐藏webdriver标识
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                
                // 伪造插件信息
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                
                // 伪造语言信息
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                
                // 添加chrome对象
                window.chrome = {runtime: {}};
                
                // 伪造权限API
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({query: () => Promise.resolve({state: 'granted'})})
                });
                
                // 伪造硬件并发
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4});
                
                // 伪造平台信息
                Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                
                // 删除自动化相关属性
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """)
            
            page = await context.new_page()
            
            print("🚀 测试访问抖音创作者中心...")
            
            # 访问抖音创作者中心
            await page.goto(DOUYIN_URL, wait_until="load", timeout=60000)
            
            # 等待页面加载
            await asyncio.sleep(3)
            
            # 检测页面状态
            title = await page.title()
            current_url = page.url
            
            print(f"📄 页面标题: {title}")
            print(f"🔗 当前URL: {current_url}")
            
            # 检查是否成功访问
            if "creator.douyin.com" in current_url:
                print("✅ 成功访问抖音创作者中心!")
                
                # 检查登录状态
                login_elements = await page.locator('text="手机号登录"').count()
                qr_elements = await page.locator('text="扫码登录"').count()
                
                if login_elements > 0 or qr_elements > 0:
                    print("⚠️  检测到登录页面，Cookie可能已过期")
                    return False
                else:
                    print("✅ Cookie有效，已登录状态")
                    
                    # 尝试访问上传页面
                    try:
                        await page.goto("https://creator.douyin.com/creator-micro/content/upload", 
                                       wait_until="load", timeout=30000)
                        await asyncio.sleep(2)
                        
                        upload_title = await page.title()
                        print(f"📤 上传页面标题: {upload_title}")
                        print("✅ 成功访问上传页面!")
                        return True
                    except Exception as e:
                        print(f"⚠️  无法访问上传页面: {e}")
                        return False
            else:
                print("❌ 访问失败，可能被重定向")
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
    print("选择测试模式:")
    print("1. 直连测试")
    print("2. 代理测试")
    
    try:
        choice = input("请选择 (1/2): ").strip()
        use_proxy = choice == "2"
        
        if use_proxy and not PROXY_CONFIG.get("server"):
            print("❌ 请先配置代理信息")
            return
        
        result = asyncio.run(test_douyin_connection(use_proxy))
        
        if result:
            print("\n🎉 测试成功! 可以尝试上传视频")
        else:
            print("\n❌ 测试失败! 需要重新获取Cookie或配置代理")
            
    except KeyboardInterrupt:
        print("\n⚠️  测试被中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main() 