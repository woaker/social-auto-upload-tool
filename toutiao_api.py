#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章转发到今日头条API
支持批量转发多个文章URL到今日头条
"""

import os
import sys
import asyncio
import json
import uuid
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import List, Dict, Optional, Any
import time

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
from examples.forward_article_to_toutiao import forward_article_from_url, publish_article_to_toutiao

# 配置日志
log_dir = os.path.join(BASE_DIR, "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "toutiao_api.log")

# 创建日志处理器
logger = logging.getLogger("toutiao_api")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# 创建FastAPI应用
app = FastAPI(
    title="文章转发到今日头条API",
    description="支持批量转发多个文章URL到今日头条",
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
class ArticleForwardRequest(BaseModel):
    urls: List[HttpUrl] = Field(..., description="文章URL列表，支持传入多个文章地址")
    save_file: bool = Field(default=False, description="是否保存文章到本地文件")
    account_file: str = Field(default="cookiesFile/toutiao_cookie.json", description="头条账号配置文件路径")
    enhance_content: bool = Field(default=True, description="是否增强文章内容")
    use_ai: bool = Field(default=False, description="是否使用AI功能（启用AI美化内容和生成标签）")
    default_tags: List[str] = Field(default=["AI", "互联网", "自动化"], description="默认文章标签")

# 定义响应模型
class TaskResponse(BaseModel):
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="任务消息")

class ArticleResponse(BaseModel):
    url: str = Field(..., description="原文章URL")
    title: str = Field(..., description="文章标题")
    status: str = Field(..., description="处理状态")
    message: str = Field(..., description="处理消息")
    toutiao_url: Optional[str] = Field(None, description="头条发布URL")

# 全局发布队列和任务状态
PUBLISH_QUEUE_MAXSIZE = 100
PUBLISH_TIMEOUT = 180  # 3分钟
publish_queue = asyncio.Queue(maxsize=PUBLISH_QUEUE_MAXSIZE)
task_status = {}  # {task_id: {...}}

async def publish_worker():
    while True:
        task_id, article_req, article_url = await publish_queue.get()
        task_status[task_id]["status"] = "processing"
        task_status[task_id]["start_time"] = time.time()
        try:
            # 单篇文章发布，带超时
            async def publish_one():
                # 只处理一篇
                result = await process_article_batch_single(task_id, article_req, article_url)
                return result
            await asyncio.wait_for(publish_one(), timeout=PUBLISH_TIMEOUT)
            if task_status[task_id]["status"] == "processing":
                task_status[task_id]["status"] = "completed"
        except asyncio.TimeoutError:
            task_status[task_id]["status"] = "timeout"
            task_status[task_id]["message"] = "任务超时（3分钟）"
        except Exception as e:
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["message"] = f"任务失败: {str(e)}"
        finally:
            publish_queue.task_done()

# 启动worker
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(publish_worker())

# 单篇文章处理逻辑
async def process_article_batch_single(task_id: str, request: ArticleForwardRequest, url: str):
    url_str = str(url)
    logger.info(f"[队列] 任务{task_id} 开始处理文章: {url_str}")
    result = {
        "url": url_str,
        "title": "",
        "status": "processing",
        "message": "正在处理",
        "toutiao_url": None,
        "stdout": "",
        "stderr": ""
    }
    try:
        # 用subprocess调用命令行脚本
        cmd = [
            "python3", "examples/forward_article_to_toutiao.py",
            url_str, "--no-save"
        ]
        logger.info(f"[队列] 任务{task_id} 调用命令: {' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            result["status"] = "timeout"
            result["message"] = "命令行发布超时"
            task_status[task_id]["results"].append(result)
            task_status[task_id]["completed"] += 1
            logger.error(f"[队列] 任务{task_id} 命令行超时")
            return
        result["stdout"] = stdout.decode(errors="ignore")
        result["stderr"] = stderr.decode(errors="ignore")
        if proc.returncode == 0:
            result["status"] = "success"
            result["message"] = "命令行发布成功"
            logger.info(f"[队列] 任务{task_id} 命令行发布成功")
        else:
            result["status"] = "failed"
            result["message"] = f"命令行发布失败: {result['stderr']}"
            logger.error(f"[队列] 任务{task_id} 命令行发布失败: {result['stderr']}")
        task_status[task_id]["results"].append(result)
        task_status[task_id]["completed"] += 1
    except Exception as e:
        result["status"] = "failed"
        result["message"] = f"命令行异常: {str(e)}"
        result["stderr"] += f"\nException: {str(e)}"
        task_status[task_id]["results"].append(result)
        task_status[task_id]["completed"] += 1
        logger.error(f"[队列] 任务{task_id} 命令行异常: {str(e)}", exc_info=True)
    logger.info(f"[队列] 任务{task_id} 处理完成: {result['status']}")

@app.post("/api/toutiao/forward", response_model=TaskResponse)
async def forward_articles(request: ArticleForwardRequest, background_tasks: BackgroundTasks):
    """
    单线程队列串行转发文章到今日头条
    """
    # 只允许单篇文章（如需批量可循环调用）
    if len(request.urls) != 1:
        raise HTTPException(status_code=400, detail="每次只允许提交一篇文章（urls只能有一个元素）")
    if publish_queue.full():
        return {"task_id": None, "status": "queue_full", "message": "队列已满，请稍后再试"}
    task_id = str(uuid.uuid4())
    task_status[task_id] = {
        "status": "queued",
        "message": "已加入队列，等待发布",
        "total": 1,
        "completed": 0,
        "success": 0,
        "failed": 0,
        "results": [],
        "start_time": None
    }
    await publish_queue.put((task_id, request, request.urls[0]))
    return {
        "task_id": task_id,
        "status": "queued",
        "message": "已加入队列，等待发布"
    }

@app.get("/api/toutiao/status/{task_id}", response_model=Dict[str, Any])
async def get_task_status(task_id: str):
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task_status[task_id]

@app.get("/api/toutiao/accounts")
async def get_accounts():
    """
    获取可用的头条账号列表
    
    返回系统中配置的头条账号信息
    """
    try:
        # 查找cookiesFile目录下的头条cookie文件
        cookies_dir = os.path.join(BASE_DIR, "cookiesFile")
        if not os.path.exists(cookies_dir):
            return {"accounts": []}
        
        accounts = []
        for file in os.listdir(cookies_dir):
            if file.startswith("toutiao_") and file.endswith(".json"):
                account_path = os.path.join(cookies_dir, file)
                try:
                    with open(account_path, "r", encoding="utf-8") as f:
                        account_data = json.load(f)
                        account_info = {
                            "file": file,
                            "path": account_path,
                            "name": account_data.get("name", "未命名账号")
                        }
                        accounts.append(account_info)
                except:
                    # 跳过无法解析的文件
                    pass
        
        return {"accounts": accounts}
    except Exception as e:
        logger.error(f"获取账号列表失败: {str(e)}")
        return {"accounts": [], "error": str(e)}

@app.get("/")
async def root():
    """API根路径，返回简单的欢迎信息"""
    return {
        "message": "文章转发到今日头条API服务",
        "version": "1.0.0",
        "endpoints": {
            "forward_articles": "/api/toutiao/forward",
            "get_task_status": "/api/toutiao/status/{task_id}",
            "get_accounts": "/api/toutiao/accounts"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("toutiao_api:app", host="0.0.0.0", port=8001, reload=True) 