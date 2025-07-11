#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime
import argparse
from playwright.async_api import async_playwright

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uploader.douyin_uploader.main import DouYinVideo
from utils.files_times import get_title_and_hashtags

class EnhancedDouYinUploader:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.cookies_dir = os.path.join(self.base_dir, "cookiesFile")
        self.account_file = os.path.join(self.cookies_dir, "douyin_account.json")
        
    async def setup_browser(self):
        """设置优化的浏览器配置"""
        print("🔧 设置浏览器环境...")
        
        # 检查cookie文件
        if not os.path.exists(self.account_file):
            print(f"❌ Cookie文件不存在: {self.account_file}")
            return None, None, None
        
        print(f"✅ 找到cookie文件: {self.account_file}")
        
        # 加载cookie
        try:
            with open(self.account_file, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)
            print("✅ Cookie文件加载成功")
        except Exception as e:
            print(f"❌ Cookie文件加载失败: {e}")
            return None, None, None
        
        # 启动浏览器
        playwright = await async_playwright().start()
        
        # 使用优化的浏览器参数
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-gpu',
                '--disable-dev-shm-usage',  # 重要：避免使用/dev/shm，防止内存不足
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
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized',
                '--single-process',  # 单进程模式，减少资源占用
                '--no-zygote',       # 禁用zygote进程
                '--disable-breakpad' # 禁用崩溃报告
            ],
            timeout=120000  # 增加启动超时时间到120秒
        )
        
        # 创建新的上下文
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
        )
        
        # 添加cookie
        if 'cookies' in cookie_data:
            await context.add_cookies(cookie_data['cookies'])
        
        return playwright, browser, context
    
    async def test_connection(self, context):
        """测试抖音连接"""
        print("🌐 测试抖音连接...")
        
        # 创建新页面
        page = await context.new_page()
        
        # 设置超时
        page.set_default_timeout(60000)  # 60秒超时
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                print(f"尝试访问主页 (尝试 {attempt}/{max_retries})...")
                await page.goto("https://creator.douyin.com/", timeout=60000)
                print("✅ 访问成功!")
                
                # 检查是否需要登录
                login_button = await page.query_selector('text="登录"')
                if login_button:
                    print("⚠️ 需要登录，Cookie可能已过期")
                    await page.close()
                    return False
                else:
                    print("✅ 已登录状态")
                    await page.close()
                    return True
                
            except Exception as e:
                print(f"⚠️ 访问失败，等待重试... ({attempt}/{max_retries})")
                print(f"错误信息: {e}")
                await asyncio.sleep(5)
        
        await page.close()
        print("❌ 多次尝试后仍然无法访问抖音创作者平台")
        return False
    
    async def upload_video(self, video_file, schedule_time=None):
        """上传视频到抖音"""
        print(f"\n📤 开始上传视频: {os.path.basename(video_file)}")
        
        # 设置浏览器
        playwright, browser, context = await self.setup_browser()
        if not context:
            print("❌ 浏览器设置失败")
            return False
        
        # 测试连接
        connection_ok = await self.test_connection(context)
        if not connection_ok:
            print("❌ 抖音连接测试失败，无法继续上传")
            await browser.close()
            await playwright.stop()
            return False
        
        try:
            # 获取视频标题和标签
            try:
                title, tags = get_title_and_hashtags(video_file)
            except Exception as e:
                print(f"⚠️ 无法读取视频标题和标签: {e}")
                title = os.path.basename(video_file).split('.')[0]
                tags = []
            
            print(f"📝 视频标题: {title}")
            print(f"🏷️ 视频标签: {tags}")
            
            # 设置发布时间
            if schedule_time:
                if isinstance(schedule_time, str):
                    try:
                        schedule_time = datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S")
                        print(f"⏰ 定时发布: {schedule_time.strftime('%Y-%m-%d %H:%M')}")
                    except:
                        print("⚠️ 发布时间格式错误，将立即发布")
                        schedule_time = None
                else:
                    print(f"⏰ 定时发布: {schedule_time.strftime('%Y-%m-%d %H:%M')}")
            else:
                print("📤 立即发布模式")
            
            # 增加重试机制
            max_upload_retries = 3
            for upload_attempt in range(1, max_upload_retries + 1):
                try:
                    print(f"🔄 上传尝试 ({upload_attempt}/{max_upload_retries})...")
                    
                    # 创建抖音视频对象
                    app = DouYinVideo(title, video_file, tags, schedule_time, self.account_file)
                    
                    # 设置地理位置
                    app.default_location = "北京市"
                    
                    # 使用我们的浏览器上下文
                    app.browser = browser
                    app.context = context
                    app.playwright = playwright
                    
                    # 上传视频
                    print("🚀 开始上传过程...")
                    await app.main()
                    
                    print(f"✅ 视频 {os.path.basename(video_file)} 上传成功")
                    return True
                    
                except Exception as e:
                    print(f"⚠️ 上传尝试 {upload_attempt} 失败: {e}")
                    if upload_attempt < max_upload_retries:
                        wait_time = 30  # 等待30秒后重试
                        print(f"等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                        
                        # 重新初始化浏览器
                        await browser.close()
                        await playwright.stop()
                        playwright, browser, context = await self.setup_browser()
                        if not context:
                            print("❌ 浏览器重新初始化失败")
                            return False
                            
                        # 重新测试连接
                        connection_ok = await self.test_connection(context)
                        if not connection_ok:
                            print("❌ 抖音连接测试失败，无法继续上传")
                            return False
                    else:
                        print(f"❌ 达到最大重试次数，上传失败")
                        return False
            
            return False
            
        except Exception as e:
            print(f"❌ 上传失败: {e}")
            return False
        finally:
            # 关闭浏览器
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
    
    async def batch_upload(self, date_str, schedule=False):
        """批量上传指定日期目录下的视频"""
        print(f"🎯 批量上传 {date_str} 目录下的视频")
        
        # 构建视频目录路径
        video_dir = os.path.join(self.base_dir, "videoFile", date_str)
        
        # 检查目录是否存在
        if not os.path.exists(video_dir):
            print(f"❌ 视频目录不存在: {video_dir}")
            return False
        
        # 获取视频文件
        video_extensions = [".mp4", ".webm", ".avi", ".mov", ".mkv", ".flv"]
        video_files = []
        
        for file in os.listdir(video_dir):
            if any(file.lower().endswith(ext) for ext in video_extensions):
                video_files.append(os.path.join(video_dir, file))
        
        if not video_files:
            print(f"❌ 在目录 {video_dir} 中没有找到视频文件")
            return False
        
        print(f"📁 找到 {len(video_files)} 个视频文件:")
        for i, file in enumerate(video_files, 1):
            print(f"  {i}. {os.path.basename(file)}")
        
        # 设置发布时间
        schedule_times = None
        if schedule:
            from utils.files_times import generate_schedule_time_next_day
            schedule_times = generate_schedule_time_next_day(
                len(video_files), 1, daily_times=[16], start_days=0
            )
            print(f"⏰ 定时发布配置:")
            for i, dt in enumerate(schedule_times):
                print(f"  视频{i+1}: {dt.strftime('%Y-%m-%d %H:%M')}")
        
        # 上传视频
        success_count = 0
        for i, file in enumerate(video_files):
            print(f"\n{'='*50}")
            print(f"处理视频 {i+1}/{len(video_files)}: {os.path.basename(file)}")
            print(f"{'='*50}")
            
            current_schedule = schedule_times[i] if schedule and schedule_times else None
            success = await self.upload_video(file, current_schedule)
            
            if success:
                success_count += 1
            
            # 添加间隔，避免频率限制
            if i < len(video_files) - 1:
                wait_time = 10
                print(f"等待 {wait_time} 秒后继续下一个视频...")
                await asyncio.sleep(wait_time)
        
        print(f"\n🎉 批量上传完成: {success_count}/{len(video_files)} 个视频成功")
        return success_count > 0

async def main():
    parser = argparse.ArgumentParser(description="增强版抖音视频上传工具")
    parser.add_argument("--date", type=str, required=True, help="视频所在日期目录，格式：YYYY-MM-DD")
    parser.add_argument("--schedule", action="store_true", help="是否使用定时发布")
    parser.add_argument("--file", type=str, help="单个视频文件路径，如果提供则只上传这一个文件")
    args = parser.parse_args()
    
    uploader = EnhancedDouYinUploader()
    
    if args.file:
        if os.path.exists(args.file):
            await uploader.upload_video(args.file, None)
        else:
            print(f"❌ 视频文件不存在: {args.file}")
    else:
        await uploader.batch_upload(args.date, args.schedule)

if __name__ == "__main__":
    asyncio.run(main()) 