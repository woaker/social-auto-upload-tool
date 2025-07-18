#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube视频下载与多平台转发API
支持异步下载YouTube视频并转发到多个社交媒体平台
"""

import os
import sys
import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import uuid
import tempfile
import logging
from logging.handlers import RotatingFileHandler

# FastAPI相关
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 导入项目模块
from conf import BASE_DIR
from utils.log import douyin_logger
from utils.video_converter import convert_video_if_needed, extract_video_thumbnail
from batch_upload_by_date import BatchUploader
from uploader.douyin_uploader.main import DouYinVideo

# 配置日志
log_dir = os.path.join(BASE_DIR, "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "youtube_api.log")

# 创建日志处理器
logger = logging.getLogger("youtube_api")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# 创建FastAPI应用
app = FastAPI(
    title="YouTube视频下载与多平台转发API",
    description="支持异步下载YouTube视频并转发到多个社交媒体平台",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义请求模型
class YouTubeDownloadRequest(BaseModel):
    url: List[HttpUrl] = Field(..., description="YouTube视频URL列表，支持传入多个视频地址")
    platforms: List[str] = Field(default=["douyin","bilibili","kuaishou","xiaohongshu","baijiahao"], description="要转发的平台列表，支持：douyin, bilibili, kuaishou, xiaohongshu, baijiahao，或使用'all'表示所有平台")
    title: Optional[str] = Field(default=None, description="自定义视频标题，如不提供则使用YouTube标题")
    tags: Optional[List[str]] = Field(default=["MCP","AI","互联网","自动化","技术"], description="视频标签列表")
    schedule_time: Optional[str] = Field(default=None, description="定时发布时间，格式：YYYY-MM-DD HH:MM:SS，不提供则立即发布")

# 定义响应模型
class TaskResponse(BaseModel):
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="任务消息")

# 任务状态存储
task_status = {}

async def download_youtube_video(url: str) -> str:
    """
    下载YouTube视频
    
    Args:
        url: YouTube视频URL
        
    Returns:
        str: 下载的视频文件路径
    """
    logger.info(f"开始下载YouTube视频: {url}")
    
    # 创建临时目录存放下载的视频
    temp_dir = os.path.join(tempfile.gettempdir(), f"youtube_dl_{uuid.uuid4().hex}")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 使用yt-dlp下载视频
        from yt_dlp import YoutubeDL
        
        # 下载选项
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # 优先下载mp4格式
            'outtmpl': os.path.join(temp_dir, '%(title).100s.%(ext)s'),  # 限制标题长度，避免路径问题
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': False,
        }
        
        # 下载视频
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'unknown_title')
            
            # 查找下载的文件
            video_path = None
            for file in os.listdir(temp_dir):
                if file.endswith(('.mp4', '.webm', '.mkv', '.avi')):
                    video_path = os.path.join(temp_dir, file)
                    break
            
            if not video_path:
                raise Exception("未找到下载的视频文件")
            
            # 获取视频信息
            logger.info(f"视频已下载: {video_path}")
            return video_path
            
    except Exception as e:
        logger.error(f"下载YouTube视频失败: {e}")
        raise Exception(f"下载YouTube视频失败: {e}")

async def prepare_video_for_upload(video_path: str, title: Optional[str] = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    准备视频上传，包括转换格式、创建标签文件等
    
    Args:
        video_path: 视频文件路径
        title: 自定义标题
        tags: 标签列表
        
    Returns:
        Dict: 包含处理后的视频信息
    """
    logger.info(f"准备视频上传: {video_path}")
    
    try:
        # 获取视频文件名（不含扩展名）
        video_file = Path(video_path)
        video_name = video_file.stem
        
        # 如果没有提供标题，使用文件名作为标题
        if not title:
            title = video_name
            
        # 如果没有提供标签，使用默认标签
        if not tags:
            tags = ["YouTube", "转发"]
            
        # 转换视频格式（如果需要）
        converted_path = convert_video_if_needed(video_path)
        
        # 提取视频封面
        thumbnail_path = extract_video_thumbnail(converted_path)
        
        # 创建标签文件（与视频同名的.txt文件）
        tags_file = video_file.with_suffix('.txt')
        with open(tags_file, 'w', encoding='utf-8') as f:
            f.write(f"{title}\n")
            f.write(' '.join(tags))
        
        # 返回处理后的视频信息
        return {
            "video_path": converted_path,
            "thumbnail_path": thumbnail_path,
            "title": title,
            "tags": tags,
            "tags_file": str(tags_file)
        }
        
    except Exception as e:
        logger.error(f"准备视频上传失败: {e}")
        raise Exception(f"准备视频上传失败: {e}")

async def upload_to_platforms(video_info: Dict[str, Any], platforms: List[str], schedule_time: Optional[str] = None) -> Dict[str, Any]:
    """
    将视频上传到指定平台
    
    Args:
        video_info: 视频信息
        platforms: 平台列表
        schedule_time: 定时发布时间
        
    Returns:
        Dict: 上传结果
    """
    logger.info(f"开始上传视频到平台: {platforms}")
    
    results = {}
    
    try:
        # 创建视频目录
        today = datetime.now().strftime('%Y-%m-%d')
        video_dir = os.path.join(BASE_DIR, "videoFile", today)
        os.makedirs(video_dir, exist_ok=True)
        
        # 复制视频文件和标签文件到视频目录
        video_path = video_info["video_path"]
        video_file = Path(video_path)
        target_video = os.path.join(video_dir, video_file.name)
        shutil.copy2(video_path, target_video)
        
        tags_file = video_info["tags_file"]
        target_tags = os.path.join(video_dir, Path(tags_file).name)
        shutil.copy2(tags_file, target_tags)
        
        # 如果有封面，也复制
        target_thumbnail = None
        if video_info.get("thumbnail_path"):
            thumbnail_path = video_info["thumbnail_path"]
            thumbnail_file = Path(thumbnail_path)
            target_thumbnail = os.path.join(video_dir, thumbnail_file.name)
            shutil.copy2(thumbnail_path, target_thumbnail)
            logger.info(f"已复制视频封面: {target_thumbnail}")
        
        # 设置定时发布
        enable_schedule = False
        daily_times = []
        start_days = 0
        
        if schedule_time:
            enable_schedule = True
            schedule_dt = datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S")
            daily_times = [f"{schedule_dt.hour}:{schedule_dt.minute}"]
            
            # 计算与今天的天数差
            today = datetime.now().date()
            schedule_date = schedule_dt.date()
            days_diff = (schedule_date - today).days
            start_days = max(0, days_diff - 1)  # BatchUploader会自动加1
        
        # 创建批量上传器
        uploader = BatchUploader(
            date_str=today,
            videos_per_day=1,
            daily_times=daily_times,
            start_days=start_days,
            enable_schedule=enable_schedule
        )
        
        # 获取视频文件列表
        video_files = [Path(target_video)]
        
        # 处理'all'平台特殊情况
        if len(platforms) == 1 and platforms[0].lower() == 'all':
            logger.info("上传到所有支持的平台")
            # 为每个平台设置正确的封面路径
            for platform_name in uploader.platforms:
                if platform_name == 'douyin':
                    # 特别处理抖音平台，确保传递封面参数
                    try:
                        account_file = uploader.platforms['douyin']['account_file']
                        if account_file:
                            for video_file in video_files:
                                title, tags = uploader.get_video_info(video_file)
                                # 创建抖音视频对象时传递缩略图路径
                                app = DouYinVideo(
                                    title=title, 
                                    file_path=str(video_file), 
                                    tags=tags, 
                                    publish_date=0 if not enable_schedule else uploader.get_publish_schedule(1)[0],
                                    account_file=account_file,
                                    thumbnail_path=target_thumbnail
                                )
                                # 设置默认地理位置
                                app.default_location = "上海市"
                                await app.main()
                                logger.info(f"抖音视频上传完成: {video_file.name}")
                    except Exception as e:
                        logger.error(f"抖音上传失败: {e}")
                        results['douyin'] = {"status": "failed", "message": str(e)}
                    else:
                        results['douyin'] = {"status": "success", "message": "上传成功"}
            
            # 上传到其他平台
            for platform in uploader.platforms:
                if platform != 'douyin':  # 抖音已单独处理
                    try:
                        if platform in uploader.platforms and uploader.platforms[platform]['account_file']:
                            logger.info(f"上传到平台: {platform}")
                            await uploader.upload_to_platform(platform, video_files)
                            results[platform] = {"status": "success", "message": "上传成功"}
                    except Exception as e:
                        logger.error(f"上传到{platform}失败: {e}")
                        results[platform] = {"status": "failed", "message": str(e)}
        else:
            # 上传到指定平台
            for platform in platforms:
                try:
                    if platform in uploader.platforms:
                        logger.info(f"上传到平台: {platform}")
                        
                        if platform == 'douyin':
                            # 特别处理抖音平台，确保传递封面参数
                            account_file = uploader.platforms['douyin']['account_file']
                            if account_file:
                                for video_file in video_files:
                                    title, tags = uploader.get_video_info(video_file)
                                    # 创建抖音视频对象时传递缩略图路径
                                    app = DouYinVideo(
                                        title=title, 
                                        file_path=str(video_file), 
                                        tags=tags, 
                                        publish_date=0 if not enable_schedule else uploader.get_publish_schedule(1)[0],
                                        account_file=account_file,
                                        thumbnail_path=target_thumbnail
                                    )
                                    # 设置默认地理位置
                                    app.default_location = "上海市"
                                    await app.main()
                                    logger.info(f"抖音视频上传完成: {video_file.name}")
                        else:
                            # 其他平台使用通用上传方法
                            await uploader.upload_to_platform(platform, video_files)
                            
                        results[platform] = {"status": "success", "message": "上传成功"}
                    else:
                        logger.warning(f"不支持的平台: {platform}")
                        results[platform] = {"status": "failed", "message": f"不支持的平台: {platform}"}
                except Exception as e:
                    logger.error(f"上传到{platform}失败: {e}")
                    results[platform] = {"status": "failed", "message": str(e)}
        
        return results
        
    except Exception as e:
        logger.error(f"上传视频失败: {e}")
        raise Exception(f"上传视频失败: {e}")

async def process_youtube_video(task_id: str, request: YouTubeDownloadRequest):
    """
    处理YouTube视频下载和上传的后台任务
    
    Args:
        task_id: 任务ID
        request: 请求参数
    """
    try:
        logger.info(f"============>开始处理YouTube视频: {request.url}")
        # 更新任务状态
        task_status[task_id] = {"status": "downloading", "message": "正在下载YouTube视频"}
        
        all_results = {}
        
        # 处理每个URL
        for url in request.url:
            # 下载YouTube视频
            video_path = await download_youtube_video(str(url))
            
            # 准备视频上传
            task_status[task_id] = {"status": "processing", "message": f"正在处理视频: {url}"}
            video_info = await prepare_video_for_upload(video_path, request.title, request.tags)
            
            # 上传到各平台
            task_status[task_id] = {"status": "uploading", "message": f"正在上传视频到各平台: {url}"}
            results = await upload_to_platforms(video_info, request.platforms, request.schedule_time)
            
            # 将结果添加到总结果中
            url_key = str(url)
            all_results[url_key] = results
        
        # 更新任务状态
        task_status[task_id] = {
            "status": "completed", 
            "message": "处理完成", 
            "results": all_results
        }
        
    except Exception as e:
        logger.error(f"任务处理失败: {e}")
        task_status[task_id] = {"status": "failed", "message": str(e)}

@app.post("/api/youtube/download", response_model=TaskResponse)
async def youtube_download(request: YouTubeDownloadRequest, background_tasks: BackgroundTasks):
    """
    下载YouTube视频并转发到指定平台
    """
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 初始化任务状态
    task_status[task_id] = {"status": "pending", "message": "任务已创建"}
    
    # 添加后台任务
    background_tasks.add_task(process_youtube_video, task_id, request)
    
    return {"task_id": task_id, "status": "pending", "message": "任务已创建，正在处理中"}

@app.get("/api/youtube/status/{task_id}")
async def get_task_status(task_id: str):
    """
    获取任务状态
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return task_status[task_id]

@app.get("/api/platforms")
async def get_platforms():
    """
    获取支持的平台列表
    """
    # 创建临时上传器以获取平台列表
    uploader = BatchUploader(date_str=datetime.now().strftime('%Y-%m-%d'))
    
    platforms = []
    for platform, config in uploader.platforms.items():
        platforms.append({
            "id": platform,
            "name": config["name"],
            "available": config["account_file"] is not None
        })
    
    # 添加"all"选项，表示所有平台
    platforms.append({
        "id": "all",
        "name": "所有平台",
        "available": True
    })
    
    return platforms

@app.get("/")
async def root():
    """
    API根路径，返回API信息
    """
    return {
        "name": "YouTube视频下载与多平台转发API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

if __name__ == "__main__":
    import argparse
    import sys
    
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 命令行模式
        parser = argparse.ArgumentParser(description="YouTube视频下载工具")
        parser.add_argument("--url", required=True, help="YouTube视频URL")
        parser.add_argument("--quality", default="best", help="视频质量")
        parser.add_argument("--output_dir", default="videos", help="输出目录")
        parser.add_argument("--download_type", default="default", help="下载类型: default, type1, type2")
        
        args = parser.parse_args()
        
        # 创建输出目录
        os.makedirs(args.output_dir, exist_ok=True)
        
        # 执行下载
        async def main():
            try:
                video_path = await download_youtube_video(args.url)
                # 移动文件到输出目录
                filename = os.path.basename(video_path)
                target_path = os.path.join(args.output_dir, filename)
                shutil.move(video_path, target_path)
                print(f"视频已下载到: {target_path} (类型: {args.download_type})")
                return 0
            except Exception as e:
                print(f"下载失败: {e}")
                return 1
        
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    else:
        # API服务模式
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000) 