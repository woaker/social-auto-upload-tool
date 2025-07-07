#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频上传工具 - 带进度显示
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from uploader.douyin_uploader.main import DouYinVideo
from utils.log import douyin_logger

class ProgressUploader:
    def __init__(self, video_file, title, tags, account_file):
        self.video_file = video_file
        self.title = title
        self.tags = tags
        self.account_file = account_file
        self.current_step = 0
        self.total_steps = 8
        
        self.steps = [
            "🚀 初始化浏览器",
            "🌐 访问抖音创作者中心", 
            "📁 选择视频文件",
            "⬆️  开始上传视频",
            "⏳ 等待视频处理",
            "✏️  填写视频信息",
            "🎯 设置发布选项",
            "✅ 确认发布"
        ]
    
    def print_progress(self, step_name, status="进行中"):
        """打印进度信息"""
        self.current_step += 1
        progress_bar = "█" * self.current_step + "░" * (self.total_steps - self.current_step)
        percentage = (self.current_step / self.total_steps) * 100
        
        print(f"\r[{progress_bar}] {percentage:.1f}% - {step_name} ({status})", end="")
        sys.stdout.flush()
        
        if status in ["完成", "成功"]:
            print()  # 换行
    
    def print_step(self, step_name):
        """打印当前步骤"""
        print(f"\n{self.steps[self.current_step]}: {step_name}")
        self.print_progress(step_name, "进行中")
    
    async def upload_with_progress(self):
        """带进度显示的上传"""
        print("=" * 60)
        print(f"🎬 开始上传视频: {Path(self.video_file).name}")
        print(f"📝 标题: {self.title}")
        print(f"🏷️  标签: {', '.join(self.tags)}")
        print("=" * 60)
        
        try:
            # 步骤1: 初始化
            self.print_step("启动浏览器环境")
            await asyncio.sleep(2)  # 模拟启动时间
            
            # 步骤2: 访问页面  
            self.print_step("连接抖音创作者中心")
            
            # 创建上传实例
            app = DouYinVideo(
                title=self.title,
                file_path=self.video_file,
                tags=self.tags,
                publish_date=datetime.now(),
                account_file=self.account_file
            )
            
            # 步骤3-8: 实际上传过程
            print(f"\n{self.steps[2]}: 选择视频文件")
            self.current_step = 2
            self.print_progress("选择视频文件", "完成")
            
            print(f"\n{self.steps[3]}: 开始上传")
            self.current_step = 3
            self.print_progress("开始上传", "进行中")
            
            # 监控上传过程
            upload_task = asyncio.create_task(app.main())
            
            # 模拟进度更新
            for i in range(4, 8):
                await asyncio.sleep(10)  # 每10秒更新一次
                if not upload_task.done():
                    print(f"\n{self.steps[i]}: 正在处理...")
                    self.current_step = i
                    self.print_progress(self.steps[i], "进行中")
                else:
                    break
            
            # 等待上传完成
            await upload_task
            
            # 完成
            self.current_step = self.total_steps
            self.print_progress("上传完成", "成功")
            print("\n🎉 视频上传成功!")
            return True
            
        except Exception as e:
            print(f"\n❌ 上传失败: {e}")
            return False

async def main():
    """主函数"""
    # 配置信息
    video_dir = Path("./videoFile/2025-07-03")
    account_file = "cookiesFile/douyin_account.json"
    
    # 查找视频文件
    video_files = list(video_dir.glob("*.mp4"))
    if not video_files:
        print(f"❌ 在 {video_dir} 中未找到视频文件")
        return
    
    video_file = video_files[0]
    print(f"📁 找到视频文件: {video_file.name}")
    
    # 生成标题和标签
    title = video_file.stem[:30]  # 使用文件名作为标题
    tags = ["AI", "n8n", "自动化", "工作流"]
    
    # 开始上传
    uploader = ProgressUploader(
        video_file=str(video_file),
        title=title,
        tags=tags,
        account_file=account_file
    )
    
    success = await uploader.upload_with_progress()
    
    if success:
        print("\n✅ 所有任务完成!")
    else:
        print("\n❌ 上传任务失败!")

if __name__ == "__main__":
    asyncio.run(main()) 