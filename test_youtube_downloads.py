#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试YouTube下载接口
"""

import requests
import json
import time

# API基础URL
BASE_URL = "http://localhost:8000"

def test_youtube_download_with_platforms():
    """测试YouTube下载并上传到平台接口"""
    print("\n=== 测试YouTube下载并上传到平台接口 ===")
    
    url = f"{BASE_URL}/api/youtube/download"
    data = {
        "url": ["https://www.youtube.com/watch?v=-K0fODITV2c"],
        "platforms": ["douyin", "bilibili"],
        "title": "测试视频标题",
        "tags": ["测试", "技术", "AI"]
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        
        if response.status_code == 200:
            task_id = response.json()["task_id"]
            print(f"任务ID: {task_id}")
            
            # 查询任务状态
            time.sleep(2)
            status_url = f"{BASE_URL}/api/task/{task_id}"
            status_response = requests.get(status_url)
            print(f"任务状态: {status_response.json()}")
            
    except Exception as e:
        print(f"请求失败: {e}")

def test_get_all_task_logs():
    """测试获取所有任务日志"""
    print("\n=== 测试获取所有任务日志 ===")
    
    url = f"{BASE_URL}/api/tasks/logs"
    
    try:
        response = requests.get(url)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"总任务数: {result['total_tasks']}")
        
        for task in result['tasks']:
            print(f"任务ID: {task['task_id']}")
            print(f"类型: {task['type']}")
            print(f"状态: {task['status']}")
            print(f"消息: {task['message']}")
            print(f"创建时间: {task['created_at']}")
            print("---")
            
    except Exception as e:
        print(f"请求失败: {e}")

def test_get_youtube_task_logs():
    """测试获取YouTube任务日志"""
    print("\n=== 测试获取YouTube任务日志 ===")
    
    # 获取所有任务，然后过滤YouTube任务
    url = f"{BASE_URL}/api/tasks/logs"
    try:
        response = requests.get(url)
        print(f"状态码: {response.status_code}")
        result = response.json()
        
        youtube_tasks = [task for task in result['tasks'] if task['type'] == 'youtube_download']
        print(f"YouTube任务数: {len(youtube_tasks)}")
        
        for task in youtube_tasks:
            print(f"任务ID: {task['task_id']}")
            print(f"状态: {task['status']}")
            print(f"消息: {task['message']}")
            print(f"创建时间: {task['created_at']}")
            print("---")
            
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    print("开始测试YouTube下载接口...")
    
    # 测试YouTube下载并上传到平台接口
    test_youtube_download_with_platforms()
    
    # 等待一段时间让任务处理
    print("\n等待任务处理...")
    time.sleep(5)
    
    # 测试日志查询接口
    test_get_all_task_logs()
    test_get_youtube_task_logs()
    
    print("\n测试完成！")
    print("\n总结：")
    print("- 正确的YouTube下载接口: POST /api/youtube/download")
    print("- 支持基本下载和平台上传功能")
    print("- 支持的接口：")
    print("  * POST /api/youtube/download - YouTube视频下载")
    print("  * GET /api/task/{task_id} - 查询任务状态")
    print("  * GET /api/tasks/logs - 查看所有任务日志") 