# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Page
import os
import asyncio
import time
from playwright.sync_api import sync_playwright
import json

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
                    return json.load(f)
                    
        print("❌ 未找到任何cookie文件")
    except Exception as e:
        print(f"❌ 加载cookies失败: {str(e)}")
    return None

def save_cookies(cookies):
    """保存cookies"""
    try:
        # 优先保存到标准位置
        cookie_dir = os.path.join('cookies', 'douyin_uploader')
        os.makedirs(cookie_dir, exist_ok=True)
        cookie_file = os.path.join(cookie_dir, 'douyin_cookies.json')
        
        with open(cookie_file, 'w') as f:
            json.dump(cookies, f)
        print(f"✅ cookies已保存到: {cookie_file}")
        
        # 同时保存一份到cookiesFile目录
        alt_cookie_dir = 'cookiesFile'
        os.makedirs(alt_cookie_dir, exist_ok=True)
        alt_cookie_file = os.path.join(alt_cookie_dir, 'douyin_account.json')
        
        with open(alt_cookie_file, 'w') as f:
            json.dump(cookies, f)
        print(f"✅ cookies已备份到: {alt_cookie_file}")
        
    except Exception as e:
        print(f"❌ 保存cookies失败: {str(e)}")

def check_login(page):
    """检查是否已登录"""
    try:
        # 检查是否存在上传按钮
        upload_btn = page.query_selector('.upload-btn')
        return upload_btn is not None
    except:
        return False

def handle_login(page):
    """处理登录流程"""
    try:
        print("🔄 等待登录...")
        
        # 等待扫码登录按钮出现
        qr_btn = page.wait_for_selector('text=扫码登录', timeout=10000)
        if qr_btn:
            qr_btn.click()
            print("📱 请使用抖音APP扫描二维码登录")
            
            # 等待登录完成
            page.wait_for_selector('.upload-btn', timeout=300000)  # 5分钟超时
            print("✅ 登录成功！")
            
            # 保存cookies
            cookies = page.context.cookies()
            save_cookies(cookies)
            return True
    except Exception as e:
        print(f"❌ 登录失败: {str(e)}")
        return False

def upload_to_douyin(video_file):
    """上传视频到抖音"""
    try:
        with sync_playwright() as p:
            # 启动 Firefox
            browser = p.firefox.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/91.0'
            )
            
            # 加载cookies
            cookies = load_cookies()
            if cookies:
                context.add_cookies(cookies)
            
            page = context.new_page()
            page.set_default_timeout(60000)  # 60秒超时
            
            try:
                # 打开抖音创作者平台
                page.goto('https://creator.douyin.com/')
                
                # 检查登录状态
                if not check_login(page):
                    if not handle_login(page):
                        return False
                
                print("📤 开始上传视频...")
                
                # 点击上传按钮
                page.click('.upload-btn')
                
                # 等待上传对话框出现
                upload_input = page.wait_for_selector('input[type="file"]', timeout=30000)
                
                # 上传视频
                upload_input.set_input_files(video_file)
                
                # 等待上传完成
                page.wait_for_selector('.upload-success-icon', timeout=300000)  # 5分钟超时
                
                # 点击发布按钮
                publish_button = page.wait_for_selector('button:has-text("发布")', timeout=30000)
                publish_button.click()
                
                # 等待发布完成
                page.wait_for_selector('.publish-success', timeout=60000)
                
                print(f"✅ {os.path.basename(video_file)} 上传成功！")
                return True
                
            except Exception as e:
                print(f"❌ {os.path.basename(video_file)} 上传失败: {str(e)}")
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


