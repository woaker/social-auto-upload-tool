#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
今日视频目录设置脚本
自动创建今天的日期目录，并提供使用示例
"""

import os
from pathlib import Path
from datetime import datetime

from conf import BASE_DIR


def setup_today_directory():
    """设置今天的视频目录"""
    today = datetime.now().strftime('%Y-%m-%d')
    base_dir = Path(BASE_DIR)
    
    # 创建今天的视频目录
    today_dir = base_dir / "videoFile" / today
    today_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 已创建今天的视频目录: {today_dir}")
    
    # 检查是否有视频文件
    video_files = list(today_dir.glob("*.mp4"))
    if video_files:
        print(f"✅ 找到 {len(video_files)} 个视频文件:")
        for i, file in enumerate(video_files, 1):
            print(f"   {i}. {file.name}")
    else:
        print("📝 目录为空，请按以下步骤操作:")
        print(f"   1. 将视频文件(.mp4)复制到: {today_dir}")
        print(f"   2. 为每个视频创建对应的标题文件(.txt)")
        print()
        
        # 创建示例文件
        create_example_files(today_dir)
    
    return today_dir, today


def create_example_files(directory):
    """创建示例文件"""
    print("📝 创建示例文件说明:")
    
    # 示例视频文件名
    example_video = "我的生活日常.mp4"
    example_txt = "我的生活日常.txt"
    
    print(f"   示例视频: {example_video}")
    print(f"   示例标题文件: {example_txt}")
    print()
    
    # 创建示例txt文件
    txt_path = directory / example_txt
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("我的生活日常分享\n")
        f.write("#生活 #日常 #分享 #vlog")
    
    print(f"✅ 已创建示例标题文件: {txt_path}")
    print("   内容:")
    print("   第一行: 我的生活日常分享")
    print("   第二行: #生活 #日常 #分享 #vlog")
    print()


def show_upload_commands(date_str):
    """显示上传命令"""
    print("🚀 视频上传命令:")
    print(f"   上传到抖音:     python quick_upload.py douyin {date_str}")
    print(f"   上传到B站:      python quick_upload.py bilibili {date_str}")
    print(f"   上传到所有平台: python batch_upload_by_date.py --platform all --date {date_str}")
    print()
    
    print("💡 如果是今天的日期，可以省略日期参数:")
    print("   python quick_upload.py douyin")
    print("   python quick_upload.py bilibili")
    print()


def check_cookie_files():
    """检查cookie文件是否存在"""
    print("🍪 检查账号配置文件:")
    base_dir = Path(BASE_DIR)
    cookies_dir = base_dir / "cookies"
    
    platforms = {
        'douyin_uploader': '抖音',
        'bilibili_uploader': 'B站',
        'ks_uploader': '快手',
        'xiaohongshu_uploader': '小红书',
        'tk_uploader': 'TikTok',
        'baijiahao_uploader': '百家号',
        'tencent_uploader': '视频号'
    }
    
    missing_cookies = []
    
    for platform_dir, platform_name in platforms.items():
        cookie_file = cookies_dir / platform_dir / "account.json"
        if cookie_file.exists():
            print(f"   ✅ {platform_name}: {cookie_file}")
        else:
            print(f"   ❌ {platform_name}: 配置文件不存在")
            missing_cookies.append((platform_dir, platform_name))
    
    if missing_cookies:
        print()
        print("⚠️  需要先获取以下平台的登录信息:")
        for platform_dir, platform_name in missing_cookies:
            print(f"   {platform_name}: python examples/get_{platform_dir.replace('_uploader', '')}_cookie.py")
    
    print()


def main():
    print("🎯 今日视频目录设置脚本")
    print("=" * 50)
    
    # 设置今天的目录
    today_dir, today = setup_today_directory()
    
    # 检查cookie文件
    check_cookie_files()
    
    # 显示上传命令
    show_upload_commands(today)
    
    print("📋 操作步骤总结:")
    print("1. 将视频文件(.mp4)放入今天的目录")
    print("2. 为每个视频创建同名的.txt文件(标题和标签)")
    print("3. 确保已获取对应平台的登录信息")
    print("4. 运行上传命令")
    print()
    
    print("🎉 设置完成！")


if __name__ == '__main__':
    main() 