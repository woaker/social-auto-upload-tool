#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
import socket
from datetime import datetime
import subprocess
import sys

def test_network_connectivity():
    """测试基础网络连接"""
    print("\n🌐 测试基础网络连接...")
    
    # 测试DNS解析
    try:
        ip = socket.gethostbyname('www.douyin.com')
        print(f"✅ DNS解析成功: www.douyin.com -> {ip}")
    except Exception as e:
        print(f"❌ DNS解析失败: {e}")
        return False
    
    # 测试HTTP连接
    try:
        response = requests.get('https://www.douyin.com', timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        print(f"✅ HTTP连接成功: 状态码 {response.status_code}")
        return True
    except requests.exceptions.Timeout:
        print("❌ HTTP连接超时")
        return False
    except Exception as e:
        print(f"❌ HTTP连接失败: {e}")
        return False

def test_creator_page():
    """测试创作者页面连接"""
    print("\n🎬 测试创作者页面...")
    
    try:
        response = requests.get('https://creator.douyin.com', timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        print(f"✅ 创作者页面访问成功: 状态码 {response.status_code}")
        
        # 检查是否被重定向到登录页
        if 'login' in response.url.lower():
            print("⚠️  页面被重定向到登录页，可能需要重新获取cookie")
            return False
        return True
    except requests.exceptions.Timeout:
        print("❌ 创作者页面访问超时")
        return False
    except Exception as e:
        print(f"❌ 创作者页面访问失败: {e}")
        return False

def check_cookie_file():
    """检查cookie文件"""
    print("\n🍪 检查Cookie文件...")
    
    import glob
    import os
    
    # 查找cookie文件
    cookie_files = glob.glob("*.json")
    douyin_cookies = [f for f in cookie_files if len(f.split('-')) >= 5]
    
    if not douyin_cookies:
        print("❌ 未找到抖音cookie文件")
        return None
    
    cookie_file = douyin_cookies[0]
    print(f"✅ 找到cookie文件: {cookie_file}")
    
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookie_data = json.load(f)
        
        print(f"✅ Cookie文件大小: {len(json.dumps(cookie_data))} 字节")
        
        # 检查文件修改时间
        mtime = os.path.getmtime(cookie_file)
        mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        hours_old = (time.time() - mtime) / 3600
        
        print(f"📅 Cookie创建时间: {mtime_str}")
        print(f"⏰ Cookie年龄: {hours_old:.1f} 小时")
        
        if hours_old > 24:
            print("⚠️  Cookie可能已过期（超过24小时）")
        
        return cookie_file
    except Exception as e:
        print(f"❌ 读取Cookie文件失败: {e}")
        return None

def test_ping():
    """测试ping连接"""
    print("\n🏓 测试网络延迟...")
    
    try:
        result = subprocess.run(['ping', '-c', '3', 'www.douyin.com'], 
                              capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'avg' in line and 'ms' in line:
                    print(f"✅ 网络延迟: {line.split('/')[-3]}ms")
                    break
            return True
        else:
            print("❌ Ping测试失败")
            return False
    except Exception as e:
        print(f"❌ Ping测试异常: {e}")
        return False

def get_server_info():
    """获取服务器信息"""
    print("\n🖥️  服务器信息...")
    
    try:
        # 获取外网IP
        response = requests.get('https://api.ipify.org', timeout=10)
        external_ip = response.text.strip()
        print(f"🌍 外网IP: {external_ip}")
        
        # 获取地理位置信息
        response = requests.get(f'https://ipapi.co/{external_ip}/json/', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"📍 地理位置: {data.get('country_name', 'Unknown')} - {data.get('city', 'Unknown')}")
            print(f"🏢 ISP: {data.get('org', 'Unknown')}")
    except Exception as e:
        print(f"❌ 获取服务器信息失败: {e}")

def main():
    print("🔍 抖音连接详细诊断工具")
    print("=" * 50)
    
    # 获取服务器信息
    get_server_info()
    
    # 测试基础网络
    network_ok = test_network_connectivity()
    
    # 测试ping
    ping_ok = test_ping()
    
    # 测试创作者页面
    creator_ok = test_creator_page()
    
    # 检查cookie
    cookie_file = check_cookie_file()
    
    print("\n" + "=" * 50)
    print("📊 诊断结果汇总:")
    print(f"🌐 基础网络连接: {'✅ 正常' if network_ok else '❌ 异常'}")
    print(f"🏓 网络延迟: {'✅ 正常' if ping_ok else '❌ 异常'}")
    print(f"🎬 创作者页面: {'✅ 可访问' if creator_ok else '❌ 不可访问'}")
    print(f"🍪 Cookie文件: {'✅ 存在' if cookie_file else '❌ 缺失'}")
    
    print("\n🔧 建议解决方案:")
    if not network_ok:
        print("1. 检查服务器网络配置和防火墙设置")
    
    if not creator_ok:
        print("2. 抖音创作者页面可能限制了云服务器IP访问")
        print("   - 可以尝试使用代理服务器")
        print("   - 或者在本地获取cookie后上传")
    
    if not cookie_file:
        print("3. 需要重新获取抖音cookie")
    else:
        print("3. Cookie文件存在，但可能已过期，建议重新获取")
    
    print("\n💡 推荐操作:")
    print("1. 在本地重新获取新的cookie")
    print("2. 将新cookie上传到服务器")
    print("3. 如果问题持续，考虑配置代理服务器")

if __name__ == "__main__":
    main() 