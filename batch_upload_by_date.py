#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按日期目录批量上传视频脚本
支持多个平台：抖音、快手、小红书、视频号

使用方法：
python batch_upload_by_date.py --platform douyin --date 2025-01-11
python batch_upload_by_date.py --platform bilibili --date 2025-01-11
python batch_upload_by_date.py --platform all --date 2025-01-11
"""

import argparse
import asyncio
import time
from pathlib import Path
from datetime import datetime
import os
import sys
import json
from playwright.sync_api import sync_playwright

# 添加当前目录到Python路径，确保可以导入本地的conf模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BASE_DIR
from utils.files_times import get_title_and_hashtags, generate_schedule_time_next_day

# 导入各平台的上传模块
from uploader.douyin_uploader.main import douyin_setup, DouYinVideo, upload_to_douyin
from uploader.bilibili_uploader.main import read_cookie_json_file, extract_keys_from_json, random_emoji, BilibiliUploader
from utils.video_converter import VideoConverter
from uploader.ks_uploader.main import KSVideo, ks_setup
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo, xiaohongshu_setup
from uploader.tk_uploader.main import TiktokVideo, tiktok_setup
from uploader.baijiahao_uploader.main import BaiJiaHaoVideo, baijiahao_setup
from uploader.tencent_uploader.main import TencentVideo, weixin_setup
from utils.constant import VideoZoneTypes


class BatchUploader:
    def __init__(self, date_str: str, videos_per_day: int = 1, daily_times: list = None, start_days: int = 0, enable_schedule: bool = True):
        self.date_str = date_str
        self.base_dir = Path(BASE_DIR)
        self.video_dir = self.base_dir / "videoFile" / date_str
        self.cookies_dir = self.base_dir / "cookiesFile"
        
        # 定时发布配置
        self.enable_schedule = enable_schedule
        self.videos_per_day = videos_per_day
        self.daily_times = daily_times if daily_times else [16]  # 默认下午4点
        self.start_days = start_days
        
        # 支持的平台配置
        self.platforms = {
            'douyin': {
                'name': '抖音',
                'domains': ['douyin.com', 'creator.douyin.com'],
                'account_file': None,  # 动态设置
                'upload_func': self.upload_to_douyin
            },
            'bilibili': {
                'name': 'B站',
                'domains': ['bilibili.com'],
                'account_file': None,
                'upload_func': self.upload_to_bilibili
            },
            'kuaishou': {
                'name': '快手',
                'domains': ['kuaishou.com'],
                'account_file': None,
                'upload_func': self.upload_to_kuaishou
            },
            'xiaohongshu': {
                'name': '小红书',
                'domains': ['xiaohongshu.com'],
                'account_file': None,
                'upload_func': self.upload_to_xiaohongshu
            },
            # 'tiktok': {
            #     'name': 'TikTok',
            #     'domains': ['tiktok.com'],
            #     'account_file': None,
            #     'upload_func': self.upload_to_tiktok
            # },
            'baijiahao': {
                'name': '百家号',
                'domains': ['baijiahao.baidu.com', 'baidu.com'],
                'account_file': None,
                'upload_func': self.upload_to_baijiahao
            }
            # 'tencent': {
            #     'name': '视频号',
            #     'domains': ['weixin.qq.com', 'channels.weixin.qq.com'],
            #     'account_file': None,
            #     'upload_func': self.upload_to_tencent
            # }
        }
        
        # 动态查找每个平台的账号文件
        self._match_account_files()
    
    def _match_account_files(self):
        """动态匹配每个平台的账号文件"""
        # 首先检查新的cookie目录结构
        cookies_base = self.base_dir / "cookies"
        
        # 平台特定的cookie文件路径
        platform_paths = {
            'douyin': self.cookies_dir / "douyin_account.json",
            'bilibili': self.cookies_dir / "32b2189f-8ea6-41b8-b48d-395894ae01ed.json",
            'kuaishou': self.cookies_dir / "a7b72f5a-4689-11f0-87bd-82265ec8d59d.json",
            'xiaohongshu': self.cookies_dir / "ebd39c7e-4688-11f0-87bd-82265ec8d59d.json",
            'baijiahao': self.cookies_dir / "ee7a766a-d8b1-4d48-a9d9-4ce6e154ad8a.json"
        }
        
        for platform, config in self.platforms.items():
            # 检查新路径
            if platform in platform_paths:
                new_path = platform_paths[platform]
                if new_path.exists():
                    config['account_file'] = new_path
                    print(f"✅ {config['name']} 匹配到账号文件: {new_path}")
                    continue
            
            # 如果新路径不存在，尝试在旧目录中查找
            matched_file = None
            
            # 检查特定的文件名
            if platform == 'douyin':
                douyin_account = self.cookies_dir / "douyin_account.json"
                if douyin_account.exists():
                    matched_file = douyin_account
            
            # 如果没有找到特定文件，尝试在旧目录中查找
            if not matched_file:
                json_files = list(self.cookies_dir.glob("*.json"))
                
                for json_file in json_files:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # 检查cookies中的domain是否匹配
                        if 'cookies' in data:
                            for cookie in data['cookies']:
                                domain = cookie.get('domain', '').lstrip('.')
                                for platform_domain in config['domains']:
                                    if platform_domain in domain:
                                        matched_file = json_file
                                        break
                                if matched_file:
                                    break
                        
                        if matched_file:
                            break
                            
                    except Exception as e:
                        print(f"⚠️  读取文件 {json_file} 失败: {e}")
                        continue
            
            if matched_file:
                config['account_file'] = matched_file
                print(f"✅ {config['name']} 匹配到账号文件: {matched_file.name}")
            else:
                print(f"❌ {config['name']} 未找到账号文件")

    def check_date_directory(self):
        """检查日期目录是否存在"""
        if not self.video_dir.exists():
            print(f"❌ 日期目录不存在: {self.video_dir}")
            print(f"请先创建目录并放入视频文件: {self.video_dir}")
            return False
        return True
    
    def get_video_files(self):
        """获取指定日期目录下的所有视频文件，支持多种格式"""
        # 支持的视频格式
        video_extensions = ["*.mp4", "*.webm", "*.avi", "*.mov", "*.mkv", "*.flv"]
        video_files = []
        
        # 收集所有支持格式的视频文件
        for ext in video_extensions:
            video_files.extend(list(self.video_dir.glob(ext)))
        
        if not video_files:
            print(f"❌ 在目录 {self.video_dir} 中没有找到视频文件")
            return []
        
        print(f"📁 找到 {len(video_files)} 个视频文件:")
        for i, file in enumerate(video_files, 1):
            print(f"  {i}. {file.name}")
        
        return video_files
    
    def check_platform_account(self, platform):
        """检查平台账号配置文件是否存在"""
        account_file = self.platforms[platform]['account_file']
        if not account_file or not account_file.exists():
            print(f"❌ {self.platforms[platform]['name']} 账号配置文件不存在")
            print(f"请先运行对应的获取cookie脚本")
            return False
        return True
    
    def get_video_info(self, video_file):
        """获取视频标题和标签信息"""
        try:
            title, tags = get_title_and_hashtags(str(video_file))
            return title, tags
        except Exception as e:
            print(f"⚠️  无法读取视频 {video_file.name} 的txt文件，使用默认标题")
            # 使用文件名作为默认标题
            title = video_file.stem
            tags = []
            return title, tags
    
    def get_publish_schedule(self, file_num):
        """获取发布时间安排"""
        if self.enable_schedule:
            # 将时间字符串转换为小时数
            daily_hours = []
            for time_str in self.daily_times:
                if ':' in time_str:
                    # 解析"HH:MM"格式
                    hour, minute = time_str.split(':')
                    daily_hours.append(int(hour))
                else:
                    # 兼容原来的小时数字格式
                    daily_hours.append(int(time_str))
            
            publish_datetimes = generate_schedule_time_next_day(
                file_num, 
                self.videos_per_day, 
                daily_hours, 
                start_days=self.start_days
            )
            print(f"⏰ 定时发布配置:")
            print(f"   每天发布数量: {self.videos_per_day}")
            print(f"   发布时间点: {self.daily_times}")
            print(f"   开始天数: {self.start_days} ({'明天' if self.start_days == 0 else '后天' if self.start_days == 1 else f'{self.start_days+1}天后'})")
            print(f"   发布时间安排:")
            for i, dt in enumerate(publish_datetimes):
                print(f"     视频{i+1}: {dt.strftime('%Y-%m-%d %H:%M')}")
        else:
            publish_datetimes = [0 for _ in range(file_num)]
            print(f"📤 立即发布模式")
        
        return publish_datetimes
    
    async def upload_to_douyin(self, video_files):
        """上传到抖音"""
        print(f"🎵 开始上传到抖音...")
        account_file = self.platforms['douyin']['account_file']
        
        file_num = len(video_files)
        publish_datetimes = self.get_publish_schedule(file_num)
        
        try:
            cookie_setup = await douyin_setup(account_file, handle=True)
            if not cookie_setup:
                print(f"❌ 抖音登录失败")
                return
        except Exception as e:
            print(f"❌ 抖音登录失败: {e}")
            return
        
        for index, file in enumerate(video_files):
            try:
                title, tags = self.get_video_info(file)
                print(f"📤 正在上传: {file.name}")
                print(f"   标题: {title}")
                print(f"   标签: {tags}")
                print(f"   地理位置: 北京市")
                if self.enable_schedule:
                    print(f"   发布时间: {publish_datetimes[index].strftime('%Y-%m-%d %H:%M')}")
                else:
                    print(f"   发布方式: 立即发布")
                
                app = DouYinVideo(title, file, tags, publish_datetimes[index], account_file)
                # 设置固定地理位置
                app.default_location = "北京市"
                await app.main()
                
                print(f"✅ {file.name} 上传成功")
                time.sleep(5)  # 防止频率过快
                
            except Exception as e:
                print(f"❌ {file.name} 上传失败: {e}")
    
    async def upload_to_bilibili(self, video_files):
        """上传到B站"""
        print(f"📺 开始上传到B站...")
        account_file = self.platforms['bilibili']['account_file']
        
        try:
            cookie_data = read_cookie_json_file(account_file)
            cookie_data = extract_keys_from_json(cookie_data)
        except Exception as e:
            print(f"❌ B站登录失败: {e}")
            return
        
        tid = VideoZoneTypes.MUSIC_OTHER.value  # 设置分区id为音乐综合
        file_num = len(video_files)
        
        if self.enable_schedule:
            timestamps = generate_schedule_time_next_day(file_num, self.videos_per_day, daily_times=self.daily_times, timestamps=True, start_days=self.start_days)
        else:
            timestamps = [0] * file_num  # 立即发布
        
        for index, file in enumerate(video_files):
            try:
                title, tags = self.get_video_info(file)
                # 清理标题中的特殊字符，避免B站审核问题
                title = title.replace(" - ", " ").replace("(", "").replace(")", "")
                title += random_emoji()  # B站不允许相同标题
                tags_str = ','.join([tag for tag in tags])
                
                print(f"📤 正在上传: {file.name}")
                print(f"   标题: {title}")
                print(f"   标签: {tags}")
                if self.enable_schedule:
                    print(f"   发布时间: {timestamps[index] if timestamps[index] != 0 else '立即发布'}")
                else:
                    print(f"   发布方式: 立即发布")
                
                # B站视频格式检查和转换
                converter = VideoConverter()
                supported_formats = ['.mp4', '.avi', '.mov', '.flv']
                
                current_file = file
                if file.suffix.lower() not in supported_formats:
                    print(f"⚠️  B站不支持 {file.suffix} 格式，正在转换为mp4...")
                    converted_file = converter.convert_to_mp4(str(file))
                    if converted_file:
                        current_file = Path(converted_file)
                        print(f"✅ 视频转换成功: {current_file.name}")
                    else:
                        print(f"❌ 视频转换失败，跳过文件: {file.name}")
                        continue
                
                desc = title
                bili_uploader = BilibiliUploader(cookie_data, current_file, title, desc, tid, tags, timestamps[index])
                await asyncio.get_event_loop().run_in_executor(None, bili_uploader.upload)
                
                # 如果转换了文件，上传完成后清理临时文件
                if current_file != file:
                    converter.cleanup_temp_file(str(current_file))
                
                print(f"✅ {file.name} 上传成功")
                time.sleep(30)  # B站需要较长间隔
                
            except Exception as e:
                print(f"❌ {file.name} 上传失败: {e}")
    
    async def upload_to_kuaishou(self, video_files):
        """上传到快手"""
        print(f"🎬 开始上传到快手...")
        account_file = self.platforms['kuaishou']['account_file']
        
        file_num = len(video_files)
        publish_datetimes = self.get_publish_schedule(file_num)
        
        try:
            cookie_setup = await ks_setup(account_file, handle=False)
        except Exception as e:
            print(f"❌ 快手登录失败: {e}")
            return
        
        for index, file in enumerate(video_files):
            try:
                title, tags = self.get_video_info(file)
                print(f"📤 正在上传: {file.name}")
                print(f"   标题: {title}")
                print(f"   标签: {tags}")
                if self.enable_schedule:
                    print(f"   发布时间: {publish_datetimes[index].strftime('%Y-%m-%d %H:%M')}")
                else:
                    print(f"   发布方式: 立即发布")
                
                app = KSVideo(title, file, tags, publish_datetimes[index], account_file)
                await app.main()
                
                print(f"✅ {file.name} 上传成功")
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ {file.name} 上传失败: {e}")
    
    async def upload_to_xiaohongshu(self, video_files):
        """上传到小红书"""
        print(f"📖 开始上传到小红书...")
        account_file = self.platforms['xiaohongshu']['account_file']
        
        file_num = len(video_files)
        publish_datetimes = self.get_publish_schedule(file_num)
        
        try:
            cookie_setup = await xiaohongshu_setup(account_file, handle=False)
        except Exception as e:
            print(f"❌ 小红书登录失败: {e}")
            return
        
        for index, file in enumerate(video_files):
            try:
                title, tags = self.get_video_info(file)
                print(f"📤 正在上传: {file.name}")
                print(f"   标题: {title}")
                print(f"   标签: {tags}")
                if self.enable_schedule:
                    print(f"   发布时间: {publish_datetimes[index].strftime('%Y-%m-%d %H:%M')}")
                else:
                    print(f"   发布方式: 立即发布")
                
                app = XiaoHongShuVideo(title, file, tags, publish_datetimes[index], account_file, location="北京市")
                await app.main()
                
                print(f"✅ {file.name} 上传成功")
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ {file.name} 上传失败: {e}")
    
    async def upload_to_tiktok(self, video_files):
        """上传到TikTok"""
        print(f"🎵 开始上传到TikTok...")
        account_file = self.platforms['tiktok']['account_file']
        
        file_num = len(video_files)
        publish_datetimes = generate_schedule_time_next_day(file_num, 1, daily_times=[16])
        
        try:
            cookie_setup = await tiktok_setup(account_file, handle=False)
        except Exception as e:
            print(f"❌ TikTok登录失败: {e}")
            return
        
        for index, file in enumerate(video_files):
            try:
                title, tags = self.get_video_info(file)
                print(f"📤 正在上传: {file.name}")
                print(f"   标题: {title}")
                print(f"   标签: {tags}")
                
                app = TiktokVideo(title, file, tags, publish_datetimes[index], account_file)
                await app.main()
                
                print(f"✅ {file.name} 上传成功")
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ {file.name} 上传失败: {e}")
    
    async def upload_to_baijiahao(self, video_files):
        """上传到百家号"""
        print(f"📰 开始上传到百家号...")
        account_file = self.platforms['baijiahao']['account_file']
        
        file_num = len(video_files)
        publish_datetimes = self.get_publish_schedule(file_num)
        
        try:
            cookie_setup = await baijiahao_setup(account_file, handle=False)
        except Exception as e:
            print(f"❌ 百家号登录失败: {e}")
            return
        
        for index, file in enumerate(video_files):
            try:
                title, tags = self.get_video_info(file)
                print(f"📤 正在上传: {file.name}")
                print(f"   标题: {title}")
                print(f"   标签: {tags}")
                if self.enable_schedule:
                    print(f"   发布时间: {publish_datetimes[index].strftime('%Y-%m-%d %H:%M')}")
                else:
                    print(f"   发布方式: 立即发布")
                
                app = BaiJiaHaoVideo(title, file, tags, publish_datetimes[index], account_file)
                await app.main()
                
                print(f"✅ {file.name} 上传成功")
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ {file.name} 上传失败: {e}")
    
    async def upload_to_tencent(self, video_files):
        """上传到视频号"""
        print(f"🎬 开始上传到视频号...")
        account_file = self.platforms['tencent']['account_file']
        
        file_num = len(video_files)
        publish_datetimes = self.get_publish_schedule(file_num)
        
        try:
            cookie_setup = await weixin_setup(account_file, handle=False)
        except Exception as e:
            print(f"❌ 视频号登录失败: {e}")
            return
        
        for index, file in enumerate(video_files):
            try:
                title, tags = self.get_video_info(file)
                print(f"📤 正在上传: {file.name}")
                print(f"   标题: {title}")
                print(f"   标签: {tags}")
                if self.enable_schedule:
                    print(f"   发布时间: {publish_datetimes[index].strftime('%Y-%m-%d %H:%M')}")
                else:
                    print(f"   发布方式: 立即发布")
                
                app = TencentVideo(title, file, tags, publish_datetimes[index], account_file)
                await app.main()
                
                print(f"✅ {file.name} 上传成功")
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ {file.name} 上传失败: {e}")
    
    async def upload_to_platform(self, platform, video_files):
        """上传到指定平台"""
        if platform not in self.platforms:
            print(f"❌ 不支持的平台: {platform}")
            return
        
        if not self.check_platform_account(platform):
            return
        
        upload_func = self.platforms[platform]['upload_func']
        if asyncio.iscoroutinefunction(upload_func):
            await upload_func(video_files)
        else:
            upload_func(video_files)
    
    async def upload_to_all_platforms(self, video_files):
        """上传到所有平台"""
        print("🚀 开始上传到所有平台...")
        
        for platform in self.platforms.keys():
            if self.check_platform_account(platform):
                print(f"\n{'='*50}")
                print(f"开始上传到 {self.platforms[platform]['name']}")
                print(f"{'='*50}")
                await self.upload_to_platform(platform, video_files)
                print(f"\n{self.platforms[platform]['name']} 上传完成")
                time.sleep(10)  # 平台间间隔
    
    def create_date_directory(self):
        """创建日期目录"""
        self.video_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 已创建日期目录: {self.video_dir}")
    
    async def run(self, platform='all'):
        """主运行函数"""
        print(f"🎯 批量上传脚本启动")
        print(f"📅 目标日期: {self.date_str}")
        print(f"🎯 目标平台: {platform}")
        print(f"📁 视频目录: {self.video_dir}")
        
        # 显示定时发布配置
        if self.enable_schedule:
            print(f"⏰ 定时发布: 启用")
            print(f"   每天发布: {self.videos_per_day} 个视频")
            print(f"   发布时间: {self.daily_times}")
            print(f"   开始天数: {self.start_days}")
        else:
            print(f"📤 发布方式: 立即发布")
        
        # 检查日期目录
        if not self.check_date_directory():
            print("是否要创建日期目录？(y/n): ", end="")
            if input().lower() == 'y':
                self.create_date_directory()
                print("请将视频文件放入目录后重新运行脚本")
            return
        
        # 获取视频文件
        video_files = self.get_video_files()
        if not video_files:
            return
        
        # 开始上传
        print(f"\n{'='*50}")
        print(f"开始批量上传 {len(video_files)} 个视频")
        print(f"{'='*50}")
        
        if platform == 'all':
            await self.upload_to_all_platforms(video_files)
        else:
            await self.upload_to_platform(platform, video_files)
        
        print(f"\n🎉 批量上传完成！")


def upload_douyin_videos(video_files, schedule_time=None):
    print("🎵 开始上传到抖音...")
    if schedule_time:
        print(f"⏰ 定时发布: {schedule_time}")
    else:
        print("📤 立即发布模式")

    success_count = 0
    for video_file in video_files:
        if upload_to_douyin(video_file):
            success_count += 1

    print(f"\n✅ 上传完成: {success_count}/{len(video_files)} 个视频成功")
    return success_count > 0

def check_account_files():
    """检查账号配置文件是否存在"""
    account_files = {
        'douyin': 'douyin_account.json',
        'bilibili': '32b2189f-8ea6-41b8-b48d-395894ae01ed.json',
        'kuaishou': 'a7b72f5a-4689-11f0-87bd-82265ec8d59d.json',
        'xiaohongshu': 'ebd39c7e-4688-11f0-87bd-82265ec8d59d.json',
        'baijiahao': 'ee7a766a-d8b1-4d48-a9d9-4ce6e154ad8a.json'
    }
    
    for platform, file in account_files.items():
        if os.path.exists(file):
            print(f"✅ {platform.title()} 匹配到账号文件: {file}")
        else:
            print(f"❌ {platform.title()} 未找到账号文件: {file}")

def main():
    parser = argparse.ArgumentParser(description='批量上传视频到各个平台')
    parser.add_argument('--platform', type=str, required=True, help='目标平台 (douyin/bilibili/kuaishou/xiaohongshu/baijiahao)')
    parser.add_argument('--date', type=str, required=True, help='视频所在日期目录，格式：YYYY-MM-DD')
    parser.add_argument('--no-schedule', action='store_true', help='是否立即发布，默认为定时发布')
    args = parser.parse_args()

    # 验证日期格式
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("❌ 日期格式错误，请使用YYYY-MM-DD格式")
        return

    # 设置发布时间
    schedule_time = None if args.no_schedule else f"{args.date} 12:00:00"

    print("🎯 批量上传配置:")
    print(f"   平台: {args.platform}")
    print(f"   日期: {args.date}")
    print(f"   发布方式: {'立即发布' if args.no_schedule else '定时发布'}")
    print()

    # 检查账号配置
    check_account_files()

    # 获取视频文件列表
    video_dir = os.path.join("videoFile", args.date)
    if not os.path.exists(video_dir):
        print(f"❌ 视频目录不存在: {video_dir}")
        return

    video_files = []
    for file in os.listdir(video_dir):
        if file.endswith(('.mp4', '.MP4', '.mov', '.MOV')):
            video_files.append(os.path.join(video_dir, file))

    if not video_files:
        print(f"❌ 未找到视频文件")
        return

    print("🎯 批量上传脚本启动")
    print(f"📅 目标日期: {args.date}")
    print(f"🎯 目标平台: {args.platform}")
    print(f"📁 视频目录: {os.path.abspath(video_dir)}")
    print(f"📤 发布方式: {'立即发布' if args.no_schedule else '定时发布'}")
    print(f"📁 找到 {len(video_files)} 个视频文件:")
    for i, file in enumerate(video_files, 1):
        print(f"  {i}. {os.path.basename(file)}")
    print()

    print("=" * 50)
    print(f"开始批量上传 {len(video_files)} 个视频")
    print("=" * 50)

    # 根据平台调用不同的上传函数
    if args.platform == 'douyin':
        upload_douyin_videos(video_files, schedule_time)
    else:
        print(f"❌ 不支持的平台: {args.platform}")

    print("\n🎉 批量上传完成！")


if __name__ == '__main__':
    main() 