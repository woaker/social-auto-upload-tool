# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Page
import os
import asyncio
import time
from playwright.sync_api import sync_playwright
import json
import re

from config import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.log import douyin_logger
from douyin_config import get_browser_config, get_context_config, get_anti_detection_script


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        try:
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=5000)
        except:
            print("[+] 等待5秒 cookie 失效")
            await context.close()
            await browser.close()
            return False
        # 2024.06.17 抖音创作者中心改版
        if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
            print("[+] 等待5秒 cookie 失效")
            return False
        else:
            print("[+] cookie 有效")
            return True


async def douyin_setup(account_file, handle=False):
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # Todo alert message
            return False
        douyin_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await douyin_cookie_gen(account_file)
    return True


async def douyin_cookie_gen(account_file):
    async with async_playwright() as playwright:
        options = {
            'headless': False
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.douyin.com/")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


class DouYinVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, thumbnail_path=None, proxy_setting=None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.thumbnail_path = thumbnail_path
        self.default_location = "北京市"  # 默认地理位置
        self.proxy_setting = proxy_setting

    async def set_schedule_time_douyin(self, page, publish_date):
        # 选择包含特定文本内容的 label 元素
        label_element = page.locator("[class^='radio']:has-text('定时发布')")
        # 在选中的 label 元素下点击 checkbox
        await label_element.click()
        await asyncio.sleep(1)
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")

        await asyncio.sleep(1)
        await page.locator('.semi-input[placeholder="日期和时间"]').click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")

        await asyncio.sleep(1)

    async def handle_upload_error(self, page):
        douyin_logger.info('视频出错了，重新上传中')
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)

    async def upload(self, playwright: Playwright) -> None:
        # 使用增强版云服务器优化配置
        launch_options, env = get_browser_config()
        
        # 添加额外的稳定性配置
        launch_options["args"].extend([
            "--no-sandbox",  # 云服务器必需
            "--disable-dev-shm-usage",  # 云服务器必需
            "--disable-gpu",  # 云服务器必需
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-background-networking",
            "--disable-client-side-phishing-detection", 
            "--disable-sync",
            "--disable-translate",
            "--disable-ipc-flooding-protection",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
            # 添加新的优化参数
            "--disable-extensions",  # 禁用扩展
            "--disable-popup-blocking",  # 禁用弹窗拦截
            "--ignore-certificate-errors",  # 忽略证书错误
            "--no-zygote",  # 禁用zygote进程
            "--disable-setuid-sandbox",  # 禁用setuid沙箱
            "--disable-accelerated-2d-canvas",  # 禁用加速2D画布
            "--disable-accelerated-jpeg-decoding",  # 禁用加速JPEG解码
            "--disable-accelerated-video-decode",  # 禁用加速视频解码
            "--disable-gpu-sandbox",  # 禁用GPU沙箱
            "--disable-software-rasterizer",  # 禁用软件光栅化器
            "--force-gpu-mem-available-mb=1024",  # 强制GPU内存
            "--no-experiments",  # 禁用实验性功能
            "--disable-dev-tools",  # 禁用开发者工具
            "--disable-logging",  # 禁用日志
            "--disable-breakpad",  # 禁用崩溃报告
            "--disable-component-extensions-with-background-pages"  # 禁用带有后台页面的组件扩展
        ])
        
        if self.local_executable_path:
            launch_options["executable_path"] = self.local_executable_path
            
        if self.proxy_setting:
            launch_options["proxy"] = self.proxy_setting
            
        browser = None
        context = None
        page = None
        
        try:
            douyin_logger.info("🚀 启动浏览器...")
            browser = await playwright.chromium.launch(**launch_options)
            
            # 使用增强版上下文配置
            context_config = get_context_config()
            context_config["storage_state"] = f"{self.account_file}"
            context_config["viewport"] = {'width': 1920, 'height': 1080}
            context_config["user_agent"] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            
            douyin_logger.info("🔧 创建浏览器上下文...")
            context = await browser.new_context(**context_config)
            
            # 使用增强版反检测脚本
            await context.add_init_script(get_anti_detection_script())
            
            context = await set_init_script(context)

            # 创建一个新的页面
            douyin_logger.info("📄 创建新页面...")
            page = await context.new_page()
            
            # 添加页面级别的反检测
            await page.add_init_script("""
                // 额外的页面级反检测
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
                
                // 删除自动化相关属性
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                
                // 伪造更真实的navigator
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en-US', 'en'],
                    configurable: true
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                    configurable: true
                });
            """)
            
            # 访问指定的 URL
            douyin_logger.info("🌐 访问抖音创作者中心...")
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # 修改等待策略和超时时间
                    await page.goto("https://creator.douyin.com/creator-micro/content/upload", 
                                wait_until="domcontentloaded", timeout=120000)  # 增加到120秒并改用domcontentloaded
                    
                    # 等待页面加载完成的关键元素
                    try:
                        await page.wait_for_selector("input[type='file'], .upload-btn input, .semi-upload input", 
                                                 timeout=30000,
                                                 state="attached")
                        break
                    except Exception as e:
                        douyin_logger.warning(f"等待上传按钮超时，准备重试: {str(e)}")
                        raise e
                        
                except Exception as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        douyin_logger.error(f"访问抖音创作者中心失败: {str(e)}")
                        raise
                    douyin_logger.warning(f"第{retry_count}次重试访问抖音创作者中心...")
                    # 增加重试等待时间
                    await asyncio.sleep(10 * retry_count)  # 递增等待时间：10秒、20秒、30秒
            
            # 检查是否在登录页面
            if await page.get_by_text('手机号登录').count() > 0 or await page.get_by_text('扫码登录').count() > 0:
                # 保存错误截图
                await page.screenshot(path='douyin_error_screenshot.png')
                raise Exception("Cookie已失效，需要重新登录")
                    
            douyin_logger.info(f'[+]正在上传-------{os.path.basename(self.file_path)}')
            
            # 等待页面加载完成
            await asyncio.sleep(5)  # 额外等待5秒确保页面完全加载
            
            # 尝试多个可能的上传按钮选择器
            upload_button = None
            selectors = [
                "input[type='file']",
                "input[accept='video/*']",
                ".upload-btn input",
                ".semi-upload input",
                "div[class^='upload'] input[type='file']"
            ]
            
            for selector in selectors:
                try:
                    upload_button = await page.wait_for_selector(selector, timeout=20000, state="attached")
                    if upload_button:
                        douyin_logger.info(f"找到上传按钮: {selector}")
                        break
                except:
                    continue
            
            if not upload_button:
                # 保存错误截图
                await page.screenshot(path='douyin_error_screenshot.png')
                raise Exception("未找到上传按钮，请检查页面结构")
            
            # 上传文件
            await upload_button.set_input_files(self.file_path)

            # 等待页面跳转到指定的 URL 2025.01.08修改在原有基础上兼容两种页面
            while True:
                try:
                    # 尝试等待第一个 URL
                    await page.wait_for_url(
                        "https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page", timeout=3000)
                    douyin_logger.info("[+] 成功进入version_1发布页面!")
                    break  # 成功进入页面后跳出循环
                except Exception:
                    try:
                        # 如果第一个 URL 超时，再尝试等待第二个 URL
                        await page.wait_for_url(
                            "https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page",
                            timeout=3000)
                        douyin_logger.info("[+] 成功进入version_2发布页面!")

                        break  # 成功进入页面后跳出循环
                    except:
                        print("  [-] 超时未进入视频发布页面，重新尝试...")
                        await asyncio.sleep(0.5)  # 等待 0.5 秒后重新尝试
            # 填充标题和话题
            # 检查是否存在包含输入框的元素
            # 这里为了避免页面变化，故使用相对位置定位：作品标题父级右侧第一个元素的input子元素
            await asyncio.sleep(1)
            douyin_logger.info(f'  [-] 正在填充标题和话题...')
            title_container = page.get_by_text('作品标题').locator("..").locator("xpath=following-sibling::div[1]").locator("input")
            if await title_container.count():
                await title_container.fill(self.title[:30])
            else:
                titlecontainer = page.locator(".notranslate")
                await titlecontainer.click()
                await page.keyboard.press("Backspace")
                await page.keyboard.press("Control+KeyA")
                await page.keyboard.press("Delete")
                await page.keyboard.type(self.title)
                await page.keyboard.press("Enter")
            css_selector = ".zone-container"
            for index, tag in enumerate(self.tags, start=1):
                await page.type(css_selector, "#" + tag)
                await page.press(css_selector, "Space")
            douyin_logger.info(f'总共添加{len(self.tags)}个话题')

            while True:
                # 判断重新上传按钮是否存在，如果不存在，代表视频正在上传，则等待
                try:
                    #  新版：定位重新上传
                    number = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
                    if number > 0:
                        douyin_logger.success("  [-]视频上传完毕")
                        break
                    else:
                        douyin_logger.info("  [-] 正在上传视频中...")
                        await asyncio.sleep(2)

                        if await page.locator('div.progress-div > div:has-text("上传失败")').count():
                            douyin_logger.error("  [-] 发现上传出错了... 准备重试")
                            await self.handle_upload_error(page)
                except:
                    douyin_logger.info("  [-] 正在上传视频中...")
                    await asyncio.sleep(2)
            
            #上传视频封面
            await self.set_thumbnail(page, self.thumbnail_path)

            # 更换可见元素
            await self.set_location(page, self.default_location)

            # 頭條/西瓜 - 自动同步到头条
            await self.set_toutiao_sync(page)

            if self.publish_date != 0:
                await self.set_schedule_time_douyin(page, self.publish_date)

            # 判断视频是否发布成功
            while True:
                # 判断视频是否发布成功
                try:
                    publish_button = page.get_by_role('button', name="发布", exact=True)
                    if await publish_button.count():
                        await publish_button.click()
                    await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage**",
                                            timeout=3000)  # 如果自动跳转到作品页面，则代表发布成功
                    douyin_logger.success("  [-]视频发布成功")
                    break
                except:
                    douyin_logger.info("  [-] 视频正在发布中...")
                    await page.screenshot(full_page=True)
                    await asyncio.sleep(0.5)

            await context.storage_state(path=self.account_file)  # 保存cookie
            douyin_logger.success('  [-]cookie更新完毕！')
            await asyncio.sleep(2)  # 这里延迟是为了方便眼睛直观的观看
            
        except Exception as e:
            douyin_logger.error(f"❌ 上传过程中发生错误: {str(e)}")
            douyin_logger.error(f"  错误类型: {type(e).__name__}")
            
            # 尝试截图保存现场
            if page:
                try:
                    await page.screenshot(path="douyin_error_screenshot.png", full_page=True)
                    douyin_logger.info("📸 错误截图已保存: douyin_error_screenshot.png")
                except:
                    pass
            
            # 重新抛出异常
            raise e
        finally:
            # 确保资源正确清理
            try:
                if context:
                    await context.close()
                    douyin_logger.info("🔒 浏览器上下文已关闭")
            except:
                pass
            
            try:
                if browser:
                    await browser.close()
                    douyin_logger.info("🔒 浏览器已关闭")
            except:
                pass

    async def set_thumbnail(self, page: Page, thumbnail_path: str):
        if thumbnail_path:
            await page.click('text="选择封面"')
            await page.wait_for_selector("div.semi-modal-content:visible")
            await page.click('text="设置竖封面"')
            await page.wait_for_timeout(2000)  # 等待2秒
            # 定位到上传区域并点击
            await page.locator("div[class^='semi-upload upload'] >> input.semi-upload-hidden-input").set_input_files(thumbnail_path)
            await page.wait_for_timeout(2000)  # 等待2秒
            await page.locator("div[class^='extractFooter'] button:visible:has-text('完成')").click()
            # finish_confirm_element = page.locator("div[class^='confirmBtn'] >> div:has-text('完成')")
            # if await finish_confirm_element.count():
            #     await finish_confirm_element.click()
            # await page.locator("div[class^='footer'] button:has-text('完成')").click()

    async def set_location(self, page: Page, location: str = "北京市"):
        """设置地理位置，如果失败则跳过"""
        try:
            douyin_logger.info(f"  [-] 正在设置地理位置: {location}")
            
            # 检查地理位置选择器是否存在
            location_selector = 'div.semi-select span:has-text("输入地理位置")'
            location_element = page.locator(location_selector)
            
            # 等待元素出现，设置较短的超时时间
            await location_element.wait_for(timeout=10000)
            
            # 点击地理位置输入框
            await location_element.click()
            await page.keyboard.press("Backspace")
            await page.wait_for_timeout(2000)
            
            # 输入地理位置
            await page.keyboard.type(location)
            
            # 等待下拉选项出现
            await page.wait_for_selector('div[role="listbox"] [role="option"]', timeout=5000)
            
            # 选择第一个选项
            await page.locator('div[role="listbox"] [role="option"]').first.click()
            
            douyin_logger.success(f"  [-] 地理位置设置成功: {location}")
            
        except Exception as e:
            douyin_logger.warning(f"  [-] 地理位置设置失败，跳过此步骤: {str(e)}")
            douyin_logger.info("  [-] 地理位置不是必需的，继续发布流程...")
            # 不抛出异常，继续执行后续流程

    async def set_toutiao_sync(self, page: Page):
        """设置自动同步到头条，尝试多种选择器"""
        douyin_logger.info('  [-] 正在设置自动同步到头条...')
        
        # 多种可能的选择器
        selectors = [
            # 原始选择器
            '[class^="info"] > [class^="first-part"] div div.semi-switch',
            # 更通用的选择器
            'div.semi-switch',
            # 通过文本查找
            'span:has-text("头条") + div .semi-switch',
            'span:has-text("今日头条") + div .semi-switch', 
            'span:has-text("西瓜视频") + div .semi-switch',
            # 通过类名查找
            'div[class*="third-part"] .semi-switch',
            'div[class*="platform"] .semi-switch',
            # xpath方式
            '//span[contains(text(), "头条") or contains(text(), "西瓜")]/following-sibling::div//div[contains(@class, "semi-switch")]',
            '//div[contains(@class, "semi-switch") and ./ancestor::*[contains(., "头条") or contains(., "西瓜")]]'
        ]
        
        try:
            # 等待页面加载完成
            await asyncio.sleep(2)
            
            # 截图用于调试
            douyin_logger.info('  [-] 截图保存当前页面状态...')
            await page.screenshot(path="douyin_toutiao_sync_debug.png", full_page=True)
            
            switch_found = False
            
            # 尝试每个选择器
            for i, selector in enumerate(selectors):
                try:
                    douyin_logger.info(f'  [-] 尝试选择器 {i+1}: {selector}')
                    
                    if selector.startswith('//'):
                        # xpath选择器
                        elements = await page.locator(f'xpath={selector}').all()
                    else:
                        # css选择器
                        elements = await page.locator(selector).all()
                    
                    if elements:
                        douyin_logger.info(f'  [-] 找到 {len(elements)} 个匹配的开关元素')
                        
                        for j, element in enumerate(elements):
                            try:
                                # 检查是否可见
                                is_visible = await element.is_visible()
                                if not is_visible:
                                    douyin_logger.info(f'  [-] 开关 {j+1} 不可见，跳过')
                                    continue
                                
                                # 获取开关状态
                                switch_class = await element.get_attribute('class')
                                is_checked = 'semi-switch-checked' in (switch_class or '')
                                
                                douyin_logger.info(f'  [-] 开关 {j+1} 状态: {"已开启" if is_checked else "未开启"}')
                                
                                # 如果未开启，则点击开启
                                if not is_checked:
                                    # 尝试点击开关本身
                                    try:
                                        await element.click()
                                        douyin_logger.success('  [-] 成功点击开关开启头条同步')
                                        switch_found = True
                                        break
                                    except:
                                        # 尝试点击内部的input元素
                                        try:
                                            input_element = element.locator('input.semi-switch-native-control')
                                            if await input_element.count():
                                                await input_element.click()
                                                douyin_logger.success('  [-] 成功通过input开启头条同步')
                                                switch_found = True
                                                break
                                        except:
                                            pass
                                else:
                                    douyin_logger.info('  [-] 头条同步已经开启')
                                    switch_found = True
                                    break
                                    
                            except Exception as e:
                                douyin_logger.warning(f'  [-] 处理开关 {j+1} 时出错: {e}')
                                continue
                        
                        if switch_found:
                            break
                            
                except Exception as e:
                    douyin_logger.warning(f'  [-] 选择器 {i+1} 失败: {e}')
                    continue
            
            if not switch_found:
                # 尝试通过文本内容查找
                douyin_logger.info('  [-] 尝试通过文本内容查找头条同步选项...')
                
                # 查找包含"头条"或"西瓜"的文本
                text_patterns = ["头条", "今日头条", "西瓜视频", "西瓜"]
                
                for pattern in text_patterns:
                    try:
                        text_elements = await page.get_by_text(pattern).all()
                        for text_element in text_elements:
                            try:
                                # 查找附近的开关
                                parent = text_element.locator('..')
                                switches = await parent.locator('.semi-switch').all()
                                
                                if switches:
                                    switch = switches[0]
                                    switch_class = await switch.get_attribute('class')
                                    is_checked = 'semi-switch-checked' in (switch_class or '')
                                    
                                    if not is_checked:
                                        await switch.click()
                                        douyin_logger.success(f'  [-] 通过文本"{pattern}"找到并开启头条同步')
                                        switch_found = True
                                        break
                                    else:
                                        douyin_logger.info(f'  [-] 通过文本"{pattern}"找到头条同步，已开启')
                                        switch_found = True
                                        break
                            except:
                                continue
                        
                        if switch_found:
                            break
                            
                    except:
                        continue
            
            if not switch_found:
                douyin_logger.warning('  [-] 未找到头条同步选项，可能页面结构已变化或账号不支持此功能')
                douyin_logger.info('  [-] 请手动检查页面是否有头条同步开关')
            else:
                # 等待一下确保设置生效
                await asyncio.sleep(1)
                douyin_logger.success('  [-] 头条同步设置完成')
                
        except Exception as e:
            douyin_logger.error(f'  [-] 设置头条同步时发生错误: {str(e)}')
            douyin_logger.info('  [-] 继续发布流程...')

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)


def load_cookies():
    """加载cookies"""
    try:
        # 尝试多个可能的cookie文件路径
        cookie_paths = [
            os.path.join('cookies', 'douyin_uploader', 'douyin_cookies.json'),
            os.path.join('cookiesFile', 'douyin_account.json'),
            'douyin_account.json'
        ]
        
        for cookie_file in cookie_paths:
            if os.path.exists(cookie_file):
                print(f"✅ 找到cookie文件: {cookie_file}")
                with open(cookie_file, 'r') as f:
                    data = json.load(f)
                    # 处理不同的cookie格式
                    if isinstance(data, dict) and 'cookies' in data:
                        return data['cookies']  # 返回cookies数组
                    elif isinstance(data, list):
                        return data  # 直接返回cookie数组
                    else:
                        print(f"❌ Cookie文件 {cookie_file} 格式不正确")
                        continue
                    
        print("❌ 未找到任何有效的cookie文件")
    except Exception as e:
        print(f"❌ 加载cookies失败: {str(e)}")
    return None

def save_cookies(cookies):
    """保存cookies"""
    try:
        cookie_data = {
            'cookies': cookies,
            'timestamp': time.time()
        }
        
        # 优先保存到标准位置
        cookie_dir = os.path.join('cookies', 'douyin_uploader')
        os.makedirs(cookie_dir, exist_ok=True)
        cookie_file = os.path.join(cookie_dir, 'douyin_cookies.json')
        
        with open(cookie_file, 'w') as f:
            json.dump(cookie_data, f, indent=2)
        print(f"✅ cookies已保存到: {cookie_file}")
        
        # 同时保存一份到cookiesFile目录
        alt_cookie_dir = 'cookiesFile'
        os.makedirs(alt_cookie_dir, exist_ok=True)
        alt_cookie_file = os.path.join(alt_cookie_dir, 'douyin_account.json')
        
        with open(alt_cookie_file, 'w') as f:
            json.dump(cookie_data, f, indent=2)
        print(f"✅ cookies已备份到: {alt_cookie_file}")
        
    except Exception as e:
        print(f"❌ 保存cookies失败: {str(e)}")

def check_login(page):
    """检查是否已登录"""
    try:
        print("🔍 检查登录状态...")
        
        # 等待页面加载完成
        page.wait_for_load_state('networkidle')
        
        # 检查多个可能的登录状态指标
        login_indicators = [
            # 未登录的标志
            {
                'selector': 'text=扫码登录',
                'text': ['扫码登录', '手机号登录'],
                'expect_visible': False
            },
            # 已登录的标志
            {
                'selector': '.upload-btn, button:has-text("发布"), .semi-button:has-text("发布视频")',
                'expect_visible': True
            }
        ]
        
        # 检查未登录标志
        for text in login_indicators[0]['text']:
            if page.get_by_text(text).count() > 0:
                print(f"❌ 发现未登录标志: {text}")
                return False
                
        # 检查已登录标志
        try:
            upload_btn = page.wait_for_selector(login_indicators[1]['selector'], timeout=5000)
            if upload_btn:
                print("✅ 已找到上传按钮，登录状态有效")
                return True
        except:
            print("❌ 未找到上传按钮")
            return False
            
        return False
    except Exception as e:
        print(f"❌ 检查登录状态时出错: {str(e)}")
        return False

def handle_login(page):
    """处理登录流程"""
    try:
        print("🔄 等待登录...")
        
        # 首先检查是否已经登录
        if check_login(page):
            print("✅ 已经处于登录状态")
            return True
            
        # 如果未登录，等待扫码登录按钮
        try:
            qr_btn = page.wait_for_selector('text=扫码登录', timeout=10000)
            if qr_btn:
                qr_btn.click()
                print("📱 请使用抖音APP扫描二维码登录")
                
                # 等待登录完成
                max_wait = 300  # 5分钟超时
                start_time = time.time()
                
                while time.time() - start_time < max_wait:
                    if check_login(page):
                        print("✅ 登录成功！")
                        # 保存cookies
                        cookies = page.context.cookies()
                        save_cookies(cookies)
                        return True
                    time.sleep(2)
                    
                print("❌ 登录等待超时")
                return False
        except Exception as e:
            print(f"❌ 等待登录按钮时出错: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ 登录过程出错: {str(e)}")
        return False

def upload_to_douyin(video_file):
    """上传视频到抖音"""
    try:
        with sync_playwright() as p:
            # 启动浏览器，添加更多内存和稳定性相关的参数
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials',
                    '--ignore-certificate-errors',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-setuid-sandbox',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-extensions',
                    '--disable-popup-blocking',
                    '--disable-notifications',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-background-timer-throttling',
                    '--memory-pressure-off',
                    # 增加内存限制
                    '--js-flags=--max-old-space-size=4096',
                    # 限制并发连接数
                    '--limit-fps=30',
                    '--disable-threaded-scrolling',
                    '--disable-threaded-animation',
                    # 禁用不必要的功能
                    '--disable-speech-api',
                    '--disable-sync',
                    '--disable-file-system',
                    '--disable-breakpad',
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True,
                bypass_csp=True,
                # 增加浏览器性能设置
                java_script_enabled=True,
                accept_downloads=False,
                has_touch=False,
                is_mobile=False,
                device_scale_factor=1
            )
            
            # 加载cookies
            cookies = load_cookies()
            if cookies:
                context.add_cookies(cookies)
            
            page = context.new_page()
            page.set_default_timeout(120000)  # 2分钟超时
            
            try:
                print("🌐 访问抖音创作者平台...")
                
                # 添加重试机制
                max_retries = 3
                retry_count = 0
                last_error = None
                
                while retry_count < max_retries:
                    try:
                        # 先访问主页，等待较短时间
                        print(f"尝试访问主页 (尝试 {retry_count + 1}/{max_retries})...")
                        page.goto('https://creator.douyin.com/', 
                                wait_until='domcontentloaded',
                                timeout=30000)
                        
                        # 等待一下让页面稳定
                        page.wait_for_timeout(2000)
                        
                        # 然后访问上传页面
                        print(f"尝试访问上传页面 (尝试 {retry_count + 1}/{max_retries})...")
                        response = page.goto(
                            'https://creator.douyin.com/creator-micro/content/upload',
                            wait_until='domcontentloaded',  # 使用domcontentloaded而不是load
                            timeout=60000
                        )
                        
                        if response and response.ok:
                            print("✅ 页面加载成功")
                            
                            # 等待页面准备就绪
                            try:
                                # 等待任意一个关键元素出现
                                page.wait_for_selector(
                                    'input[type="file"], .upload-btn, .semi-upload, [class*="upload"]',
                                    timeout=30000,
                                    state='attached'  # 使用attached而不是visible
                                )
                                print("✅ 页面已准备就绪")
                                break
                            except Exception as e:
                                print(f"⚠️ 等待页面元素超时: {str(e)}")
                                # 保存当前页面状态
                                page.screenshot(path=f'douyin_page_state_{retry_count}.png')
                                raise e
                        else:
                            print(f"⚠️ 页面响应异常: {response.status if response else 'No response'}")
                            raise Exception("页面响应异常")
                            
                    except Exception as e:
                        last_error = e
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"⚠️ 访问失败，等待重试... ({retry_count}/{max_retries})")
                            print(f"错误信息: {str(e)}")
                            # 保存错误现场
                            try:
                                page.screenshot(path=f'douyin_error_{retry_count}.png')
                                with open(f'douyin_error_{retry_count}.html', 'w', encoding='utf-8') as f:
                                    f.write(page.content())
                            except:
                                pass
                            # 增加重试等待时间
                            page.wait_for_timeout(5000 * retry_count)
                            # 刷新cookies
                            if cookies:
                                context.clear_cookies()
                                context.add_cookies(cookies)
                            continue
                        else:
                            print(f"❌ 重试次数已达上限，上传失败: {str(last_error)}")
                            return False
                
                # 检查登录状态
                if not check_login(page):
                    print("⚠️ 需要重新登录")
                    if not handle_login(page):
                        print("❌ 登录失败")
                        return False
                
                print("📤 开始上传视频...")
                
                # 等待页面加载完成
                page.wait_for_load_state('networkidle')
                
                # 尝试多个可能的上传按钮选择器
                upload_selectors = [
                    'input[type="file"]',
                    'input[accept*="video"]',
                    '.upload-btn input[type="file"]',
                    '.semi-upload input[type="file"]',
                    'div[class*="upload"] input[type="file"]'
                ]
                
                upload_input = None
                for selector in upload_selectors:
                    try:
                        print(f"尝试查找上传按钮: {selector}")
                        # 使用evaluate处理隐藏的input
                        elements = page.evaluate(f'''
                            () => {{
                                const inputs = document.querySelectorAll('{selector}');
                                return Array.from(inputs).map(el => {{
                                    return {{
                                        visible: el.offsetParent !== null,
                                        disabled: el.disabled,
                                        type: el.type
                                    }};
                                }});
                            }}
                        ''')
                        
                        if elements:
                            print(f"找到 {len(elements)} 个匹配元素")
                            # 等待元素可交互
                            upload_input = page.wait_for_selector(selector, state='attached', timeout=5000)
                            if upload_input:
                                print(f"✅ 成功找到上传按钮: {selector}")
                                break
                    except Exception as e:
                        print(f"尝试选择器 {selector} 失败: {str(e)}")
                        continue
                
                if not upload_input:
                    print("❌ 未找到可用的上传按钮")
                    # 保存页面源码以供调试
                    page.content().then(lambda content: open('douyin_upload_page.html', 'w', encoding='utf-8').write(content))
                    page.screenshot(path='douyin_upload_error.png')
                    return False
                
                # 上传视频
                print(f"正在上传视频: {os.path.basename(video_file)}")
                upload_input.set_input_files(video_file)
                
                print("⏳ 等待上传开始...")
                
                # 等待上传进度出现
                progress_selectors = [
                    '[class*="progress"]',
                    '[class*="upload-progress"]',
                    '[class*="percentage"]',
                    'div[role="progressbar"]'
                ]
                
                # 等待任意进度条出现
                for selector in progress_selectors:
                    try:
                        if page.wait_for_selector(selector, timeout=10000):
                            print("✅ 检测到上传进度条")
                            break
                    except:
                        continue
                
                # 监控上传状态
                max_wait = 300  # 最长等待5分钟
                start_time = time.time()
                last_progress = 0
                consecutive_errors = 0  # 连续错误计数
                
                while time.time() - start_time < max_wait:
                    try:
                        # 使用更简单的JavaScript代码检查进度
                        progress = page.evaluate('''
                            () => {
                                const els = document.querySelectorAll('[class*="progress"], [class*="percentage"], div[role="progressbar"]');
                                for (const el of els) {
                                    const text = el.textContent || '';
                                    const match = text.match(/\\d+/);
                                    if (match) return parseInt(match[0]);
                                }
                                return null;
                            }
                        ''')
                        
                        if progress is not None and progress != last_progress:
                            print(f"⏳ 上传进度: {progress}%")
                            last_progress = progress
                            consecutive_errors = 0  # 重置错误计数
                            
                            if progress >= 100:
                                print("✅ 上传完成，等待处理...")
                                # 等待处理完成
                                time.sleep(5)
                                break
                        
                        # 检查是否出现发布按钮
                        try:
                            if page.query_selector('button:has-text("发布")'):
                                print("✅ 检测到发布按钮")
                                return handle_publish(page)
                        except:
                            pass
                            
                        # 检查错误提示
                        try:
                            error_el = page.query_selector('text=上传失败, text=网络错误, text=文件格式不支持, [class*="error"]')
                            if error_el:
                                error_text = error_el.text_content()
                                print(f"❌ 上传出错: {error_text}")
                                return False
                        except:
                            pass
                        
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"监控进度时出错: {str(e)}")
                        consecutive_errors += 1
                        
                        # 如果连续错误超过5次，保存错误现场并重试
                        if consecutive_errors >= 5:
                            print("⚠️ 检测到连续错误，正在保存错误现场...")
                            try:
                                page.screenshot(path='douyin_upload_error.png')
                                with open('douyin_upload_error.html', 'w', encoding='utf-8') as f:
                                    f.write(page.content())
                            except:
                                pass
                            
                            # 尝试刷新页面
                            try:
                                page.reload(timeout=30000, wait_until='domcontentloaded')
                                print("🔄 页面已刷新，继续监控...")
                                consecutive_errors = 0
                            except:
                                print("❌ 页面刷新失败")
                                return False
                        
                        time.sleep(2)  # 错误后等待更长时间
                
                print("❌ 上传超时")
                return False
                
            except Exception as e:
                print(f"❌ {os.path.basename(video_file)} 上传失败: {str(e)}")
                # 保存错误现场
                try:
                    page.screenshot(path='douyin_error_final.png')
                    with open('douyin_error_final.html', 'w', encoding='utf-8') as f:
                        f.write(page.content())
                except:
                    pass
                return False
            finally:
                try:
                    context.close()
                    browser.close()
                except:
                    pass
    except Exception as e:
        print(f"❌ 浏览器启动失败: {str(e)}")
        return False

def create_browser_context(p):
    """创建浏览器实例和上下文"""
    browser = p.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--ignore-certificate-errors',
            '--disable-blink-features=AutomationControlled',
            '--disable-setuid-sandbox',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-extensions',
            '--disable-popup-blocking',
            '--disable-notifications',
            # 内存相关优化
            '--single-process',  # 使用单进程模式
            '--no-zygote',      # 禁用zygote进程
            '--disable-gpu-sandbox',
            '--disable-software-rasterizer',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--disable-accelerated-video-decode',
            # 降低内存使用
            '--js-flags=--max-old-space-size=2048',
            '--memory-pressure-off',
        ]
    )
    
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ignore_https_errors=True,
        bypass_csp=True,
        # 优化性能设置
        java_script_enabled=True,
        accept_downloads=False,
        has_touch=False,
        is_mobile=False,
        device_scale_factor=1,
        # 减少内存使用
        service_workers='block'
    )
    
    return browser, context

def try_click_button(page, button, max_attempts=3):
    """尝试多种方式点击按钮"""
    for attempt in range(max_attempts):
        try:
            # 检查页面是否崩溃
            try:
                page.evaluate('1')  # 简单的JS执行测试
            except:
                print("⚠️ 检测到页面崩溃，尝试恢复...")
                # 重新加载页面
                try:
                    current_url = page.url
                    page.reload(timeout=30000, wait_until='domcontentloaded')
                    # 重新获取按钮
                    button = page.wait_for_selector('button:has-text("发布")', 
                                                  state='visible',
                                                  timeout=30000)
                    if not button:
                        raise Exception("无法重新获取发布按钮")
                except Exception as e:
                    print(f"❌ 页面恢复失败: {str(e)}")
                    return False
            
            print(f"\n第 {attempt + 1} 次尝试点击:")
            
            # 1. 检查按钮状态
            button_info = page.evaluate("""(element) => {
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return {
                    visible: style.display !== 'none' && style.visibility !== 'hidden',
                    enabled: !element.disabled,
                    position: {
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    }
                };
            }""", button)
            
            print(f"按钮状态: {json.dumps(button_info, indent=2)}")
            
            # 2. 尝试常规点击
            try:
                button.click(timeout=30000, force=True)
                print("✅ 常规点击成功")
                return True
            except Exception as e1:
                print(f"常规点击失败: {str(e1)}")
                
                # 3. 尝试使用position点击
                try:
                    pos = button_info['position']
                    page.mouse.click(pos['x'] + pos['width']/2, pos['y'] + pos['height']/2)
                    print("✅ 位置点击成功")
                    return True
                except Exception as e2:
                    print(f"位置点击失败: {str(e2)}")
                    
                    # 4. 尝试JavaScript点击
                    try:
                        page.evaluate("""(element) => {
                            element.click();
                            element.dispatchEvent(new MouseEvent('click', {
                                bubbles: true,
                                cancelable: true,
                                view: window
                            }));
                        }""", button)
                        print("✅ JavaScript点击成功")
                        return True
                    except Exception as e3:
                        print(f"JavaScript点击失败: {str(e3)}")
                        
                        # 5. 尝试移除遮罩并点击
                        try:
                            page.evaluate("""() => {
                                // 移除遮罩
                                const overlays = document.querySelectorAll('[class*="overlay"], [class*="mask"], [class*="modal"], [class*="dialog"]');
                                overlays.forEach(overlay => overlay.remove());
                                
                                // 修复样式
                                const elements = document.querySelectorAll('*');
                                elements.forEach(el => {
                                    if (window.getComputedStyle(el).pointerEvents === 'none') {
                                        el.style.pointerEvents = 'auto';
                                    }
                                    if (window.getComputedStyle(el).zIndex > 1000) {
                                        el.style.zIndex = '0';
                                    }
                                });
                            }""")
                            
                            button.click(timeout=30000, force=True)
                            print("✅ 移除遮罩后点击成功")
                            return True
                        except Exception as e4:
                            print(f"移除遮罩后点击失败: {str(e4)}")
            
            if attempt < max_attempts - 1:
                print(f"\n等待3秒后进行第 {attempt + 2} 次尝试...")
                time.sleep(3)
                
                # 保存当前状态
                try:
                    page.screenshot(path=f'douyin_click_attempt_{attempt + 1}.png')
                    with open(f'douyin_click_attempt_{attempt + 1}.html', 'w', encoding='utf-8') as f:
                        f.write(page.content())
                except:
                    pass
                    
        except Exception as e:
            print(f"尝试过程出错: {str(e)}")
            if attempt < max_attempts - 1:
                print(f"\n等待3秒后重试...")
                time.sleep(3)
    
    return False

def handle_publish(page):
    """处理发布阶段"""
    try:
        # 等待发布按钮完全可点击
        publish_button = page.wait_for_selector('button:has-text("发布")', 
                                              state='visible',
                                              timeout=30000)
        
        if not publish_button:
            print("❌ 未找到发布按钮")
            return False
            
        print("✅ 检测到发布按钮")
        
        # 确保页面稳定
        time.sleep(3)
        
        # 记录发布前的URL
        pre_publish_url = page.url
        
        # 尝试点击发布按钮
        print("尝试点击发布按钮...")
        if not try_click_button(page, publish_button):
            print("❌ 所有点击方式都失败了")
            
            # 保存失败现场
            try:
                page.screenshot(path='douyin_click_error.png')
                with open('douyin_click_error.html', 'w', encoding='utf-8') as f:
                    f.write(page.content())
                print("📸 已保存点击失败现场")
            except:
                pass
                
            return False
            
        print("✅ 点击发布按钮成功")
        
        # 等待页面发生变化
        try:
            page.wait_for_url(lambda url: url != pre_publish_url, timeout=30000)
            print("✅ 检测到页面跳转")
        except:
            print("⚠️ 页面未发生跳转")
        
        # 多轮检查发布状态
        max_checks = 3
        check_interval = 5
        success = False
        
        for check_round in range(max_checks):
            print(f"\n🔄 第 {check_round + 1} 轮状态检查:")
            
            # 1. 检查URL
            current_url = page.url
            if any(x in current_url for x in ['publish/success', 'video/manage', 'creator/content']):
                print("✅ URL显示发布成功")
                success = True
                break
            
            # 2. 检查成功提示
            success_indicators = [
                'text=发布成功',
                'text=已发布',
                'text=视频已发布',
                '[class*="success"]',
                '[class*="published"]',
                'text=视频正在处理',  # 有些情况下会显示这个
                'text=视频已上传成功'
            ]
            
            for indicator in success_indicators:
                try:
                    if page.query_selector(indicator):
                        print(f"✅ 检测到成功标志: {indicator}")
                        success = True
                        break
                except:
                    continue
            
            if success:
                break
            
            # 3. 检查页面状态
            try:
                # 检查是否在视频管理页面
                if page.query_selector('text=视频管理') or page.query_selector('text=内容管理'):
                    print("✅ 已进入视频管理页面")
                    success = True
                    break
                    
                # 检查是否有最新发布的视频
                recent_videos = page.query_selector_all('[class*="video-item"], [class*="content-item"]')
                if recent_videos:
                    print("✅ 检测到视频列表")
                    success = True
                    break
            except:
                pass
            
            # 4. 检查错误提示
            error_indicators = [
                'text=发布失败',
                'text=网络错误',
                'text=系统繁忙',
                '[class*="error"]',
                '[class*="fail"]'
            ]
            
            has_error = False
            for indicator in error_indicators:
                try:
                    error_el = page.query_selector(indicator)
                    if error_el:
                        error_text = error_el.text_content()
                        print(f"❌ 发布失败: {error_text}")
                        has_error = True
                        break
                except:
                    continue
            
            if has_error:
                return False
            
            # 如果还没有明确结果，等待后继续检查
            if not success and check_round < max_checks - 1:
                print(f"⏳ 等待 {check_interval} 秒后进行下一轮检查...")
                time.sleep(check_interval)
                
                # 尝试刷新页面
                try:
                    page.reload(timeout=30000, wait_until='domcontentloaded')
                    print("🔄 页面已刷新")
                except:
                    print("⚠️ 页面刷新失败")
        
        if not success:
            print("\n⚠️ 未检测到明确的发布结果，保存当前状态...")
            
            # 保存发布状态信息
            try:
                # 截图
                page.screenshot(path='douyin_publish_status.png')
                print("📸 已保存状态截图")
                
                # 保存页面内容
                with open('douyin_publish_status.html', 'w', encoding='utf-8') as f:
                    f.write(page.content())
                print("📄 已保存页面内容")
                
                # 保存当前URL
                print(f"🔗 当前URL: {page.url}")
            except Exception as e:
                print(f"⚠️ 保存状态信息时出错: {str(e)}")
            
            return None
        
        # 发布成功后，尝试获取视频ID
        try:
            video_id = None
            match = re.search(r'video/(\d+)', page.url)
            if match:
                video_id = match.group(1)
                print(f"📝 视频ID: {video_id}")
        except:
            pass
        
        print("\n✅ 发布流程完成")
        return True
        
    except Exception as e:
        print(f"❌ 发布过程出错: {str(e)}")
        
        # 保存错误现场
        try:
            page.screenshot(path='douyin_publish_error.png')
            with open('douyin_publish_error.html', 'w', encoding='utf-8') as f:
                f.write(page.content())
        except:
            pass
            
        return False

def process_upload_result(success):
    """处理上传结果"""
    if success is True:
        print("\n✅ 视频发布成功！")
        return True
    elif success is False:
        print("\n❌ 视频发布失败")
        return False
    else:  # success is None
        print("\n⚠️ 发布状态未知，请手动检查")
        return False


