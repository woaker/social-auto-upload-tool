#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频格式转换工具
支持将各种视频格式转换为小红书等平台支持的格式
"""

import os
import subprocess
import tempfile
from pathlib import Path
from utils.log import xiaohongshu_logger


class VideoConverter:
    """视频格式转换器"""
    
    def __init__(self):
        self.supported_formats = {'.mp4', '.mov', '.avi'}  # 小红书支持的格式
        self.temp_files = []  # 用于跟踪临时文件
    
    def is_supported_format(self, file_path):
        """检查文件格式是否被平台支持"""
        return Path(file_path).suffix.lower() in self.supported_formats
    
    def is_format_supported(self, file_path, supported_formats):
        """检查文件格式是否在指定的支持格式列表中"""
        file_ext = Path(file_path).suffix.lower()
        return file_ext in [fmt.lower() for fmt in supported_formats]
    
    def check_ffmpeg_available(self):
        """检查系统是否安装了ffmpeg"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def convert_to_mp4(self, input_file, output_file=None):
        """
        将视频转换为MP4格式
        
        Args:
            input_file: 输入视频文件路径
            output_file: 输出文件路径（可选，默认生成临时文件）
        
        Returns:
            str: 转换后的文件路径
        """
        input_path = Path(input_file)
        
        # 如果已经是支持的格式，直接返回原文件
        if self.is_supported_format(input_file):
            xiaohongshu_logger.info(f"文件格式已支持，无需转换: {input_path.suffix}")
            return str(input_file)
        
        # 检查ffmpeg是否可用
        if not self.check_ffmpeg_available():
            xiaohongshu_logger.error("❌ 未安装ffmpeg，无法进行视频格式转换")
            xiaohongshu_logger.error("请安装ffmpeg: brew install ffmpeg (macOS) 或访问 https://ffmpeg.org/")
            raise RuntimeError("ffmpeg未安装")
        
        # 生成输出文件路径
        if output_file is None:
            # 创建临时文件
            temp_dir = tempfile.gettempdir()
            output_file = os.path.join(temp_dir, f"{input_path.stem}_converted.mp4")
            self.temp_files.append(output_file)  # 记录临时文件用于后续清理
        
        xiaohongshu_logger.info(f"🔄 开始转换视频格式: {input_path.suffix} -> .mp4")
        xiaohongshu_logger.info(f"   输入文件: {input_file}")
        xiaohongshu_logger.info(f"   输出文件: {output_file}")
        
        try:
            # 使用ffmpeg进行转换 - 优化参数提高速度
            cmd = [
                'ffmpeg',
                '-i', str(input_file),
                '-c:v', 'libx264',  # 视频编码器
                '-c:a', 'aac',      # 音频编码器
                '-crf', '28',       # 质量参数 (提高到28以加快速度)
                '-preset', 'fast',  # 使用快速预设
                '-movflags', '+faststart',  # 优化web播放
                '-threads', '0',    # 使用所有可用CPU核心
                '-y',  # 覆盖输出文件
                str(output_file)
            ]
            
            xiaohongshu_logger.info(f"🔧 转换命令: {' '.join(cmd)}")
            
            # 执行转换命令 - 增加超时时间到15分钟
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=900  # 15分钟超时
            )
            
            if result.returncode == 0:
                xiaohongshu_logger.success(f"✅ 视频转换成功: {output_file}")
                
                # 检查输出文件是否存在且不为空
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    return output_file
                else:
                    xiaohongshu_logger.error("转换后的文件为空或不存在")
                    raise RuntimeError("转换失败：输出文件无效")
            else:
                xiaohongshu_logger.error(f"❌ 视频转换失败:")
                xiaohongshu_logger.error(f"错误信息: {result.stderr}")
                raise RuntimeError(f"ffmpeg转换失败: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            xiaohongshu_logger.error("❌ 视频转换超时（15分钟）")
            raise RuntimeError("视频转换超时")
        except Exception as e:
            xiaohongshu_logger.error(f"❌ 视频转换过程中出错: {e}")
            raise
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    xiaohongshu_logger.info(f"🗑️  已清理临时文件: {temp_file}")
            except Exception as e:
                xiaohongshu_logger.warning(f"⚠️  清理临时文件失败: {temp_file}, 错误: {e}")
        
        self.temp_files.clear()
    
    def cleanup_temp_file(self, file_path):
        """清理单个临时文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                xiaohongshu_logger.info(f"🗑️  已清理临时文件: {file_path}")
            # 从临时文件列表中移除
            if file_path in self.temp_files:
                self.temp_files.remove(file_path)
        except Exception as e:
            xiaohongshu_logger.warning(f"⚠️  清理临时文件失败: {file_path}, 错误: {e}")


# 创建全局转换器实例
video_converter = VideoConverter()


def convert_video_if_needed(file_path, platform="xiaohongshu"):
    """
    如果需要，转换视频格式
    
    Args:
        file_path: 视频文件路径
        platform: 目标平台（用于确定支持的格式）
    
    Returns:
        str: 可用的视频文件路径（原文件或转换后的文件）
    """
    try:
        return video_converter.convert_to_mp4(file_path)
    except Exception as e:
        xiaohongshu_logger.error(f"❌ 视频格式转换失败: {e}")
        raise


def cleanup_converted_files():
    """清理所有转换生成的临时文件"""
    video_converter.cleanup_temp_files() 