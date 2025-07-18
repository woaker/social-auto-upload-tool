#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试YouTube下载类型1和类型2接口
"""

import requests
import json
import time

# API基础URL
BASE_URL = "http://localhost:8000"

def test_youtube_download_type1():
    """测试YouTube下载类型1接口"""
    print("=== 测试YouTube下载类型1接口 ===")
    
    url = f"{BASE_URL}/api/youtube/download/type1"
    data = {
        "url": ["https://www.youtube.com/watch?v=TyrCvZlhF68"],
        "quality": "best",
        "output_dir": "videos",
        "download_type": "type1"
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

def test_youtube_download_type2():
    """测试YouTube下载类型2接口"""
    print("\n=== 测试YouTube下载类型2接口 ===")
    
    url = f"{BASE_URL}/api/youtube/download/type2"
    data = {
        "url": ["https://www.youtube.com/watch?v=-K0fODITV2c"],
        "quality": "best",
        "output_dir": "videos",
        "download_type": "type2"
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

def test_get_task_logs_by_type():
    """测试按类型获取任务日志"""
    print("\n=== 测试按类型获取任务日志 ===")
    
    # 测试类型1
    url1 = f"{BASE_URL}/api/tasks/logs/youtube_download_type1"
    try:
        response = requests.get(url1)
        print(f"类型1任务状态码: {response.status_code}")
        result = response.json()
        print(f"类型1任务数: {result['total_tasks']}")
    except Exception as e:
        print(f"类型1请求失败: {e}")
    
    # 测试类型2
    url2 = f"{BASE_URL}/api/tasks/logs/youtube_download_type2"
    try:
        response = requests.get(url2)
        print(f"类型2任务状态码: {response.status_code}")
        result = response.json()
        print(f"类型2任务数: {result['total_tasks']}")
    except Exception as e:
        print(f"类型2请求失败: {e}")

if __name__ == "__main__":
    print("开始测试YouTube下载接口...")
    
    # 测试两个不同的下载接口
    test_youtube_download_type1()
    test_youtube_download_type2()
    
    # 等待一段时间让任务处理
    print("\n等待任务处理...")
    time.sleep(5)
    
    # 测试日志查询接口
    test_get_all_task_logs()
    test_get_task_logs_by_type()
    
    print("\n测试完成！") 