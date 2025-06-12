#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量视频下载脚本
使用 yt-dlp 下载指定的视频文件
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List
import json


class VideoDownloader:
    def __init__(self, download_dir: str = "./downloads"):
        """
        初始化下载器
        
        Args:
            download_dir: 下载目录路径
        """
        self.download_dir = Path(download_dir).resolve()
        self.ensure_download_dir()
        self.check_yt_dlp()
    
    def ensure_download_dir(self):
        """确保下载目录存在"""
        self.download_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ 下载目录已设置为: {self.download_dir}")
    
    def check_yt_dlp(self):
        """检查 yt-dlp 是否已安装"""
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                   capture_output=True, text=True, check=True)
            print(f"✓ yt-dlp 版本: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ 错误: yt-dlp 未安装或不在 PATH 中")
            print("请先安装 yt-dlp:")
            print("  pip install yt-dlp")
            print("  或")
            print("  brew install yt-dlp")
            sys.exit(1)
    
    def download_video(self, url: str, custom_options: List[str] = None) -> bool:
        """
        下载单个视频
        
        Args:
            url: 视频URL
            custom_options: 自定义yt-dlp选项
            
        Returns:
            bool: 下载是否成功
        """
        print(f"\n🔽 开始下载: {url}")
        
        # 基础选项
        cmd = [
            'yt-dlp',
            '--output', str(self.download_dir / '%(title)s.%(ext)s')
        ]
        
        # 添加自定义选项
        if custom_options:
            cmd.extend(custom_options)
        
        # 添加URL
        cmd.append(url)
        
        try:
            # 执行下载命令
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✓ 下载成功: {url}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 下载失败: {url}")
            print(f"错误信息: {e.stderr}")
            return False
    
    def download_from_urls(self, urls: List[str], custom_options: List[str] = None) -> dict:
        """
        批量下载视频
        
        Args:
            urls: 视频URL列表
            custom_options: 自定义yt-dlp选项
            
        Returns:
            dict: 下载结果统计
        """
        total = len(urls)
        success_count = 0
        failed_urls = []
        
        print(f"\n📺 开始批量下载 {total} 个视频...")
        print(f"下载目录: {self.download_dir}")
        print("-" * 50)
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{total}] 处理中...")
            success = self.download_video(url, custom_options)
            
            if success:
                success_count += 1
            else:
                failed_urls.append(url)
        
        # 打印结果统计
        print("\n" + "=" * 50)
        print(f"📊 下载完成!")
        print(f"总数: {total}")
        print(f"成功: {success_count}")
        print(f"失败: {len(failed_urls)}")
        
        if failed_urls:
            print("\n❌ 失败的URL:")
            for url in failed_urls:
                print(f"  - {url}")
        
        return {
            'total': total,
            'success': success_count,
            'failed': len(failed_urls),
            'failed_urls': failed_urls
        }
    
    def download_from_file(self, file_path: str, custom_options: List[str] = None) -> dict:
        """
        从文件读取URL并批量下载
        
        Args:
            file_path: 包含URL的文件路径
            custom_options: 自定义yt-dlp选项
            
        Returns:
            dict: 下载结果统计
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if not urls:
                print(f"❌ 文件 {file_path} 中没有找到有效的URL")
                return {'total': 0, 'success': 0, 'failed': 0, 'failed_urls': []}
            
            print(f"✓ 从文件 {file_path} 读取到 {len(urls)} 个URL")
            return self.download_from_urls(urls, custom_options)
            
        except FileNotFoundError:
            print(f"❌ 文件不存在: {file_path}")
            return {'total': 0, 'success': 0, 'failed': 0, 'failed_urls': []}
        except Exception as e:
            print(f"❌ 读取文件时出错: {e}")
            return {'total': 0, 'success': 0, 'failed': 0, 'failed_urls': []}


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='批量视频下载工具 - 使用 yt-dlp',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 从命令行参数下载
  python batch_video_downloader.py -d ./videos -u "https://example.com/video1" "https://example.com/video2"
  
  # 从文件下载
  python batch_video_downloader.py -d ./videos -f urls.txt
  
  # 使用自定义选项
  python batch_video_downloader.py -d ./videos -f urls.txt --options "--format" "best[height<=720]"
        """)
    
    parser.add_argument('-d', '--dir', default='./downloads',
                        help='下载目录 (默认: ./downloads)')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-u', '--urls', nargs='+',
                       help='视频URL列表')
    group.add_argument('-f', '--file',
                       help='包含URL的文件路径 (每行一个URL)')
    
    parser.add_argument('--options', nargs='*',
                        help='自定义 yt-dlp 选项')
    
    args = parser.parse_args()
    
    # 创建下载器
    downloader = VideoDownloader(args.dir)
    
    # 执行下载
    if args.urls:
        result = downloader.download_from_urls(args.urls, args.options)
    else:
        result = downloader.download_from_file(args.file, args.options)
    
    # 退出码
    sys.exit(0 if result['failed'] == 0 else 1)


if __name__ == '__main__':
    main() 