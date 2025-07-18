#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试两个独立的任务队列：toutiao_task_queue 和 youtube_task_queue
"""

import requests
import json
import time

# API基础URL
BASE_URL = "http://localhost:8000"

def test_toutiao_queue():
    """测试头条任务队列"""
    print("=== 测试头条任务队列 ===")
    
    url = f"{BASE_URL}/api/toutiao/forward"
    data = {
        "urls": ["https://juejin.cn/post/7509755785611952180"],
        "save_file": False,
        "account_file": "cookiesFile/toutiao_cookie.json",
        "use_ai": False,
        "default_tags": ["AI", "互联网", "自动化"]
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        
        if response.status_code == 200:
            task_id = response.json()["task_id"]
            print(f"头条任务ID: {task_id}")
            
            # 查询任务状态
            time.sleep(2)
            status_url = f"{BASE_URL}/api/task/{task_id}"
            status_response = requests.get(status_url)
            print(f"头条任务状态: {status_response.json()}")
            
    except Exception as e:
        print(f"头条请求失败: {e}")

def test_youtube_queue():
    """测试YouTube任务队列"""
    print("\n=== 测试YouTube任务队列 ===")
    
    url = f"{BASE_URL}/api/youtube/download"
    data = {
        "url": ["https://www.youtube.com/watch?v=TyrCvZlhF68"],
        "quality": "best",
        "output_dir": "videos"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        
        if response.status_code == 200:
            task_id = response.json()["task_id"]
            print(f"YouTube任务ID: {task_id}")
            
            # 查询任务状态
            time.sleep(2)
            status_url = f"{BASE_URL}/api/task/{task_id}"
            status_response = requests.get(status_url)
            print(f"YouTube任务状态: {status_response.json()}")
            
    except Exception as e:
        print(f"YouTube请求失败: {e}")

def test_queue_logs():
    """测试队列日志查询"""
    print("\n=== 测试队列日志查询 ===")
    
    # 查询所有任务日志
    url = f"{BASE_URL}/api/tasks/logs"
    try:
        response = requests.get(url)
        print(f"所有任务日志状态码: {response.status_code}")
        result = response.json()
        print(f"总任务数: {result['total_tasks']}")
        
        # 统计各类型任务数量
        toutiao_count = 0
        youtube_count = 0
        
        for task in result['tasks']:
            task_type = task['type']
            if task_type == 'toutiao_forward':
                toutiao_count += 1
            elif task_type == 'youtube_download':
                youtube_count += 1
        
        print(f"头条任务数: {toutiao_count}")
        print(f"YouTube任务数: {youtube_count}")
        
    except Exception as e:
        print(f"查询任务日志失败: {e}")



if __name__ == "__main__":
    print("开始测试两个独立的任务队列...")
    
    # 测试头条任务队列
    test_toutiao_queue()
    
    # 测试YouTube任务队列
    test_youtube_queue()
    
    # 等待一段时间让任务处理
    print("\n等待任务处理...")
    time.sleep(5)
    
    # 测试队列日志查询
    test_queue_logs()
    
    print("\n测试完成！")
    print("\n总结：")
    print("- toutiao_task_queue: 处理头条文章转发任务")
    print("- youtube_task_queue: 处理YouTube视频下载任务")
    print("- 两个队列完全独立，互不干扰")
    print("- 支持的接口：")
    print("  * POST /api/toutiao/forward - 头条文章转发")
    print("  * POST /api/youtube/download - YouTube视频下载")
    print("  * GET /api/task/{task_id} - 查询任务状态")
    print("  * GET /api/tasks/logs - 查看所有任务日志") 