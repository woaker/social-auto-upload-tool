# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Page
import os
import asyncio

from conf import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script, wait_with_timeout
from utils.log import douyin_logger


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
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, thumbnail_path=None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.thumbnail_path = thumbnail_path
        self.default_location = "北京市"  # 默认地理位置

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

    async def set_thumbnail(self, page: Page, thumbnail_path: str):
        """设置视频封面，如果未提供封面则等待平台自动生成"""
        try:
            # 检查是否有封面选择器
            cover_selector = 'text="选择封面"'
            cover_button = page.locator(cover_selector)
            
            # 等待封面按钮出现，最多等待10秒
            try:
                await cover_button.wait_for(timeout=10000)
            except:
                douyin_logger.warning("  [-] 未找到封面选择按钮，可能页面结构已变化")
                return
            
            if thumbnail_path:
                # 用户提供了封面，上传自定义封面
                douyin_logger.info("  [-] 正在上传自定义封面...")
                await cover_button.click()
                await page.wait_for_selector("div.semi-modal-content:visible", timeout=5000)
                await page.click('text="设置竖封面"')
                await page.wait_for_timeout(2000)  # 等待2秒
                
                # 定位到上传区域并点击
                file_input = page.locator("div[class^='semi-upload upload'] >> input.semi-upload-hidden-input")
                await file_input.set_input_files(thumbnail_path)
                await page.wait_for_timeout(2000)  # 等待2秒
                
                # 点击完成按钮
                finish_button = page.locator("div[class^='extractFooter'] button:visible:has-text('完成')")
                if await finish_button.count() > 0:
                    await finish_button.click()
                    douyin_logger.success("  [-] 自定义封面设置成功")
                else:
                    douyin_logger.warning("  [-] 未找到完成按钮，封面可能未设置成功")
            else:
                # 未提供封面，等待平台自动生成
                douyin_logger.info("  [-] 未提供封面，等待平台自动生成封面...")
                
                # 检查是否已有自动生成的封面预览
                preview_selectors = [
                    "div[class*='cover-container']",
                    "div[class*='cover-preview']",
                    "div[class*='thumbnail']",
                    "div[class*='cover'] img"
                ]
                
                # 等待封面生成，最多等待15秒
                cover_found = False
                start_time = datetime.now()
                timeout_seconds = 15
                
                while (datetime.now() - start_time).total_seconds() < timeout_seconds:
                    for selector in preview_selectors:
                        try:
                            preview = page.locator(selector)
                            if await preview.count() > 0 and await preview.is_visible():
                                cover_found = True
                                douyin_logger.success(f"  [-] 检测到平台已自动生成封面")
                                break
                        except:
                            pass
                    
                    if cover_found:
                        break
                        
                    douyin_logger.info(f"  [-] 等待封面生成中... ({int((datetime.now() - start_time).total_seconds())}秒)")
                    await asyncio.sleep(2)
                
                if not cover_found:
                    douyin_logger.warning(f"  [-] 等待封面生成超时({timeout_seconds}秒)，将使用平台默认封面")
        except Exception as e:
            douyin_logger.warning(f"  [-] 设置封面过程中出错: {str(e)}，将使用平台默认封面")
            douyin_logger.info("  [-] 封面不是必需的，继续发布流程...")

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium 浏览器启动一个浏览器实例
        if self.local_executable_path:
            browser = await playwright.chromium.launch(headless=False, executable_path=self.local_executable_path)
        else:
            browser = await playwright.chromium.launch(headless=False)
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(storage_state=f"{self.account_file}")
        context = await set_init_script(context)

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        douyin_logger.info(f'[+]正在上传-------{os.path.basename(self.file_path)}')
        # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
        douyin_logger.info(f'[-] 正在打开主页...')
        await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload")
        # 点击 "上传视频" 按钮
        await page.locator("div[class^='container'] input").set_input_files(self.file_path)

        # 等待页面跳转到指定的 URL，使用通用超时函数
        async def check_page_loaded():
            current_url = page.url
            return (
                "creator.douyin.com/creator-micro/content/publish?enter_from=publish_page" in current_url or
                "creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page" in current_url
            )
        
        page_loaded = await wait_with_timeout(
            check_func=check_page_loaded,
            timeout_seconds=60,
            interval_seconds=1.0,
            timeout_message="等待发布页面超时",
            success_message="成功进入发布页面!",
            progress_message="等待进入视频发布页面...",
            logger=douyin_logger
        )
        
        if not page_loaded:
            douyin_logger.error("❌ 终止发布")
            await context.close()
            await browser.close()
            return
            
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

        # 等待视频上传完成，使用通用超时函数
        async def check_upload_completed():
            try:
                number = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
                if number > 0:
                    return True
                
                # 检查是否上传失败
                if await page.locator('div.progress-div > div:has-text("上传失败")').count():
                    douyin_logger.error("  [-] 发现上传出错了... 准备重试")
                    await self.handle_upload_error(page)
            except:
                pass
            return False
        
        upload_completed = await wait_with_timeout(
            check_func=check_upload_completed,
            timeout_seconds=300,  # 5分钟超时
            interval_seconds=2.0,
            timeout_message="视频上传超时",
            success_message="视频上传完毕",
            progress_message="正在上传视频中...",
            logger=douyin_logger
        )
        
        if not upload_completed:
            douyin_logger.error("❌ 终止发布")
            await context.close()
            await browser.close()
            return
            
        #上传视频封面
        await self.set_thumbnail(page, self.thumbnail_path)

        # 更换可见元素
        await self.set_location(page, self.default_location)

        # 頭條/西瓜 - 自动同步到头条
        await self.set_toutiao_sync(page)

        if self.publish_date != 0:
            await self.set_schedule_time_douyin(page, self.publish_date)

        # 等待发布完成，使用通用超时函数
        async def check_publish_completed():
            try:
                publish_button = page.get_by_role('button', name="发布", exact=True)
                if await publish_button.count():
                    await publish_button.click()
                
                # 检查是否已跳转到作品管理页面
                current_url = page.url
                if "creator.douyin.com/creator-micro/content/manage" in current_url:
                    return True
            except:
                # 保存当前状态的截图
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                await page.screenshot(path=f"douyin_publish_{timestamp}.png", full_page=True)
            return False
        
        publish_completed = await wait_with_timeout(
            check_func=check_publish_completed,
            timeout_seconds=180,  # 3分钟超时
            interval_seconds=1.0,
            timeout_message="视频发布超时，可能需要手动确认",
            success_message="视频发布成功",
            progress_message="视频正在发布中...",
            logger=douyin_logger
        )
        
        if not publish_completed:
            # 尝试截图保存当前状态
            await page.screenshot(path="douyin_publish_timeout.png", full_page=True)

        await context.storage_state(path=self.account_file)  # 保存cookie
        douyin_logger.success('  [-]cookie更新完毕！')
        await asyncio.sleep(2)  # 这里延迟是为了方便眼睛直观的观看
        # 关闭浏览器上下文和浏览器实例
        await context.close()
        await browser.close()
    
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


