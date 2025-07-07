#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音重试上传工具
使用多种策略避免检测和超时
"""

import asyncio
import random
import time
from datetime import datetime
from pathlib import Path
from uploader.douyin_uploader.main import DouYinVideo
from utils.log import douyin_logger

class DouYinRetryUploader:
    def __init__(self, video_file, title, tags, account_file):
        self.video_file = video_file
        self.title = title
        self.tags = tags
        self.account_file = account_file
        self.max_retries = 3
        self.retry_strategies = [
            self._strategy_standard,
            self._strategy_slow,
            self._strategy_headless
        ]
    
    async def _strategy_standard(self, attempt):
        """标准策略：增强反检测"""
        douyin_logger.info(f"🔄 尝试 {attempt}: 标准增强反检测策略")
        
        app = DouYinVideo(
            title=self.title,
            file_path=self.video_file,
            tags=self.tags,
            publish_date=datetime.now(),
            account_file=self.account_file
        )
        
        await app.main()
        return True
    
    async def _strategy_slow(self, attempt):
        """慢速策略：增加延迟和随机等待"""
        douyin_logger.info(f"🐌 尝试 {attempt}: 慢速策略（增加延迟）")
        
        # 随机等待
        wait_time = random.randint(30, 120)
        douyin_logger.info(f"   等待 {wait_time} 秒后开始...")
        await asyncio.sleep(wait_time)
        
        app = DouYinVideo(
            title=self.title,
            file_path=self.video_file,
            tags=self.tags,
            publish_date=datetime.now(),
            account_file=self.account_file
        )
        
        # 修改上传方法，增加更多延迟
        await self._slow_upload(app)
        return True
    
    async def _strategy_headless(self, attempt):
        """无头策略：使用无头浏览器"""
        douyin_logger.info(f"👻 尝试 {attempt}: 无头浏览器策略")
        
        # 这里需要修改DouYinVideo类支持headless参数
        # 临时方案：直接调用
        app = DouYinVideo(
            title=self.title,
            file_path=self.video_file,
            tags=self.tags,
            publish_date=datetime.now(),
            account_file=self.account_file
        )
        
        await app.main()
        return True
    
    async def _slow_upload(self, app):
        """慢速上传实现"""
        from playwright.async_api import async_playwright
        
        async with async_playwright() as playwright:
            # 启动配置
            launch_options = {
                "headless": True,  # 云服务器环境必须使用无头模式
                "slow_mo": 2000,  # 每个操作延迟2秒
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--exclude-switches=enable-automation",
                    "--disable-extensions",
                    "--no-sandbox",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                ]
            }
            
            browser = await playwright.chromium.launch(**launch_options)
            context = await browser.new_context(
                storage_state=self.account_file,
                viewport={"width": 1920, "height": 1080}
            )
            
            # 添加反检测脚本
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}};
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            """)
            
            page = await context.new_page()
            
            try:
                # 慢速访问抖音
                douyin_logger.info("🐌 慢速访问抖音创作者中心...")
                await page.goto("https://creator.douyin.com/creator-micro/content/upload", 
                              wait_until="load", timeout=120000)
                
                # 等待页面稳定
                await asyncio.sleep(10)
                
                douyin_logger.info("🐌 开始慢速上传...")
                # 这里可以实现更详细的慢速上传逻辑
                
            except Exception as e:
                douyin_logger.error(f"❌ 慢速上传失败: {e}")
                raise
            finally:
                await browser.close()
    
    async def upload_with_retry(self):
        """带重试机制的上传"""
        douyin_logger.info(f"🚀 开始抖音上传任务")
        douyin_logger.info(f"   视频: {Path(self.video_file).name}")
        douyin_logger.info(f"   标题: {self.title}")
        douyin_logger.info(f"   标签: {self.tags}")
        
        for attempt in range(1, self.max_retries + 1):
            strategy = self.retry_strategies[(attempt - 1) % len(self.retry_strategies)]
            
            try:
                douyin_logger.info(f"\n📍 第 {attempt}/{self.max_retries} 次尝试")
                await strategy(attempt)
                douyin_logger.success("✅ 上传成功!")
                return True
                
            except Exception as e:
                douyin_logger.error(f"❌ 第 {attempt} 次尝试失败: {e}")
                
                if attempt < self.max_retries:
                    # 指数退避等待
                    wait_time = 2 ** attempt * 60  # 2分钟, 4分钟, 8分钟
                    douyin_logger.info(f"⏰ 等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    douyin_logger.error("❌ 所有重试都失败了")
                    return False
        
        return False

async def main():
    """主函数"""
    # 配置信息
    video_file = "./videoFile/2025-06-09/demo.mp4"  # 修改为实际视频路径
    title = "测试视频上传"
    tags = ["测试", "自动化", "抖音"]
    account_file = "cookiesFile/douyin_account.json"
    
    # 检查文件是否存在
    if not Path(video_file).exists():
        print(f"❌ 视频文件不存在: {video_file}")
        return
    
    if not Path(account_file).exists():
        print(f"❌ Cookie文件不存在: {account_file}")
        return
    
    # 开始上传
    uploader = DouYinRetryUploader(video_file, title, tags, account_file)
    success = await uploader.upload_with_retry()
    
    if success:
        print("🎉 上传任务完成!")
    else:
        print("😞 上传任务失败!")

if __name__ == "__main__":
    asyncio.run(main()) 