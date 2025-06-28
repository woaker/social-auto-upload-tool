#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音上传环境配置
自动检测运行环境并配置相应的浏览器参数
"""

import os
import platform

def detect_environment():
    """检测运行环境"""
    # 检查是否有DISPLAY环境变量（Linux图形界面）
    has_display = os.environ.get('DISPLAY') is not None
    
    # 检查是否在SSH会话中
    is_ssh = os.environ.get('SSH_CLIENT') is not None or os.environ.get('SSH_TTY') is not None
    
    # 检查操作系统
    system = platform.system()
    
    # 云服务器通常的特征
    is_cloud = any([
        is_ssh,
        not has_display,
        os.path.exists('/sys/hypervisor'),  # 虚拟机
        'ec2' in platform.node().lower(),   # AWS EC2
        'cloud' in platform.node().lower()  # 其他云服务
    ])
    
    return {
        'is_cloud': is_cloud,
        'has_display': has_display,
        'is_ssh': is_ssh,
        'system': system
    }

def get_browser_config(force_headless=None):
    """获取浏览器配置"""
    env = detect_environment()
    
    # 如果强制指定headless模式
    if force_headless is not None:
        headless = force_headless
    else:
        # 云服务器或无显示环境自动使用无头模式
        headless = env['is_cloud'] or not env['has_display']
    
    # 基础配置
    config = {
        "headless": headless,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--exclude-switches=enable-automation",
            "--disable-extensions-except=",
            "--disable-extensions",
            "--no-sandbox",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-dev-shm-usage",
            "--disable-background-timer-throttling", 
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding"
        ]
    }
    
    # 云服务器额外配置
    if env['is_cloud']:
        config["args"].extend([
            "--disable-gpu",
            "--disable-software-rasterizer", 
            "--disable-gpu-sandbox",
            "--no-zygote",
            "--single-process"  # 可选：单进程模式
        ])
    
    return config, env

def get_context_config():
    """获取浏览器上下文配置"""
    return {
        "user_agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.6533.120 Safari/537.36',
        "viewport": {"width": 1920, "height": 1080},
        "extra_http_headers": {
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    }

def get_anti_detection_script():
    """获取反检测JavaScript脚本"""
    return """
        // 隐藏webdriver标识
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        
        // 伪造插件信息
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        
        // 伪造语言信息
        Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
        
        // 添加chrome对象
        window.chrome = {runtime: {}};
        
        // 伪造权限API
        Object.defineProperty(navigator, 'permissions', {
            get: () => ({query: () => Promise.resolve({state: 'granted'})})
        });
        
        // 伪造硬件并发
        Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4});
        
        // 伪造平台信息
        Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        
        // 删除自动化相关属性
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    """

def print_environment_info():
    """打印环境信息"""
    browser_config, env = get_browser_config()
    
    print("🌍 运行环境检测:")
    print(f"   操作系统: {env['system']}")
    print(f"   云服务器环境: {'✅ 是' if env['is_cloud'] else '❌ 否'}")
    print(f"   图形界面: {'✅ 有' if env['has_display'] else '❌ 无'}")
    print(f"   SSH连接: {'✅ 是' if env['is_ssh'] else '❌ 否'}")
    print(f"   浏览器模式: {'🔒 无头模式' if browser_config['headless'] else '🖥️  有头模式'}")

if __name__ == "__main__":
    print_environment_info() 