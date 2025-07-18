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

# 全局任务队列和状态
task_queue = asyncio.Queue(maxsize=100)
task_status = {}

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
    if len(request.urls) != 1:
        raise HTTPException(status_code=400, detail="单次仅支持1个URL")
    
    task_id = str(uuid.uuid4())
    task_status[task_id] = {
        "status": "queued",
        "message": "任务已加入队列",
        "created_at": datetime.now().isoformat()
    }
    
    # 将任务加入队列
    try:
        task_queue.put_nowait({
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

# YouTube视频下载接口
@app.post("/api/youtube/download", response_model=YouTubeDownloadResponse)
async def download_youtube_video(request: YouTubeDownloadRequest):
    """下载YouTube视频"""
    if len(request.url) == 0:
        raise HTTPException(status_code=400, detail="URL列表不能为空")
    
    task_id = str(uuid.uuid4())
    task_status[task_id] = {
        "status": "queued",
        "message": "任务已加入队列",
        "created_at": datetime.now().isoformat()
    }
    
    # 将任务加入队列
    try:
        task_queue.put_nowait({
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

# 后台任务处理器
async def task_worker():
    """后台任务处理worker"""
    while True:
        try:
            task = await task_queue.get()
            task_id = task["task_id"]
            task_type = task["type"]
            task_data = task["data"]
            
            logger.info(f"开始处理任务: {task_id}, 类型: {task_type}")
            task_status[task_id]["status"] = "processing"
            task_status[task_id]["message"] = "正在处理中..."
            
            if task_type == "toutiao_forward":
                await process_toutiao_forward(task_id, task_data)
            elif task_type == "youtube_download":
                await process_youtube_download(task_id, task_data)
            else:
                task_status[task_id]["status"] = "error"
                task_status[task_id]["message"] = "未知任务类型"
                
        except Exception as e:
            logger.error(f"任务处理失败: {e}")
            if "task_id" in locals():
                task_status[task_id]["status"] = "error"
                task_status[task_id]["message"] = f"处理失败: {str(e)}"

async def process_toutiao_forward(task_id: str, data: dict):
    """处理头条文章转发任务"""
    try:
        # 调用头条转发脚本
        cmd = [
            "python3", "examples/forward_article_to_toutiao.py",
            "--urls", json.dumps(data["urls"]),
            "--save_file", str(data["save_file"]),
            "--account_file", data["account_file"],
            "--use_ai", str(data["use_ai"]),
            "--default_tags", json.dumps(data["default_tags"])
        ]
        
        logger.info(f"执行头条转发命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        
        if result.returncode == 0:
            task_status[task_id]["status"] = "completed"
            task_status[task_id]["message"] = "转发成功"
            task_status[task_id]["result"] = {"output": result.stdout}
        else:
            task_status[task_id]["status"] = "error"
            task_status[task_id]["message"] = f"转发失败: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        task_status[task_id]["status"] = "error"
        task_status[task_id]["message"] = "任务超时"
    except Exception as e:
        task_status[task_id]["status"] = "error"
        task_status[task_id]["message"] = f"处理异常: {str(e)}"

async def process_youtube_download(task_id: str, data: dict):
    """处理YouTube视频下载任务"""
    try:
        urls = data["url"]
        results = []
        
        for url in urls:
            # 调用YouTube下载脚本
            cmd = [
                "python3", "youtube_api.py",
                "--url", url,
                "--quality", data["quality"],
                "--output_dir", data["output_dir"]
            ]
            
            logger.info(f"执行YouTube下载命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
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
            task_status[task_id]["message"] = f"所有视频下载成功 ({success_count}/{len(urls)})"
        elif success_count > 0:
            task_status[task_id]["status"] = "completed"
            task_status[task_id]["message"] = f"部分视频下载成功 ({success_count}/{len(urls)})"
        else:
            task_status[task_id]["status"] = "error"
            task_status[task_id]["message"] = "所有视频下载失败"
        
        task_status[task_id]["result"] = {"downloads": results}
            
    except subprocess.TimeoutExpired:
        task_status[task_id]["status"] = "error"
        task_status[task_id]["message"] = "任务超时"
    except Exception as e:
        task_status[task_id]["status"] = "error"
        task_status[task_id]["message"] = f"处理异常: {str(e)}"

@app.on_event("startup")
async def startup_event():
    """服务启动时启动后台worker"""
    asyncio.create_task(task_worker())
    logger.info("统一API服务已启动，后台worker已启动")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 