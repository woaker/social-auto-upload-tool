#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速上传脚本 - 简化版本
按日期目录批量上传视频到指定平台

使用示例：
python quick_upload.py                          # 上传今天目录下的视频到抖音
python quick_upload.py douyin                   # 上传今天目录下的视频到抖音
python quick_upload.py bilibili 2025-01-11     # 上传指定日期目录下的视频到B站
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime

from conf import BASE_DIR
from utils.files_times import get_title_and_hashtags, generate_schedule_time_next_day

# 导入平台上传模块
from uploader.douyin_uploader.main import douyin_setup, DouYinVideo
from uploader.bilibili_uploader.main import read_cookie_json_file, extract_keys_from_json, random_emoji, BilibiliUploader
from utils.constant import VideoZoneTypes


class QuickUploader:
    def __init__(self, platform='douyin', date_str=None):
        self.platform = platform
        self.date_str = date_str or datetime.now().strftime('%Y-%m-%d')
        self.base_dir = Path(BASE_DIR)
        self.video_dir = self.base_dir / "videoFile" / self.date_str
        self.cookies_dir = self.base_dir / "cookies"
        
        print(f"🎯 平台: {platform}")
        print(f"📅 日期: {self.date_str}")
        print(f"📁 视频目录: {self.video_dir}")
    
    def check_and_create_directory(self):
        """检查并创建日期目录"""
        if not self.video_dir.exists():
            print(f"📁 创建日期目录: {self.video_dir}")
            self.video_dir.mkdir(parents=True, exist_ok=True)
            return False  # 新创建的目录，没有视频文件
        return True
    
    def get_video_files(self):
        """获取视频文件"""
        video_files = list(self.video_dir.glob("*.mp4"))
        if not video_files:
            print(f"❌ 目录 {self.video_dir} 中没有找到视频文件")
            print("请将视频文件(.mp4)放入此目录")
            return []
        
        print(f"📁 找到 {len(video_files)} 个视频文件:")
        for i, file in enumerate(video_files, 1):
            print(f"  {i}. {file.name}")
        
        return video_files
    
    def get_video_info(self, video_file):
        """获取视频信息"""
        try:
            title, tags = get_title_and_hashtags(str(video_file))
            return title, tags
        except Exception:
            # 如果没有txt文件，使用文件名作为标题
            title = video_file.stem.replace('_', ' ')
            tags = ['生活', '分享']  # 默认标签
            
            # 创建默认的txt文件
            txt_file = video_file.with_suffix('.txt')
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(f"{title}\n")
                f.write("#生活 #分享")
            
            print(f"📝 为 {video_file.name} 创建了默认标题文件")
            return title, tags
    
    async def upload_to_douyin(self, video_files):
        """上传到抖音"""
        account_file = self.cookies_dir / "douyin_uploader" / "account.json"
        
        if not account_file.exists():
            print(f"❌ 抖音账号配置文件不存在: {account_file}")
            print("请先运行: python examples/get_douyin_cookie.py")
            return
        
        print(f"🎵 开始上传到抖音...")
        
        file_num = len(video_files)
        publish_datetimes = generate_schedule_time_next_day(file_num, 1, daily_times=[16])
        
        try:
            cookie_setup = await douyin_setup(account_file, handle=False)
            print("✅ 抖音登录成功")
        except Exception as e:
            print(f"❌ 抖音登录失败: {e}")
            return
        
        for index, file in enumerate(video_files):
            try:
                title, tags = self.get_video_info(file)
                print(f"\n📤 正在上传: {file.name}")
                print(f"   标题: {title}")
                print(f"   标签: {tags}")
                
                app = DouYinVideo(title, file, tags, publish_datetimes[index], account_file)
                await app.main()
                
                print(f"✅ {file.name} 上传成功")
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ {file.name} 上传失败: {e}")
    
    def upload_to_bilibili(self, video_files):
        """上传到B站"""
        account_file = self.cookies_dir / "bilibili_uploader" / "account.json"
        
        if not account_file.exists():
            print(f"❌ B站账号配置文件不存在: {account_file}")
            print("请先运行获取B站cookie的脚本")
            return
        
        print(f"📺 开始上传到B站...")
        
        try:
            cookie_data = read_cookie_json_file(account_file)
            cookie_data = extract_keys_from_json(cookie_data)
            print("✅ B站登录成功")
        except Exception as e:
            print(f"❌ B站登录失败: {e}")
            return
        
        tid = VideoZoneTypes.SPORTS_FOOTBALL.value
        file_num = len(video_files)
        timestamps = generate_schedule_time_next_day(file_num, 1, daily_times=[16], timestamps=True)
        
        for index, file in enumerate(video_files):
            try:
                title, tags = self.get_video_info(file)
                title += random_emoji()  # B站不允许重复标题
                
                print(f"\n📤 正在上传: {file.name}")
                print(f"   标题: {title}")
                print(f"   标签: {tags}")
                
                desc = title
                bili_uploader = BilibiliUploader(cookie_data, file, title, desc, tid, tags, timestamps[index])
                bili_uploader.upload()
                
                print(f"✅ {file.name} 上传成功")
                time.sleep(30)
                
            except Exception as e:
                print(f"❌ {file.name} 上传失败: {e}")
    
    async def run(self):
        """主运行函数"""
        print(f"🚀 快速上传脚本启动")
        print(f"="*50)
        
        # 检查并创建目录
        if not self.check_and_create_directory():
            print("请将视频文件放入目录后重新运行脚本")
            return
        
        # 获取视频文件
        video_files = self.get_video_files()
        if not video_files:
            return
        
        # 确认上传
        print(f"\n准备上传 {len(video_files)} 个视频到 {self.platform}")
        print("是否继续？(y/n): ", end="")
        if input().lower() != 'y':
            print("已取消上传")
            return
        
        # 开始上传
        print(f"\n{'='*50}")
        if self.platform == 'douyin':
            await self.upload_to_douyin(video_files)
        elif self.platform == 'bilibili':
            self.upload_to_bilibili(video_files)
        else:
            print(f"❌ 暂不支持平台: {self.platform}")
            return
        
        print(f"\n🎉 上传完成！")


def show_usage():
    """显示使用说明"""
    print("""
🎯 快速上传脚本使用说明

支持平台：
  douyin    - 抖音 (默认)
  bilibili  - B站

使用方法：
  python quick_upload.py                        # 上传今天目录的视频到抖音
  python quick_upload.py douyin                 # 上传今天目录的视频到抖音
  python quick_upload.py bilibili              # 上传今天目录的视频到B站
  python quick_upload.py douyin 2025-01-11     # 上传指定日期目录的视频到抖音

目录结构：
  videoFile/
  ├── 2025-01-11/
  │   ├── video1.mp4
  │   ├── video1.txt      # 标题和标签文件
  │   ├── video2.mp4
  │   └── video2.txt
  └── 2025-01-12/
      └── ...

标题文件格式 (video.txt)：
  第一行：视频标题
  第二行：标签 (用#分隔，如: #生活 #分享 #有趣)
""")


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_usage()
        return
    
    # 解析参数
    platform = 'douyin'  # 默认平台
    date_str = None
    
    if len(sys.argv) > 1:
        platform = sys.argv[1]
    
    if len(sys.argv) > 2:
        date_str = sys.argv[2]
    
    # 验证平台
    supported_platforms = ['douyin', 'bilibili']
    if platform not in supported_platforms:
        print(f"❌ 不支持的平台: {platform}")
        print(f"支持的平台: {', '.join(supported_platforms)}")
        return
    
    # 验证日期格式
    if date_str and not date_str.count('-') == 2:
        print(f"❌ 日期格式错误: {date_str}")
        print("正确格式: YYYY-MM-DD (如: 2025-01-11)")
        return
    
    # 创建上传器并运行
    uploader = QuickUploader(platform, date_str)
    asyncio.run(uploader.run())


if __name__ == '__main__':
    main() 