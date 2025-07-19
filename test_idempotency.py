#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
幂等性功能测试脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from utils.db_utils import db_manager


async def test_idempotency():
    """测试幂等性功能"""
    print("🧪 开始测试幂等性功能...")
    
    # 测试数据
    test_urls = [
        "https://www.youtube.com/watch?v=test1",
        "https://www.youtube.com/watch?v=test2",
        "https://juejin.cn/post/test1",
        "https://juejin.cn/post/test2"
    ]
    
    test_task_id = "test-task-123"
    
    print("\n1. 测试URL状态检查...")
    for url in test_urls:
        type_name = "youtube" if "youtube.com" in url else "juejin"
        is_processed = db_manager.is_url_processed(url, type_name)
        print(f"   URL: {url} (type: {type_name}) -> 已处理: {is_processed}")
    
    print("\n2. 测试标记URL为已处理...")
    for url in test_urls:
        type_name = "youtube" if "youtube.com" in url else "juejin"
        success = db_manager.mark_url_processed(url, type_name, test_task_id)
        print(f"   标记 {url} -> 成功: {success}")
    
    print("\n3. 再次检查URL状态...")
    for url in test_urls:
        type_name = "youtube" if "youtube.com" in url else "juejin"
        is_processed = db_manager.is_url_processed(url, type_name)
        print(f"   URL: {url} (type: {type_name}) -> 已处理: {is_processed}")
    
    print("\n4. 测试获取已处理URL列表...")
    youtube_urls = db_manager.get_processed_urls("youtube")
    juejin_urls = db_manager.get_processed_urls("juejin")
    all_urls = db_manager.get_processed_urls()
    
    print(f"   YouTube URL数量: {len(youtube_urls)}")
    print(f"   掘金 URL数量: {len(juejin_urls)}")
    print(f"   总URL数量: {len(all_urls)}")
    
    print("\n5. 测试统计信息...")
    stats = db_manager.get_processing_stats()
    print(f"   总记录数: {stats.get('total_count', 0)}")
    print(f"   类型统计: {stats.get('type_stats', {})}")
    print(f"   今日新增: {stats.get('today_count', 0)}")
    
    print("\n✅ 幂等性功能测试完成！")


if __name__ == "__main__":
    asyncio.run(test_idempotency()) 