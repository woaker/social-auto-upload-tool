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
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--start-maximized')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--hide-scrollbars')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--lang=zh-CN')
    options.add_argument('--remote-debugging-port=9222')  # 添加调试端口
    
    # 设置二进制文件路径
    options.binary_location = "/usr/bin/google-chrome-stable"
    
    try:
        print("🚀 启动浏览器...")
        print("Chrome路径:", options.binary_location)
        print("DISPLAY:", os.environ.get("DISPLAY"))
        
        # 使用自定义的ChromeDriver路径
        driver = uc.Chrome(
            options=options,
            driver_executable_path="/usr/bin/chromedriver",
            browser_executable_path="/usr/bin/google-chrome-stable",
            version_main=120  # 指定Chrome主版本号
        )
        
        driver.set_window_size(1920, 1080)
        
        # 设置等待
        wait = WebDriverWait(driver, 30)
        
        print("🌐 访问抖音创作者中心...")
        driver.get('https://creator.douyin.com/')
        time.sleep(3)
        
        # 保存页面截图
        driver.save_screenshot('douyin_login_page.png')
        print("📸 已保存登录页面截图")
        
        # 等待二维码出现
        print("⏳ 等待二维码加载...")
        qr_selectors = [
            '.semi-modal-content img',
            'img[src*="qrcode"]',
            'img[class*="qrcode"]',
            'img[alt*="qrcode"]',
            '.login-qrcode img'
        ]
        
        qr_img = None
        for selector in qr_selectors:
            try:
                qr_img = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                if qr_img:
                    print(f"✅ 找到二维码元素: {selector}")
                    break
            except:
                continue
        
        if not qr_img:
            print("❌ 未找到二维码元素，尝试其他登录方式...")
            try:
                scan_button = driver.find_element(By.XPATH, "//*[contains(text(), '扫码登录')]")
                scan_button.click()
                time.sleep(2)
                
                # 重新尝试获取二维码
                for selector in qr_selectors:
                    try:
                        qr_img = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        if qr_img:
                            print(f"✅ 点击扫码登录后找到二维码元素: {selector}")
                            break
                    except:
                        continue
            except:
                print("❌ 无法切换到扫码登录")
        
        if qr_img:
            qr_src = qr_img.get_attribute('src')
            print("📱 请使用抖音APP扫描以下二维码登录:")
            print(f"   二维码链接: {qr_src}")
            
            # 生成二维码到终端
            try:
                qr = qrcode.QRCode()
                qr.add_data(qr_src)
                qr.print_ascii()
            except Exception as e:
                print(f"   无法显示二维码: {e}")
                print("   请访问上面的链接")
        else:
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
        # 保存错误页面截图和源码
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