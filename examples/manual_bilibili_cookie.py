#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import uuid
from pathlib import Path

# 添加父目录到模块搜索路径
sys.path.append(str(Path(__file__).parent.parent))

from conf import BASE_DIR

def create_bilibili_cookie_manually():
    """手动创建B站cookie文件"""
    print("🎬 B站Cookie手动配置工具")
    print("=" * 50)
    
    print("请按照以下步骤获取B站Cookie：")
    print("1. 打开浏览器，访问 https://www.bilibili.com")
    print("2. 登录您的B站账号")
    print("3. 按F12打开开发者工具，切换到'应用程序'(Application)标签")
    print("4. 在左侧找到'存储' -> 'Cookie' -> 'https://www.bilibili.com'")
    print("5. 找到以下关键cookie并复制其值：")
    print()
    
    # 收集必要的cookie
    cookies = {}
    required_cookies = ["SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5"]
    
    for cookie_name in required_cookies:
        while True:
            value = input(f"请输入 {cookie_name} 的值: ").strip()
            if value:
                cookies[cookie_name] = value
                break
            else:
                print("❌ 值不能为空，请重新输入")
    
    # 构建cookie数据
    cookie_data = build_cookie_data(cookies)
    
    # 保存cookie文件
    cookie_filename = f"{uuid.uuid4()}.json"
    cookie_path = Path(BASE_DIR / "cookiesFile" / cookie_filename)
    
    with open(cookie_path, 'w', encoding='utf-8') as f:
        json.dump(cookie_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ B站Cookie文件创建成功: {cookie_filename}")
    print(f"文件路径: {cookie_path}")
    print("\n现在可以运行以下命令进行B站视频上传：")
    print("python batch_upload_by_date.py --platform bilibili --date 2025-06-29 --no-schedule")
    
    return True

def build_cookie_data(cookies):
    """构建cookie数据"""
    # 构建标准cookie格式
    standard_cookies = []
    cookie_info = {"cookies": []}
    
    for name, value in cookies.items():
        cookie_obj = {
            'name': name,
            'value': value,
            'domain': '.bilibili.com',
            'path': '/',
            'expires': -1,
            'httpOnly': False,
            'secure': False,
            'sameSite': 'Lax'
        }
        
        standard_cookies.append(cookie_obj)
        cookie_info["cookies"].append(cookie_obj)
    
    return {
        'cookies': standard_cookies,
        'origins': [],
        'cookie_info': cookie_info,
        'token_info': {},
        'cookie_dict': cookies
    }

if __name__ == '__main__':
    create_bilibili_cookie_manually() 