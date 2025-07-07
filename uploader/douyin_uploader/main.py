# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Page
import os
import asyncio
import time
from playwright.sync_api import sync_playwright
import json
import re

from config import LOCAL_CHROME_PATH, BASE_DIR
from utils.base_social_media import set_init_script
from utils.log import douyin_logger
from douyin_config import get_browser_config, get_context_config, get_anti_detection_script


async def cookie_auth(account_file):
    """验证cookie是否有效，使用更严格的检查"""
    browser = None
    context = None
    page = None
    
    try:
        async with async_playwright() as playwright:
            douyin_logger.info("启动浏览器进行cookie验证...")
            
            # 使用无头模式启动浏览器，添加更多稳定性参数
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=site-per-process',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # 创建新的上下文
            context = await browser.new_context(
                storage_state=account_file,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # 设置反检测脚本
            context = await set_init_script(context)
            
            # 创建新页面
            page = await context.new_page()
            
            # 注入监控脚本
            await page.evaluate('''() => {
                window.loginStatus = {
                    isLoggedIn: false,
                    error: null,
                    lastCheck: Date.now()
                };
                
                // 监控XHR请求
                const originalXHR = window.XMLHttpRequest;
                window.XMLHttpRequest = function() {
                    const xhr = new originalXHR();
                    const originalOpen = xhr.open;
                    
                    xhr.open = function() {
                        this.addEventListener('load', () => {
                            try {
                                const response = JSON.parse(this.responseText);
                                if (response.data && response.data.user) {
                                    window.loginStatus.isLoggedIn = true;
                                }
                            } catch {}
                        });
                        return originalOpen.apply(this, arguments);
                    };
                    
                    return xhr;
                };
                
                // 监控Fetch请求
                const originalFetch = window.fetch;
                window.fetch = async function() {
                    try {
                        const response = await originalFetch.apply(this, arguments);
                        const clonedResponse = response.clone();
                        const text = await clonedResponse.text();
                        try {
                            const data = JSON.parse(text);
                            if (data.data && data.data.user) {
                                window.loginStatus.isLoggedIn = true;
                            }
                        } catch {}
                        return response;
                    } catch (error) {
                        window.loginStatus.error = error.message;
                        throw error;
                    }
                };
            }''')
            
            # 首先尝试访问主页
            douyin_logger.info("访问抖音创作者主页...")
            try:
                await page.goto(
                    "https://creator.douyin.com/",
                    wait_until="domcontentloaded",
                    timeout=30000
                )
                await asyncio.sleep(2)
            except Exception as e:
                douyin_logger.warning(f"访问主页失败: {str(e)}")
            
            # 检查登录状态
            login_status = await check_login_status(page)
            if not login_status:
                douyin_logger.warning("主页登录检查未通过")
                return False
            
            # 访问上传页面
            douyin_logger.info("访问上传页面...")
            try:
                await page.goto(
                    "https://creator.douyin.com/creator-micro/content/upload",
                    wait_until="domcontentloaded",
                    timeout=30000
                )
                await asyncio.sleep(2)
            except Exception as e:
                douyin_logger.warning(f"访问上传页面失败: {str(e)}")
                return False
            
            # 再次检查登录状态
            login_status = await check_login_status(page)
            if not login_status:
                douyin_logger.warning("上传页面登录检查未通过")
                return False
            
            # 检查上传功能
            try:
                upload_button = await page.wait_for_selector(
                    "input[type='file'], .upload-btn input, .semi-upload input",
                    timeout=10000,
                    state="attached"
                )
                if upload_button:
                    douyin_logger.success("✅ Cookie 有效")
                    return True
                else:
                    douyin_logger.warning("未找到上传按钮")
                    return False
            except Exception as e:
                douyin_logger.warning(f"检查上传按钮失败: {str(e)}")
                return False
            
    except Exception as e:
        douyin_logger.error(f"Cookie 验证出错: {str(e)}")
        return False
        
    finally:
        # 确保资源正确清理
        try:
            if page:
                await page.screenshot(path="cookie_auth_error.png")
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
        except:
            pass
            
async def check_login_status(page):
    """检查页面登录状态"""
    try:
        # 检查登录相关元素
        login_indicators = ['手机号登录', '扫码登录', '登录', 'login']
        for indicator in login_indicators:
            try:
                if await page.get_by_text(indicator, exact=False).count() > 0:
                    douyin_logger.warning(f"发现登录提示: {indicator}")
                    return False
            except:
                continue
        
        # 检查用户相关元素
        user_indicators = [
            '.user-info',
            '.avatar',
            '.nickname',
            '[class*="user"]',
            '[class*="creator"]'
        ]
        
        for indicator in user_indicators:
            try:
                element = await page.wait_for_selector(indicator, timeout=5000)
                if element:
                    douyin_logger.info(f"找到用户元素: {indicator}")
                    return True
            except:
                continue
        
        # 检查JavaScript注入的登录状态
        try:
            login_status = await page.evaluate('window.loginStatus')
            if login_status and login_status.get('isLoggedIn'):
                douyin_logger.info("JavaScript检测显示已登录")
                return True
        except:
            pass
        
        # 检查URL
        current_url = page.url
        if '/creator-micro/' in current_url or '/creator/' in current_url:
            douyin_logger.info("URL显示在创作者平台内")
            return True
        
        douyin_logger.warning("未检测到明确的登录状态")
        return False
        
    except Exception as e:
        douyin_logger.error(f"检查登录状态出错: {str(e)}")
        return False


async def douyin_setup(account_file, handle=False):
    """设置抖音上传环境，检查cookie是否有效"""
    # 检查账号文件是否存在
    if not os.path.exists(account_file):
        douyin_logger.warning(f"❌ Cookie文件不存在: {account_file}")
        if not handle:
            return False
            
        douyin_logger.info("🔄 准备生成新的Cookie文件...")
        await douyin_cookie_gen(account_file)
        
        # 验证新生成的cookie
        if not await cookie_auth(account_file):
            douyin_logger.error("❌ 新生成的Cookie验证失败")
            return False
            
        douyin_logger.success("✅ 新Cookie生成并验证成功")
        return True
    
    # 验证现有cookie
    douyin_logger.info("🔍 验证现有Cookie...")
    if not await cookie_auth(account_file):
        douyin_logger.warning("⚠️ 现有Cookie已失效")
        
        if not handle:
            return False
            
        douyin_logger.info("🔄 准备重新登录获取Cookie...")
        await douyin_cookie_gen(account_file)
        
        # 验证新生成的cookie
        if not await cookie_auth(account_file):
            douyin_logger.error("❌ 新生成的Cookie验证失败")
            return False
            
        douyin_logger.success("✅ 新Cookie生成并验证成功")
        return True
    
    douyin_logger.success("✅ Cookie验证通过")
    return True


async def douyin_cookie_gen(account_file):
    """生成抖音cookie文件，包含更完善的登录流程"""
    browser = None
    context = None
    page = None
    
    try:
        async with async_playwright() as playwright:
            douyin_logger.info("🚀 启动浏览器进行登录...")
            
            # 配置浏览器选项
            browser_options = {
                'headless': False,  # 显示浏览器界面
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--window-size=1920,1080'
                ]
            }
            
            if os.path.exists(LOCAL_CHROME_PATH):
                browser_options['executable_path'] = LOCAL_CHROME_PATH
            
            browser = await playwright.chromium.launch(**browser_options)
            
            # 配置浏览器上下文
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # 设置反检测脚本
            context = await set_init_script(context)
            
            # 创建新页面
            page = await context.new_page()
            
            # 访问登录页面
            douyin_logger.info("访问抖音创作者平台...")
            await page.goto(
                "https://creator.douyin.com/",
                wait_until="networkidle",
                timeout=30000
            )
            
            # 等待登录元素出现
            login_button = await page.wait_for_selector(
                "text=登录 >> visible=true",
                timeout=10000
            )
            
            if login_button:
                douyin_logger.info("✅ 成功加载登录页面")
                douyin_logger.info("⚠️ 请使用手机扫码登录")
                douyin_logger.info("登录成功后，系统将自动保存Cookie")
                
                # 等待用户登录
                try:
                    await page.wait_for_url(
                        "https://creator.douyin.com/creator-micro/content/upload",
                        timeout=300000  # 给用户5分钟时间登录
                    )
                    
                    # 额外等待确保页面加载完成
                    await asyncio.sleep(5)
                    
                    # 检查是否真的登录成功
                    if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
                        raise Exception("登录未完成")
                    
                    # 保存cookie
                    douyin_logger.info("正在保存Cookie...")
                    await context.storage_state(path=account_file)
                    douyin_logger.success("✅ Cookie保存成功")
                    
                    return True
                    
                except Exception as e:
                    douyin_logger.error(f"❌ 登录失败: {str(e)}")
                    return False
            else:
                douyin_logger.error("❌ 登录页面加载失败")
                return False
                
    except Exception as e:
        douyin_logger.error(f"❌ 登录过程出错: {str(e)}")
        return False
        
    finally:
        # 确保资源正确清理
        try:
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
        except:
            pass


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
            
            # 检查页面状态
            douyin_logger.info("检查页面状态...")
            page_content = await page.content()
            if "上传视频" not in page_content and "发布视频" not in page_content:
                douyin_logger.error("页面内容异常，可能未正确加载")
                await page.screenshot(path='page_content_error.png')
                raise Exception("页面加载异常，未找到上传视频相关内容")
            
            # 尝试多个可能的上传按钮选择器
            upload_button = None
            selectors = [
                "input[type='file']",
                "input[accept='video/*']",
                ".upload-btn input",
                ".semi-upload input",
                "div[class^='upload'] input[type='file']",
                "//input[@type='file']",  # XPath选择器
                "//input[contains(@class, 'upload')][@type='file']"  # 更具体的XPath
            ]
            
            douyin_logger.info("开始查找上传按钮...")
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

            # 等待视频上传完成
            upload_timeout = 7200  # 2小时超时
            start_time = time.time()
            upload_success = False
            last_progress = ""
            no_progress_time = time.time()
            last_progress_value = 0
            max_retry_attempts = 5  # 增加重试次数
            retry_attempt = 0
            last_check_time = time.time()
            check_interval = 2  # 检查间隔（秒）
            
            # 注入监控脚本
            await page.evaluate('''() => {
                window.uploadProgress = {
                    status: '',
                    progress: 0,
                    error: null,
                    lastUpdate: Date.now()
                };
                
                // 监控XHR请求
                const originalXHR = window.XMLHttpRequest;
                window.XMLHttpRequest = function() {
                    const xhr = new originalXHR();
                    const originalOpen = xhr.open;
                    const originalSend = xhr.send;
                    
                    xhr.open = function() {
                        this.addEventListener('progress', (event) => {
                            if (event.lengthComputable) {
                                const progress = Math.round((event.loaded / event.total) * 100);
                                window.uploadProgress.progress = progress;
                                window.uploadProgress.lastUpdate = Date.now();
                            }
                        });
                        
                        this.upload?.addEventListener('progress', (event) => {
                            if (event.lengthComputable) {
                                const progress = Math.round((event.loaded / event.total) * 100);
                                window.uploadProgress.progress = progress;
                                window.uploadProgress.lastUpdate = Date.now();
                            }
                        });
                        
                        return originalOpen.apply(this, arguments);
                    };
                    
                    xhr.send = function() {
                        return originalSend.apply(this, arguments);
                    };
                    
                    return xhr;
                };
                
                // 监控Fetch请求
                const originalFetch = window.fetch;
                window.fetch = async function() {
                    try {
                        const response = await originalFetch.apply(this, arguments);
                        if (response.ok) {
                            window.uploadProgress.lastUpdate = Date.now();
                        } else {
                            window.uploadProgress.error = `HTTP ${response.status}`;
                        }
                        return response;
                    } catch (error) {
                        window.uploadProgress.error = error.message;
                        throw error;
                    }
                };
                
                // 监控网络状态
                window.addEventListener('online', () => {
                    window.uploadProgress.status = 'online';
                });
                
                window.addEventListener('offline', () => {
                    window.uploadProgress.status = 'offline';
                });
                
                // 监控页面可见性
                document.addEventListener('visibilitychange', () => {
                    window.uploadProgress.status = document.visibilityState;
                });
            }''')
            
            while time.time() - start_time < upload_timeout and retry_attempt < max_retry_attempts:
                try:
                    # 控制检查频率
                    current_time = time.time()
                    if current_time - last_check_time < check_interval:
                        await asyncio.sleep(0.5)
                        continue
                    last_check_time = current_time
                    
                    # 获取上传状态
                    upload_info = await page.evaluate('window.uploadProgress')
                    if upload_info:
                        # 检查进度
                        if 'progress' in upload_info and upload_info['progress'] > 0:
                            current_progress = f"{upload_info['progress']}%"
                            if current_progress != last_progress:
                                douyin_logger.info(f"📊 上传进度: {current_progress}")
                                last_progress = current_progress
                                no_progress_time = time.time()
                        
                        # 检查错误
                        if upload_info.get('error'):
                            douyin_logger.error(f"⚠️ 上传错误: {upload_info['error']}")
                            await page.screenshot(path=f"upload_error_{retry_attempt}.png")
                            
                            # 尝试恢复
                            try:
                                # 检查网络状态
                                network_status = await page.evaluate('''() => {
                                    return {
                                        online: navigator.onLine,
                                        connection: navigator.connection ? {
                                            type: navigator.connection.effectiveType,
                                            downlink: navigator.connection.downlink,
                                            rtt: navigator.connection.rtt
                                        } : null,
                                        visibility: document.visibilityState
                                    }
                                }''')
                                douyin_logger.info(f"网络状态: {network_status}")
                                
                                if not network_status['online']:
                                    douyin_logger.warning("⚠️ 网络连接已断开")
                                    await page.wait_for_function('navigator.onLine', timeout=300000)  # 5分钟
                                    douyin_logger.info("✅ 网络已恢复")
                                
                                # 尝试重试
                                retry_selectors = [
                                    'button:has-text("重新上传")',
                                    'button:has-text("重试")',
                                    'button:has-text("继续上传")',
                                    '[class*="reupload"]',
                                    '[class*="retry"]',
                                    '[class*="continue"]',
                                    '[class*="resume"]'
                                ]
                                
                                retry_found = False
                                for selector in retry_selectors:
                                    try:
                                        retry_button = await page.wait_for_selector(selector, timeout=5000)
                                        if retry_button:
                                            douyin_logger.info(f"找到重试按钮: {selector}")
                                            await retry_button.click()
                                            await asyncio.sleep(2)
                                            retry_found = True
                                            break
                                    except:
                                        continue
                                
                                if not retry_found:
                                    douyin_logger.info("未找到重试按钮，尝试刷新页面...")
                                    await page.reload(timeout=60000, wait_until="networkidle")
                                    await asyncio.sleep(5)
                                
                                # 重置状态
                                await page.evaluate('window.uploadProgress.error = null')
                                no_progress_time = time.time()
                                retry_attempt += 1
                                
                            except Exception as e:
                                douyin_logger.error(f"恢复失败: {str(e)}")
                                await page.screenshot(path=f"recovery_error_{retry_attempt}.png")
                                retry_attempt += 1
                                continue
                        
                        # 检查成功状态
                        success_indicators = [
                            'text="上传完成"',
                            'text="已发布"',
                            '[class*="success"]',
                            '.upload-success'
                        ]
                        
                        for indicator in success_indicators:
                            try:
                                if await page.locator(indicator).count() > 0:
                                    douyin_logger.info(f"✅ 检测到成功标志: {indicator}")
                                    upload_success = True
                                    break
                            except:
                                continue
                        
                        if upload_success:
                            break
                    
                    # 检查是否长时间无响应
                    if time.time() - no_progress_time > 180:  # 3分钟无响应
                        douyin_logger.warning("⚠️ 页面长时间无响应，尝试刷新...")
                        await page.screenshot(path=f"no_response_{retry_attempt}.png")
                        
                        try:
                            await page.reload(timeout=60000, wait_until="networkidle")
                            await asyncio.sleep(5)
                            no_progress_time = time.time()
                        except Exception as e:
                            douyin_logger.error(f"刷新页面失败: {str(e)}")
                            retry_attempt += 1
                            continue
                    
                    # 检查是否上传完成
                    success_indicators = [
                        '[class^="long-card"] div:has-text("重新上传")',
                        '[class*="upload-success"]',
                        '[class*="complete"]',
                        '.video-card:visible',
                        'div:has-text("上传成功")',
                        'div:has-text("发布")',
                        'button:has-text("发布")',
                        '.semi-button:has-text("发布")',
                        '.upload-complete',
                        '.success-icon'
                    ]
                    
                    for indicator in success_indicators:
                        try:
                            if await page.locator(indicator).count() > 0:
                                douyin_logger.success(f"✅ 检测到上传成功标志: {indicator}")
                                # 再次验证发布按钮是否真的可用
                                if "发布" in indicator:
                                    publish_button = page.get_by_role('button', name="发布", exact=True)
                                    if await publish_button.count() and await publish_button.is_enabled():
                                        douyin_logger.success("✅ 发布按钮可用，上传确实完成")
                                        upload_success = True
                                        break
                                else:
                                    upload_success = True
                                    break
                        except:
                            continue
                    
                    if upload_success:
                        # 最终验证：等待5秒后再次检查
                        await asyncio.sleep(5)
                        if await page.get_by_role('button', name="发布", exact=True).count() > 0:
                            douyin_logger.success("✅ 最终验证通过，视频确实上传完成")
                            await page.screenshot(path="upload_success.png")
                            break
                        else:
                            upload_success = False
                            douyin_logger.warning("⚠️ 最终验证失败，继续等待")
                    
                    # 检查是否上传失败
                    error_indicators = [
                        'div.progress-div > div:has-text("上传失败")',
                        'div:has-text("上传出错")',
                        'div:has-text("网络异常")',
                        'div:has-text("请重试")',
                        '.error-message',
                        '.upload-error',
                        'div:has-text("视频格式不支持")',
                        'div:has-text("视频大小超过限制")',
                        'div:has-text("视频时长超过限制")',
                        'div:has-text("上传超时")'
                    ]
                    
                    for indicator in error_indicators:
                        if await page.locator(indicator).count() > 0:
                            error_text = await page.locator(indicator).text_content()
                            douyin_logger.error(f"❌ 检测到上传失败: {error_text}")
                            await page.screenshot(path=f"upload_error_{retry_attempt}.png")
                            
                            # 如果是格式/大小/时长问题，直接失败
                            if any(x in error_text for x in ["格式不支持", "大小超过限制", "时长超过限制"]):
                                raise Exception(f"视频不符合要求: {error_text}")
                            
                            # 否则尝试重新上传
                            await self.handle_upload_error(page)
                            await asyncio.sleep(5)  # 等待重新上传开始
                            no_progress_time = time.time()  # 重置进度检查时间
                            retry_attempt += 1
                            break
                    
                    # 每30秒保存一次截图，用于调试
                    if int(time.time() - start_time) % 30 == 0:
                        await page.screenshot(path=f"upload_progress_{int(time.time())}.png")
                    
                    douyin_logger.info("⏳ 视频上传中...")
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    douyin_logger.warning(f"检查上传状态时出错: {str(e)}")
                    await page.screenshot(path=f"upload_check_error_{retry_attempt}_{int(time.time())}.png")
                    retry_attempt += 1
                    await asyncio.sleep(5)
            
            if not upload_success:
                if retry_attempt >= max_retry_attempts:
                    douyin_logger.error("❌ 超过最大重试次数")
                else:
                    douyin_logger.error("❌ 视频上传超时")
                await page.screenshot(path="upload_timeout.png")
                raise Exception("视频上传失败，请检查网络连接或重试")
            
            #上传视频封面
            await self.set_thumbnail(page, self.thumbnail_path)

            # 更换可见元素
            await self.set_location(page, self.default_location)

            # 頭條/西瓜 - 自动同步到头条
            await self.set_toutiao_sync(page)

            if self.publish_date != 0:
                await self.set_schedule_time_douyin(page, self.publish_date)

            # 发布前的最终检查
            douyin_logger.info("进行发布前的最终检查...")
            
            # 检查必填项
            required_fields = {
                "标题": self.title,
                "视频文件": self.file_path,
            }
            
            for field_name, field_value in required_fields.items():
                if not field_value:
                    raise Exception(f"发布失败：{field_name}不能为空")
            
            # 判断视频是否发布成功
            max_publish_attempts = 3
            publish_attempt = 0
            
            while publish_attempt < max_publish_attempts:
                try:
                    # 等待发布按钮可用
                    douyin_logger.info("等待发布按钮可用...")
                    publish_button = page.get_by_role('button', name="发布", exact=True)
                    
                    if await publish_button.count():
                        # 检查按钮是否可点击
                        is_enabled = await publish_button.is_enabled()
                        button_class = await publish_button.get_attribute("class")
                        button_disabled = "disabled" in (button_class or "")
                        
                        if not is_enabled or button_disabled:
                            douyin_logger.warning("发布按钮未启用，等待中...")
                            await asyncio.sleep(5)  # 增加等待时间
                            continue
                        
                        # 点击发布按钮前截图
                        await page.screenshot(path=f"before_publish_{publish_attempt}.png")
                        
                        # 点击发布按钮
                        douyin_logger.info(f"尝试点击发布按钮 (第 {publish_attempt + 1} 次)")
                        await publish_button.click()
                        await asyncio.sleep(2)  # 等待点击生效
                        
                        # 检查是否有确认弹窗
                        confirm_button = page.get_by_role('button', name="确认")
                        if await confirm_button.count() > 0:
                            douyin_logger.info("检测到确认弹窗，点击确认")
                            await confirm_button.click()
                        
                        # 等待页面跳转
                        try:
                            douyin_logger.info("等待页面跳转到作品管理页面...")
                            await page.wait_for_url(
                                "https://creator.douyin.com/creator-micro/content/manage**",
                                timeout=60000  # 增加超时时间到60秒
                            )
                            
                            # 等待页面加载和可能的动画完成
                            await asyncio.sleep(10)  # 增加等待时间
                            
                            # 验证发布成功
                            success_indicators = [
                                "发布成功",
                                "已发布",
                                "作品管理",
                                self.title[:10]  # 使用视频标题的前10个字符作为指标
                            ]
                            
                            page_content = await page.content()
                            success_found = False
                            
                            for indicator in success_indicators:
                                if indicator in page_content:
                                    douyin_logger.success(f"✅ 检测到成功标志: {indicator}")
                                    success_found = True
                                    break
                            
                            if success_found:
                                # 进一步验证：检查作品列表
                                try:
                                    await page.reload()  # 刷新页面以确保看到最新内容
                                    await asyncio.sleep(5)
                                    
                                    # 查找最新发布的视频标题
                                    video_titles = await page.locator('.video-title, .content-title').all_text_contents()
                                    if any(self.title[:15] in title for title in video_titles):
                                        douyin_logger.success("✅ 在作品列表中找到新发布的视频！")
                                        await page.screenshot(path="publish_success_final.png")
                                        return True
                                    else:
                                        douyin_logger.warning("⚠️ 未在作品列表中找到新发布的视频")
                                except Exception as e:
                                    douyin_logger.warning(f"检查作品列表时出错: {str(e)}")
                            
                            douyin_logger.warning("⚠️ 未检测到明确的发布成功标志")
                            await page.screenshot(path=f"publish_warning_{publish_attempt}.png")
                            
                        except Exception as e:
                            douyin_logger.error(f"等待页面跳转超时: {str(e)}")
                            await page.screenshot(path=f"publish_timeout_{publish_attempt}.png")
                    else:
                        douyin_logger.warning("未找到发布按钮，重试中...")
                        await page.screenshot(path=f"no_publish_button_{publish_attempt}.png")
                        
                except Exception as e:
                    douyin_logger.error(f"发布过程出错: {str(e)}")
                    await page.screenshot(path=f"publish_error_{publish_attempt}.png")
                
                publish_attempt += 1
                if publish_attempt < max_publish_attempts:
                    douyin_logger.info(f"等待 10 秒后进行第 {publish_attempt + 1} 次尝试...")
                    await asyncio.sleep(10)  # 增加重试间隔
            
            if publish_attempt >= max_publish_attempts:
                raise Exception("发布失败：超过最大重试次数")

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
        # 统一使用cookiesFile目录
        cookie_file = os.path.join(BASE_DIR, 'cookiesFile', 'douyin_account.json')
        
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
                    print(f"❌ Cookie文件格式不正确")
                    return None
        else:
            print(f"❌ Cookie文件不存在: {cookie_file}")
            return None
            
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
        
        # 统一使用cookiesFile目录
        cookie_dir = os.path.join(BASE_DIR, 'cookiesFile')
        os.makedirs(cookie_dir, exist_ok=True)
        cookie_file = os.path.join(cookie_dir, 'douyin_account.json')
        
        with open(cookie_file, 'w') as f:
            json.dump(cookie_data, f, indent=2)
        print(f"✅ cookies已保存到: {cookie_file}")
        
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
        headless=False,  # 使用有头模式
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
            # 内存和性能优化
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-background-networking',
            '--disable-breakpad',
            '--disable-component-extensions-with-background-pages',
            '--disable-ipc-flooding-protection',
            '--disable-default-apps',
            '--mute-audio',
            # 降低资源使用
            '--disable-sync',
            '--disable-speech-api',
            '--disable-file-system',
            '--disable-composited-antialiasing',
            # 内存限制
            '--js-flags=--max-old-space-size=1024',
            # 进程模型
            '--single-process',
            '--no-zygote',
        ]
    )
    
    context = browser.new_context(
        viewport={'width': 1280, 'height': 800},  # 减小视窗大小
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ignore_https_errors=True,
        bypass_csp=True,
        # 优化性能设置
        java_script_enabled=True,
        accept_downloads=False,
        has_touch=False,
        is_mobile=False,
        device_scale_factor=1,
        # 减少资源使用
        service_workers='block',
        permissions=['notifications']
    )
    
    return browser, context

def recover_browser_session(p, current_url, cookies):
    """恢复浏览器会话"""
    try:
        print("\n🔄 尝试恢复浏览器会话...")
        
        # 创建新的浏览器实例
        browser, context = create_browser_context(p)
        
        # 添加cookies
        if cookies:
            context.add_cookies(cookies)
        
        # 创建新页面
        page = context.new_page()
        page.set_default_timeout(30000)
        
        # 导航到当前URL
        print(f"正在重新访问: {current_url}")
        page.goto(current_url, wait_until='domcontentloaded', timeout=30000)
        
        # 等待页面稳定
        time.sleep(3)
        
        return page, browser, context
    except Exception as e:
        print(f"❌ 会话恢复失败: {str(e)}")
        return None, None, None

def try_click_button(page, button, p=None, cookies=None, max_attempts=3):
    """尝试多种方式点击按钮"""
    current_browser = None
    current_context = None
    
    for attempt in range(max_attempts):
        try:
            # 检查页面是否崩溃
            try:
                page.evaluate('1')  # 简单的JS执行测试
            except:
                print("⚠️ 检测到页面崩溃，尝试恢复...")
                if p:
                    # 保存当前URL
                    try:
                        current_url = page.url
                    except:
                        print("⚠️ 无法获取当前URL")
                        return False
                    
                    # 关闭崩溃的浏览器
                    try:
                        if current_browser:
                            current_browser.close()
                        if current_context:
                            current_context.close()
                    except:
                        pass
                    
                    # 恢复会话
                    page, current_browser, current_context = recover_browser_session(p, current_url, cookies)
                    if not page:
                        print("❌ 无法恢复会话")
                        return False
                    
                    # 重新获取按钮
                    button = page.wait_for_selector('button:has-text("发布")', 
                                                  state='visible',
                                                  timeout=30000)
                    if not button:
                        print("❌ 无法重新获取发布按钮")
                        return False
                else:
                    print("❌ 无法恢复会话：未提供playwright实例")
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
                # 确保按钮在视图中
                button.scroll_into_view_if_needed()
                time.sleep(1)
                
                # 移动鼠标到按钮上
                page.mouse.move(
                    button_info['position']['x'] + button_info['position']['width']/2,
                    button_info['position']['y'] + button_info['position']['height']/2
                )
                time.sleep(0.5)
                
                # 点击
                button.click(timeout=30000, force=True)
                print("✅ 常规点击成功")
                return True
            except Exception as e1:
                print(f"常规点击失败: {str(e1)}")
                
                # 3. 尝试使用position点击
                try:
                    pos = button_info['position']
                    page.mouse.move(pos['x'] + pos['width']/2, pos['y'] + pos['height']/2)
                    time.sleep(0.5)
                    page.mouse.click(pos['x'] + pos['width']/2, pos['y'] + pos['height']/2)
                    print("✅ 位置点击成功")
                    return True
                except Exception as e2:
                    print(f"位置点击失败: {str(e2)}")
                    
                    # 4. 尝试JavaScript点击
                    try:
                        page.evaluate("""(element) => {
                            // 移除所有事件监听器
                            const clone = element.cloneNode(true);
                            element.parentNode.replaceChild(clone, element);
                            
                            // 直接点击
                            clone.click();
                            
                            // 触发多个事件
                            ['mousedown', 'mouseup', 'click'].forEach(eventType => {
                                clone.dispatchEvent(new MouseEvent(eventType, {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                }));
                            });
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
                            
                            time.sleep(1)
                            button.click(timeout=30000, force=True)
                            print("✅ 移除遮罩后点击成功")
                            return True
                        except Exception as e4:
                            print(f"移除遮罩后点击失败: {str(e4)}")
            
            if attempt < max_attempts - 1:
                print(f"\n等待5秒后进行第 {attempt + 2} 次尝试...")
                time.sleep(5)
                
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
                print(f"\n等待5秒后重试...")
                time.sleep(5)
    
    return False

def handle_publish(page, p=None, cookies=None):
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
        if not try_click_button(page, publish_button, p, cookies):
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


