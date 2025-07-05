#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云服务器版本的抖音cookie获取脚本
使用selenium + undetected_chromedriver
"""

import json
import time
import qrcode
import os
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

def get_douyin_cookie_cloud():
    """使用selenium获取抖音cookie"""
    
    # 创建保存目录
    cookies_dir = Path("./cookiesFile")
    cookies_dir.mkdir(exist_ok=True)
    
    cookie_file = cookies_dir / "douyin_account.json"
    
    # 确保DISPLAY环境变量设置正确
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":99"
    
    # 配置Chrome选项
    options = uc.ChromeOptions()
    
    # 基础配置
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--headless=new')  # 使用新的headless模式
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-dev-tools')
    options.add_argument('--no-first-run')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    options.add_argument('--lang=zh-CN')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # 性能优化
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-smooth-scrolling')
    options.add_argument('--disable-javascript-harmony-shipping')
    options.add_argument('--disable-features=NetworkService')
    options.add_argument('--force-color-profile=srgb')
    options.add_argument('--disable-accelerated-2d-canvas')
    options.add_argument('--disable-accelerated-video-decode')
    options.add_argument('--disable-web-security')
    
    # 内存优化
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-backing-store-limit')
    options.add_argument('--memory-pressure-off')
    
    # 设置二进制文件路径
    options.binary_location = "/usr/bin/google-chrome-stable"
    
    driver = None
    try:
        print("🚀 启动浏览器...")
        print("Chrome路径:", options.binary_location)
        print("DISPLAY:", os.environ.get("DISPLAY"))
        print("Python版本:", sys.version)
        
        # 增加超时设置
        uc.DEFAULT_CONNECTION_TIMEOUT = 300
        
        # 使用自定义的ChromeDriver路径
        driver = uc.Chrome(
            options=options,
            driver_executable_path="/usr/bin/chromedriver",
            browser_executable_path="/usr/bin/google-chrome-stable",
            version_main=138,  # 更新为当前Chrome版本
            command_executor_timeout=300,
            page_load_timeout=300,
            service_args=['--verbose'],  # 添加详细日志
            enable_cdp_events=True,  # 启用CDP事件
            debug=True  # 启用调试模式
        )
        
        # 设置窗口大小
        driver.set_window_size(1920, 1080)
        driver.set_page_load_timeout(300)
        driver.set_script_timeout(300)
        
        # 设置等待
        wait = WebDriverWait(driver, 120)
        
        print("🌐 访问抖音创作者中心...")
        max_retries = 3
        success = False
        
        for retry in range(max_retries):
            try:
                print(f"尝试访问 ({retry + 1}/{max_retries})...")
                driver.get('https://creator.douyin.com/')
                success = True
                break
            except Exception as e:
                print(f"访问失败: {e}")
                if retry < max_retries - 1:
                    print("等待10秒后重试...")
                    time.sleep(10)
                else:
                    raise
        
        if not success:
            raise Exception("无法访问抖音创作者中心")
        
        print("✅ 页面加载成功")
        time.sleep(5)  # 等待页面加载
        
        # 保存页面截图
        driver.save_screenshot('douyin_login_page.png')
        print("📸 已保存登录页面截图")
        
        # 打印页面标题和URL
        print(f"页面标题: {driver.title}")
        print(f"当前URL: {driver.current_url}")
        
        # 等待二维码出现
        print("⏳ 等待二维码加载...")
        qr_selectors = [
            '.semi-modal-content img',
            'img[src*="qrcode"]',
            'img[class*="qrcode"]',
            'img[alt*="qrcode"]',
            '.login-qrcode img',
            '//img[contains(@src, "qrcode")]'
        ]
        
        qr_img = None
        for selector in qr_selectors:
            try:
                if '//' in selector:
                    qr_img = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                else:
                    qr_img = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                if qr_img:
                    print(f"✅ 找到二维码元素: {selector}")
                    break
            except Exception as e:
                print(f"选择器 {selector} 未找到: {e}")
                continue
        
        if not qr_img:
            print("❌ 未找到二维码元素，尝试其他登录方式...")
            try:
                login_buttons = [
                    "//*[contains(text(), '扫码登录')]",
                    "//button[contains(., '扫码登录')]",
                    "//div[contains(., '扫码登录')][@role='button']"
                ]
                
                for button in login_buttons:
                    try:
                        scan_button = driver.find_element(By.XPATH, button)
                        scan_button.click()
                        print(f"✅ 点击了登录按钮: {button}")
                        time.sleep(3)
                        break
                    except Exception as e:
                        print(f"按钮 {button} 未找到: {e}")
                        continue
                
                # 重新尝试获取二维码
                for selector in qr_selectors:
                    try:
                        if '//' in selector:
                            qr_img = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                        else:
                            qr_img = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        if qr_img:
                            print(f"✅ 点击扫码登录后找到二维码元素: {selector}")
                            break
                    except Exception as e:
                        print(f"选择器 {selector} 未找到: {e}")
                        continue
            except Exception as e:
                print(f"❌ 无法切换到扫码登录: {e}")
        
        if qr_img:
            # 获取登录链接
            try:
                # 查找登录链接元素
                login_url = None
                qr_element = driver.find_element(By.CSS_SELECTOR, 'img[class*="qrcode"]')
                if qr_element:
                    # 获取父元素中的链接
                    parent_element = qr_element.find_element(By.XPATH, '..')
                    login_url = parent_element.get_attribute('href')
                    if not login_url:
                        # 如果父元素没有链接，尝试获取兄弟元素的链接
                        sibling_link = driver.find_element(By.CSS_SELECTOR, 'a[href*="scan/login"]')
                        if sibling_link:
                            login_url = sibling_link.get_attribute('href')
                
                if login_url:
                    print("\n✨ 请按以下步骤完成登录：")
                    print("1. 复制下面的链接")
                    print("2. 在手机抖音APP中打开")
                    print("3. 完成授权登录")
                    print("\n📱 登录链接：")
                    print(login_url)
                    print("\n⏳ 等待登录成功...")
                    print("   请在手机上完成授权")
                else:
                    print("❌ 无法获取登录链接，请检查网页是否正常加载")
            except Exception as e:
                print(f"❌ 获取登录链接时出错: {e}")
        else:
            # 保存页面源码以供调试
            with open('page_source.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("📄 已保存页面源码到 page_source.html")
            raise Exception("无法获取登录二维码")
        
        # 等待登录成功
        print("⏳ 等待登录成功...")
        print("   请使用抖音APP扫描二维码完成登录")
        
        success = False
        max_wait = 300  # 最多等待5分钟
        wait_time = 0
        
        while wait_time < max_wait:
            try:
                # 保存当前页面截图
                if wait_time % 30 == 0:
                    driver.save_screenshot(f'douyin_login_progress_{wait_time}.png')
                    print(f"当前URL: {driver.current_url}")
                
                # 检查是否登录成功
                current_url = driver.current_url
                if 'creator.douyin.com' in current_url and 'login' not in current_url:
                    # 检查是否有用户相关元素
                    user_elements = driver.find_elements(By.CSS_SELECTOR, '.avatar, .username, .user-info')
                    if user_elements:
                        success = True
                        break
                
                time.sleep(2)
                wait_time += 2
                
                if wait_time % 30 == 0:
                    print(f"   仍在等待登录... ({wait_time}/{max_wait}秒)")
                    
            except Exception as e:
                print(f"   检查登录状态时出错: {e}")
                time.sleep(2)
                wait_time += 2
        
        if success:
            print("✅ 登录成功！正在保存cookie...")
            
            # 获取所有cookie
            cookies = driver.get_cookies()
            
            # 保存cookie到文件
            cookie_data = {
                'cookies': cookies,
                'user_agent': driver.execute_script('return navigator.userAgent'),
                'timestamp': time.time()
            }
            
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Cookie已保存到: {cookie_file}")
            print("🎉 抖音账号配置完成！")
            return True
            
        else:
            print("❌ 登录超时，请重新运行脚本")
            return False
            
    except Exception as e:
        print(f"❌ 获取cookie失败: {e}")
        if driver:
            try:
                driver.save_screenshot('douyin_error.png')
                print("📸 已保存错误页面截图到 douyin_error.png")
                with open('douyin_error.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                print("📄 已保存错误页面源码到 douyin_error.html")
            except:
                pass
        return False
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == '__main__':
    print("🤖 抖音Cookie获取工具 (云服务器版)")
    print("=" * 50)
    
    # 检查环境
    print("环境检查:")
    print(f"DISPLAY: {os.environ.get('DISPLAY', 'Not set')}")
    print(f"Chrome路径: {'/usr/bin/google-chrome-stable'}")
    print(f"ChromeDriver路径: {'/usr/bin/chromedriver'}")
    
    result = get_douyin_cookie_cloud()
    
    if result:
        print("\n✅ 设置完成！现在可以运行批量上传命令:")
        print("python3 batch_upload_by_date.py --platform douyin --date 2025-07-03 --no-schedule")
    else:
        print("\n❌ 设置失败，请检查网络连接后重试") 