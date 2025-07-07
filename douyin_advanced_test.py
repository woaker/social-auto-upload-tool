#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音高级访问测试工具
使用多种策略绕过反自动化检测
"""

import asyncio
import json
import random
import time
from pathlib import Path
from playwright.async_api import async_playwright
from douyin_config import get_browser_config, get_context_config, get_anti_detection_script

class DouYinAdvancedTester:
    def __init__(self, cookie_file="cookiesFile/douyin_account.json"):
        self.cookie_file = cookie_file
        self.strategies = [
            self._strategy_slow_human,
            self._strategy_multi_step,
            self._strategy_indirect_access,
            self._strategy_mobile_ua
        ]
        
    async def _strategy_slow_human(self):
        """策略1：模拟人类慢速访问"""
        print("🐌 策略1: 模拟人类慢速访问")
        
        launch_options, env = get_browser_config()
        launch_options["slow_mo"] = 3000  # 每个操作延迟3秒
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**launch_options)
            
            context_config = get_context_config()
            context_config["storage_state"] = self.cookie_file
            
            context = await browser.new_context(**context_config)
            await context.add_init_script(get_anti_detection_script())
            
            page = await context.new_page()
            
            try:
                # 先访问主页，模拟真实用户行为
                print("   🏠 先访问抖音主页...")
                await page.goto("https://www.douyin.com/", timeout=30000)
                await asyncio.sleep(random.randint(5, 10))
                
                # 模拟滚动行为
                print("   📜 模拟滚动...")
                await page.evaluate("window.scrollTo(0, 300)")
                await asyncio.sleep(random.randint(2, 5))
                
                # 再访问创作者中心
                print("   🎨 访问创作者中心...")
                await page.goto("https://creator.douyin.com/", timeout=60000)
                
                title = await page.title()
                print(f"   ✅ 成功! 页面标题: {title}")
                return True
                
            except Exception as e:
                print(f"   ❌ 失败: {e}")
                return False
            finally:
                await browser.close()
    
    async def _strategy_multi_step(self):
        """策略2：多步骤渐进访问"""
        print("🪜 策略2: 多步骤渐进访问")
        
        launch_options, env = get_browser_config()
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**launch_options)
            
            context_config = get_context_config()
            context_config["storage_state"] = self.cookie_file
            
            context = await browser.new_context(**context_config)
            await context.add_init_script(get_anti_detection_script())
            
            page = await context.new_page()
            
            try:
                # 步骤1：访问百度
                print("   🔍 步骤1: 访问百度...")
                await page.goto("https://www.baidu.com", timeout=30000)
                await asyncio.sleep(3)
                
                # 步骤2：搜索抖音
                print("   🔍 步骤2: 搜索抖音...")
                await page.fill("input[name='wd']", "抖音创作者中心")
                await asyncio.sleep(2)
                await page.keyboard.press("Enter")
                await asyncio.sleep(5)
                
                # 步骤3：直接导航到创作者中心
                print("   🎯 步骤3: 导航到创作者中心...")
                await page.goto("https://creator.douyin.com/", timeout=60000)
                
                title = await page.title()
                print(f"   ✅ 成功! 页面标题: {title}")
                return True
                
            except Exception as e:
                print(f"   ❌ 失败: {e}")
                return False
            finally:
                await browser.close()
    
    async def _strategy_indirect_access(self):
        """策略3：间接访问"""
        print("🔄 策略3: 间接访问")
        
        launch_options, env = get_browser_config()
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**launch_options)
            
            context_config = get_context_config()
            context_config["storage_state"] = self.cookie_file
            
            context = await browser.new_context(**context_config)
            await context.add_init_script(get_anti_detection_script())
            
            page = await context.new_page()
            
            try:
                # 先访问字节跳动官网
                print("   🏢 访问字节跳动官网...")
                await page.goto("https://www.bytedance.com/", timeout=30000)
                await asyncio.sleep(3)
                
                # 再访问抖音相关页面
                print("   📱 访问抖音相关页面...")
                await page.goto("https://www.douyin.com/", timeout=30000)
                await asyncio.sleep(5)
                
                # 最后访问创作者中心
                print("   🎨 最后访问创作者中心...")
                await page.goto("https://creator.douyin.com/", timeout=60000)
                
                title = await page.title()
                print(f"   ✅ 成功! 页面标题: {title}")
                return True
                
            except Exception as e:
                print(f"   ❌ 失败: {e}")
                return False
            finally:
                await browser.close()
    
    async def _strategy_mobile_ua(self):
        """策略4：使用手机用户代理"""
        print("📱 策略4: 使用手机用户代理")
        
        launch_options, env = get_browser_config()
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**launch_options)
            
            # 修改为手机用户代理
            mobile_context = {
                "storage_state": self.cookie_file,
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
                "viewport": {"width": 375, "height": 667},
                "device_scale_factor": 2,
                "is_mobile": True,
                "has_touch": True,
                "extra_http_headers": {
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Accept': '*/*',
                    'Connection': 'keep-alive',
                }
            }
            
            context = await browser.new_context(**mobile_context)
            await context.add_init_script(get_anti_detection_script())
            
            page = await context.new_page()
            
            try:
                print("   📱 使用手机模式访问...")
                await page.goto("https://creator.douyin.com/", timeout=60000)
                
                title = await page.title()
                print(f"   ✅ 成功! 页面标题: {title}")
                return True
                
            except Exception as e:
                print(f"   ❌ 失败: {e}")
                return False
            finally:
                await browser.close()
    
    async def test_all_strategies(self):
        """测试所有策略"""
        print("🧪 抖音高级访问测试工具")
        print("=" * 50)
        
        # 检查cookie文件
        if not Path(self.cookie_file).exists():
            print(f"❌ 未找到cookie文件: {self.cookie_file}")
            return False
        
        print(f"✅ 找到抖音cookie文件: {self.cookie_file}")
        
        success_count = 0
        total_strategies = len(self.strategies)
        
        for i, strategy in enumerate(self.strategies, 1):
            print(f"\n📍 测试策略 {i}/{total_strategies}")
            print("-" * 30)
            
            try:
                success = await strategy()
                if success:
                    success_count += 1
                    print(f"✅ 策略{i}成功!")
                    # 如果有一个策略成功，可以继续测试其他策略或直接返回
                    break
                else:
                    print(f"❌ 策略{i}失败")
                    
            except Exception as e:
                print(f"❌ 策略{i}出错: {e}")
            
            # 策略间等待
            if i < total_strategies:
                wait_time = random.randint(10, 30)
                print(f"⏰ 等待{wait_time}秒后尝试下一个策略...")
                await asyncio.sleep(wait_time)
        
        print("\n" + "=" * 50)
        print("📊 测试结果:")
        print(f"   成功策略数: {success_count}/{total_strategies}")
        
        if success_count > 0:
            print("🎉 至少有一个策略成功! 可以尝试上传视频")
            return True
        else:
            print("😞 所有策略都失败了，建议考虑其他解决方案")
            return False

async def main():
    """主函数"""
    tester = DouYinAdvancedTester()
    await tester.test_all_strategies()

if __name__ == "__main__":
    asyncio.run(main()) 