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
from douyin_config import get_browser_config, get_context_config, get_anti_detection_script, print_environment_info

# 配置信息
DOUYIN_COOKIE_FILE = "douyin_account.json"
DOUYIN_URL = "https://creator.douyin.com/"

# 代理配置（来自notepad）
PROXY_CONFIG = {
    "server": "http://54.226.20.77:5678",
    # 注意：这个代理使用API密钥认证，可能需要特殊配置
    # "username": "username",  # 如果需要基础认证
    # "password": "password"   # 如果需要基础认证
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
    
    # 打印环境信息
    print_environment_info()
    
    async with async_playwright() as playwright:
        # 获取浏览器配置
        launch_options, env = get_browser_config()
        
        # 如果启用代理
        if use_proxy and PROXY_CONFIG.get("server"):
            launch_options["proxy"] = PROXY_CONFIG
            print(f"🌐 使用代理: {PROXY_CONFIG['server']}")
        
        try:
            browser = await playwright.chromium.launch(**launch_options)
            
            # 获取上下文配置
            context_config = get_context_config()
            context_config["storage_state"] = DOUYIN_COOKIE_FILE
            
            # 创建上下文
            context = await browser.new_context(**context_config)
            
            # 添加反检测脚本
            await context.add_init_script(get_anti_detection_script())
            
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