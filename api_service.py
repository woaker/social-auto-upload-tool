from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import subprocess
import json
import os
import uuid
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="统一API服务",
    description="整合头条文章转发、YouTube视频下载等多平台API接口",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局任务状态
task_status = {}

# 创建独立的任务队列
toutiao_task_queue = asyncio.Queue(maxsize=50)  # 头条转发任务队列
youtube_task_queue = asyncio.Queue(maxsize=50)  # YouTube下载任务队列

# 头条文章转发相关模型
class ToutiaoForwardRequest(BaseModel):
    urls: List[str]
    save_file: bool = False
    account_file: str = "cookiesFile/toutiao_cookie.json"
    use_ai: bool = False
    default_tags: List[str] = ["AI", "互联网", "自动化"]

class ToutiaoForwardResponse(BaseModel):
    task_id: str
    status: str
    message: str

# YouTube视频下载相关模型
class YouTubeDownloadRequest(BaseModel):
    url: List[str]
    quality: str = "best"
    output_dir: str = "videos"
    platforms: List[str] = ["douyin", "bilibili", "kuaishou", "xiaohongshu", "baijiahao"]
    title: Optional[str] = None
    tags: List[str] = ["MCP", "AI", "互联网", "自动化", "技术"]
    schedule_time: Optional[str] = None

class YouTubeDownloadResponse(BaseModel):
    task_id: str
    status: str
    message: str

# 任务状态查询响应
class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    message: str
    result: Optional[Dict[str, Any]] = None

@app.get("/")
async def root():
    return {
        "name": "统一API服务",
        "version": "1.0.0",
        "description": "整合头条文章转发、YouTube视频下载等多平台API接口",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

# 头条文章转发接口
@app.post("/api/toutiao/forward", response_model=ToutiaoForwardResponse)
async def forward_article_to_toutiao(request: ToutiaoForwardRequest):
    """将文章转发到今日头条"""
    if len(request.urls) == 0:
        raise HTTPException(status_code=400, detail="URL列表不能为空")
    
    task_id = str(uuid.uuid4())
    task_status[task_id] = {
        "status": "queued",
        "message": "任务已加入队列",
        "created_at": datetime.now().isoformat(),
        "type": "toutiao_forward"
    }
    
    # 将任务加入队列
    try:
        toutiao_task_queue.put_nowait({
            "task_id": task_id,
            "type": "toutiao_forward",
            "data": request.model_dump()
        })
        logger.info(f"头条转发任务已加入队列: {task_id}")
    except asyncio.QueueFull:
        task_status[task_id]["status"] = "error"
        task_status[task_id]["message"] = "队列已满，请稍后重试"
        raise HTTPException(status_code=503, detail="服务繁忙，请稍后重试")
    
    return ToutiaoForwardResponse(
        task_id=task_id,
        status="queued",
        message="任务已加入队列，请通过 /api/task/{task_id} 查询状态"
    )

# 头条账号获取接口
@app.get("/api/toutiao/accounts")
async def get_toutiao_accounts():
    """获取可用的头条账号列表"""
    try:
        accounts = []
        cookies_dir = "cookiesFile"
        if os.path.exists(cookies_dir):
            for file in os.listdir(cookies_dir):
                if file.endswith(".json") and "toutiao" in file:
                    accounts.append({
                        "file": file,
                        "path": os.path.join(cookies_dir, file),
                        "name": "未命名账号"
                    })
        return {"accounts": accounts}
    except Exception as e:
        logger.error(f"获取头条账号失败: {e}")
        raise HTTPException(status_code=500, detail="获取账号失败")

# YouTube视频下载和上传接口
@app.post("/api/youtube/download", response_model=YouTubeDownloadResponse)
async def download_youtube_video(request: YouTubeDownloadRequest):
    """下载YouTube视频并上传到指定平台"""
    if len(request.url) == 0:
        raise HTTPException(status_code=400, detail="URL列表不能为空")
    
    task_id = str(uuid.uuid4())
    task_status[task_id] = {
        "status": "queued",
        "message": "任务已加入队列",
        "created_at": datetime.now().isoformat(),
        "type": "youtube_download"
    }
    
    # 将任务加入队列
    try:
        youtube_task_queue.put_nowait({
            "task_id": task_id,
            "type": "youtube_download",
            "data": request.model_dump()
        })
        logger.info(f"YouTube下载任务已加入队列: {task_id}")
    except asyncio.QueueFull:
        task_status[task_id]["status"] = "error"
        task_status[task_id]["message"] = "队列已满，请稍后重试"
        raise HTTPException(status_code=503, detail="服务繁忙，请稍后重试")
    
    return YouTubeDownloadResponse(
        task_id=task_id,
        status="queued",
        message="任务已加入队列，请通过 /api/task/{task_id} 查询状态"
    )

# 任务状态查询接口
@app.get("/api/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """查询任务状态"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_info = task_status[task_id]
    return TaskStatusResponse(
        task_id=task_id,
        status=task_info["status"],
        message=task_info["message"],
        result=task_info.get("result")
    )

# 查看所有任务队列执行日志接口
@app.get("/api/tasks/logs")
async def get_all_task_logs():
    """查看所有任务队列的执行日志"""
    try:
        logs = []
        for task_id, task_info in task_status.items():
            log_entry = {
                "task_id": task_id,
                "type": task_info.get("type", "unknown"),
                "status": task_info["status"],
                "message": task_info["message"],
                "created_at": task_info.get("created_at"),
                "completed_at": task_info.get("completed_at"),
                "result": task_info.get("result")
            }
            logs.append(log_entry)
        
        # 按创建时间倒序排列
        logs.sort(key=lambda x: x["created_at"] or "", reverse=True)
        
        return {
            "total_tasks": len(logs),
            "tasks": logs
        }
    except Exception as e:
        logger.error(f"获取任务日志失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务日志失败")



# 后台任务处理器
async def toutiao_task_worker():
    """头条任务处理worker"""
    while True:
        try:
            task = await toutiao_task_queue.get()
            task_id = task["task_id"]
            task_type = task["type"]
            task_data = task["data"]
            
            logger.info(f"开始处理头条任务: {task_id}, 类型: {task_type}")
            task_status[task_id]["status"] = "processing"
            task_status[task_id]["message"] = "正在处理中..."
            
            if task_type == "toutiao_forward":
                await process_toutiao_forward(task_id, task_data)
            else:
                task_status[task_id]["status"] = "error"
                task_status[task_id]["message"] = "未知任务类型"
                
        except Exception as e:
            logger.error(f"头条任务处理失败: {e}")
            if "task_id" in locals():
                task_status[task_id]["status"] = "error"
                task_status[task_id]["message"] = f"处理失败: {str(e)}"

async def youtube_task_worker():
    """YouTube任务处理worker"""
    while True:
        try:
            task = await youtube_task_queue.get()
            task_id = task["task_id"]
            task_type = task["type"]
            task_data = task["data"]
            
            logger.info(f"开始处理YouTube任务: {task_id}, 类型: {task_type}")
            task_status[task_id]["status"] = "processing"
            task_status[task_id]["message"] = "正在处理中..."
            
            if task_type == "youtube_download":
                await process_youtube_download(task_id, task_data)
            else:
                task_status[task_id]["status"] = "error"
                task_status[task_id]["message"] = "未知任务类型"
                
        except Exception as e:
            logger.error(f"YouTube任务处理失败: {e}")
            if "task_id" in locals():
                task_status[task_id]["status"] = "error"
                task_status[task_id]["message"] = f"处理失败: {str(e)}"

async def process_toutiao_forward(task_id: str, data: dict):
    """处理头条文章转发任务"""
    try:
        urls = data["urls"]
        results = []
        
        for url in urls:
            # 构建命令参数
            cmd = ["python3", "examples/forward_article_to_toutiao.py", url]
            
            # 添加可选参数
            if not data.get("save_file", True):
                cmd.append("--no-save")
            
            if not data.get("use_ai", True):
                cmd.append("--no-ai")
            
            logger.info(f"执行头条转发命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            if result.returncode == 0:
                results.append({
                    "url": url,
                    "status": "success",
                    "output": result.stdout
                })
            else:
                results.append({
                    "url": url,
                    "status": "error",
                    "error": result.stderr
                })
        
        # 检查整体结果
        success_count = sum(1 for r in results if r["status"] == "success")
        if success_count == len(urls):
            task_status[task_id]["status"] = "completed"
            task_status[task_id]["message"] = f"所有文章转发成功 ({success_count}/{len(urls)})"
        elif success_count > 0:
            task_status[task_id]["status"] = "completed"
            task_status[task_id]["message"] = f"部分文章转发成功 ({success_count}/{len(urls)})"
        else:
            task_status[task_id]["status"] = "error"
            task_status[task_id]["message"] = "所有文章处理失败"
        
        task_status[task_id]["result"] = {"forwarded_articles": results}
        task_status[task_id]["completed_at"] = datetime.now().isoformat()
            
    except subprocess.TimeoutExpired:
        task_status[task_id]["status"] = "error"
        task_status[task_id]["message"] = "任务超时"
        task_status[task_id]["completed_at"] = datetime.now().isoformat()
    except Exception as e:
        task_status[task_id]["status"] = "error"
        task_status[task_id]["message"] = f"处理异常: {str(e)}"
        task_status[task_id]["completed_at"] = datetime.now().isoformat()

async def process_youtube_download(task_id: str, data: dict):
    """处理YouTube视频下载和上传任务"""
    try:
        urls = data["url"]
        results = []
        
        for url in urls:
            # 构建请求数据
            request_data = {
                "url": [url],
                "platforms": data.get("platforms", ["douyin", "bilibili", "kuaishou", "xiaohongshu", "baijiahao"]),
                "title": data.get("title"),
                "tags": data.get("tags", ["MCP", "AI", "互联网", "自动化", "技术"]),
                "schedule_time": data.get("schedule_time")
            }
            
            # 过滤掉None值
            request_data = {k: v for k, v in request_data.items() if v is not None}
            
            # 调用YouTube API的完整功能（下载+上传）
            cmd = [
                "python3", "-c",
                f"""
import asyncio
import sys
import json
sys.path.append('.')
from youtube_api import process_youtube_video, YouTubeDownloadRequest

async def main():
    request = YouTubeDownloadRequest(**{json.dumps(request_data)})
    await process_youtube_video('{task_id}', request)

if __name__ == '__main__':
    asyncio.run(main())
                """
            ]
            
            logger.info(f"执行YouTube下载+上传命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # 增加超时时间
            
            if result.returncode == 0:
                results.append({
                    "url": url,
                    "status": "success",
                    "output": result.stdout
                })
            else:
                results.append({
                    "url": url,
                    "status": "error",
                    "error": result.stderr
                })
        
        # 检查整体结果
        success_count = sum(1 for r in results if r["status"] == "success")
        if success_count == len(urls):
            task_status[task_id]["status"] = "completed"
            task_status[task_id]["message"] = f"所有视频下载并上传成功 ({success_count}/{len(urls)})"
        elif success_count > 0:
            task_status[task_id]["status"] = "completed"
            task_status[task_id]["message"] = f"部分视频下载并上传成功 ({success_count}/{len(urls)})"
        else:
            task_status[task_id]["status"] = "error"
            task_status[task_id]["message"] = "所有视频处理失败"
        
        task_status[task_id]["result"] = {"downloads": results}
        task_status[task_id]["completed_at"] = datetime.now().isoformat()
            
    except subprocess.TimeoutExpired:
        task_status[task_id]["status"] = "error"
        task_status[task_id]["message"] = "任务超时"
        task_status[task_id]["completed_at"] = datetime.now().isoformat()
    except Exception as e:
        task_status[task_id]["status"] = "error"
        task_status[task_id]["message"] = f"处理异常: {str(e)}"
        task_status[task_id]["completed_at"] = datetime.now().isoformat()

@app.on_event("startup")
async def startup_event():
    """服务启动时启动后台worker"""
    asyncio.create_task(toutiao_task_worker())
    asyncio.create_task(youtube_task_worker())
    logger.info("统一API服务已启动，后台worker已启动")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 