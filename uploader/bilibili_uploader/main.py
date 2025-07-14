import json
import os
import pathlib
import random
import asyncio
from datetime import datetime
import time # Added for time.time()

from playwright.async_api import Playwright, async_playwright, Page

from conf import LOCAL_CHROME_PATH, BASE_DIR
from utils.base_social_media import set_init_script
from utils.log import bilibili_logger
from utils.video_converter import convert_video_if_needed, cleanup_converted_files


async def cookie_auth(account_file):
    """验证cookie是否有效"""
    bilibili_logger.info(f"正在验证B站cookie: {account_file}")
    
    # 检查文件是否存在
    if not os.path.exists(account_file):
        bilibili_logger.error(f"Cookie文件不存在: {account_file}")
        return False
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        
        try:
            # 加载cookie文件
            with open(account_file, 'r', encoding='utf-8') as f:
                storage_state = json.load(f)
            
            # 创建浏览器上下文
            context = await browser.new_context(storage_state=storage_state)
            context = await set_init_script(context)
            
            # 创建一个新的页面
            page = await context.new_page()
            
            # 访问B站个人空间页面
            bilibili_logger.info("访问B站个人空间页面检查登录状态...")
            await page.goto("https://space.bilibili.com/")
            
            # 等待页面加载
            await page.wait_for_load_state("networkidle")
            
            # 检查是否有登录按钮
            login_button = page.locator("a:has-text('登录')").first
            if await login_button.count() > 0:
                bilibili_logger.info("检测到登录按钮，cookie已失效")
                await context.close()
                await browser.close()
                return False
            
            # 检查是否有用户名元素
            username_elements = [
                page.locator(".h-name"),
                page.locator(".user-name"),
                page.locator(".bili-avatar"),
                page.locator("span.name")
            ]
            
            for elem in username_elements:
                if await elem.count() > 0:
                    bilibili_logger.info("检测到用户名元素，cookie有效")
                    await context.close()
                    await browser.close()
                    return True
            
            # 如果无法通过UI元素判断，尝试访问创作中心
            bilibili_logger.info("尝试访问创作中心验证登录状态...")
            await page.goto("https://member.bilibili.com/platform/upload/video")
            await page.wait_for_load_state("networkidle")
            
            # 检查URL是否被重定向到登录页面
            current_url = page.url
            if "passport.bilibili.com/login" in current_url:
                bilibili_logger.info("被重定向到登录页面，cookie已失效")
                await context.close()
                await browser.close()
                return False
            
            # 检查是否能看到上传按钮
            upload_button = page.locator("button:has-text('上传视频')").first
            if await upload_button.count() > 0:
                bilibili_logger.info("检测到上传按钮，cookie有效")
                await context.close()
                await browser.close()
                return True
            
            # 如果以上方法都无法确认，默认认为cookie无效
            bilibili_logger.info("无法确认cookie状态，默认认为已失效")
            await context.close()
            await browser.close()
            return False
            
        except Exception as e:
            bilibili_logger.error(f"验证cookie时发生错误: {str(e)}")
            await browser.close()
            return False


async def bilibili_setup(account_file, handle=False):
    """设置B站上传环境"""
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # 如果不处理，直接返回False
            return False
        bilibili_logger.info('[+] cookie文件不存在或已失效，请手动更新cookie文件')
        # 这里可以添加自动获取cookie的功能，类似于小红书的实现
        # await bilibili_cookie_gen(account_file)
        return False
    return True


def random_emoji():
    """生成随机表情符号，用于标题装饰"""
    emoji_list = ["🍏", "🍎", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🍈", "🍒", "🍑", "🍍", "🥭", "🥥", "🥝",
                  "🍅", "🍆", "🥑", "🥦", "🥒", "🥬", "🌶", "🌽", "🥕", "🥔", "🍠", "🥐", "🍞", "🥖", "🥨", "🥯", "🧀", "🥚", "🍳", "🥞",
                  "🥓", "🥩", "🍗", "🍖", "🌭", "🍔", "🍟", "🍕", "🥪", "🥙", "🌮", "🌯", "🥗", "🥘", "🥫", "🍝", "🍜", "🍲", "🍛", "🍣",
                  "🍱", "🥟", "🍤", "🍙", "🍚", "🍘", "🍥", "🥮", "🥠", "🍢", "🍡", "🍧", "🍨", "🍦", "🥧", "🍰", "🎂", "🍮", "🍭", "🍬",
                  "🍫", "🍿", "🧂", "🍩", "🍪", "🌰", "🥜", "🍯", "🥛", "🍼", "☕️", "🍵", "🥤", "🍶", "🍻", "🥂", "🍷", "🥃", "🍸", "🍹",
                  "🍾", "🥄", "🍴", "🍽", "🥣", "🥡", "🥢"]
    return random.choice(emoji_list)


class BilibiliVideo(object):
    def __init__(self, title, file_path, desc, tid, tags, publish_date: datetime, account_file, thumbnail_path=None):
        self.title = title  # 视频标题
        self.file_path = file_path  # 视频文件路径
        self.desc = desc  # 视频描述
        self.tid = tid  # 视频分区ID
        self.tags = tags  # 视频标签
        self.publish_date = publish_date  # 发布时间
        self.account_file = account_file  # cookie文件
        self.thumbnail_path = thumbnail_path  # 封面图片路径
        self.local_executable_path = LOCAL_CHROME_PATH  # 本地Chrome路径
        self.copyright = 1  # 版权声明：1-原创，2-转载
        self.source = ""  # 转载来源，copyright=2时需要填写

    async def set_schedule_time(self, page, publish_date):
        """设置定时发布时间"""
        bilibili_logger.info("  [-] 正在设置定时发布时间...")
        
        # 点击定时发布按钮
        await page.locator("span:has-text('定时发布')").click()
        await asyncio.sleep(1)
        
        # 格式化日期时间
        publish_date_str = publish_date.strftime("%Y-%m-%d %H:%M")
        bilibili_logger.info(f"  [-] 设置发布时间: {publish_date_str}")
        
        # 点击日期选择器
        date_selector = page.locator("input.el-input__inner[placeholder='选择日期时间']")
        await date_selector.click()
        
        # 清除默认值并输入新日期
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(publish_date_str)
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)

    async def handle_upload_error(self, page):
        """处理上传错误"""
        bilibili_logger.info('  [-] 视频上传出错，尝试重新上传...')
        # 点击重新上传按钮
        retry_button = page.locator("button:has-text('重新上传')")
        if await retry_button.count() > 0:
            await retry_button.click()
            await asyncio.sleep(1)
            # 重新选择文件上传
            file_input = page.locator("input[type='file']")
            await file_input.set_input_files(self.file_path)
        else:
            bilibili_logger.error('  [-] 未找到重新上传按钮，请手动处理')

    async def click_submit_button(self, page):
        """专门处理B站提交按钮点击"""
        bilibili_logger.info("[-] 尝试点击B站提交按钮...")
        
        # 记录当前URL，用于后续判断是否成功提交
        start_url = page.url
        bilibili_logger.info(f"[-] 当前页面URL: {start_url}")
        
        # 尝试多种方式点击提交按钮
        success = False
        
        # 方法1: 尝试直接定位span.submit-add元素
        try:
            bilibili_logger.info("[-] 方法1: 尝试直接定位span.submit-add元素")
            span_selectors = [
                "span.submit-add[data-reporter-id='28']",
                "span.submit-add",
                "span[data-reporter-id='28']"
            ]
            
            for selector in span_selectors:
                try:
                    submit_span = page.locator(selector)
                    if await submit_span.count() > 0:
                        # 使用force=True强制点击
                        await submit_span.click(force=True)
                        bilibili_logger.info(f"[-] 成功点击span元素: {selector}")
                        await asyncio.sleep(5)
                        success = await self.check_submit_success(page, start_url)
                        if success:
                            return True
                except Exception as e:
                    bilibili_logger.info(f"[-] 点击span元素 {selector} 失败: {str(e)}")
        except Exception as e:
            bilibili_logger.error(f"[-] 点击span元素失败: {str(e)}")
        
        # 方法2: 直接使用JavaScript点击所有可能的提交按钮
        try:
            bilibili_logger.info("[-] 方法2: 使用JavaScript点击所有可能的提交按钮")
            clicked = await page.evaluate("""() => {
                // 查找所有按钮和span元素
                const buttons = Array.from(document.querySelectorAll('button, span.submit-add, span[data-reporter-id="28"]'));
                
                // 首先尝试直接匹配span.submit-add元素
                const submitSpan = buttons.find(el => 
                    el.tagName.toLowerCase() === 'span' && 
                    (el.className.includes('submit-add') || el.getAttribute('data-reporter-id') === '28')
                );
                
                if (submitSpan) {
                    console.log('点击span元素:', submitSpan.textContent.trim());
                    submitSpan.click();
                    return { clicked: true, text: submitSpan.textContent.trim(), element: 'span' };
                }
                
                // 按钮文本优先级
                const buttonTexts = ['立即投稿', '投稿', '发布', '提交', '确认', '确定'];
                
                // 遍历所有可能的按钮文本
                for (const text of buttonTexts) {
                    // 查找包含指定文本的按钮
                    const button = buttons.find(b => (b.textContent || '').includes(text));
                    if (button) {
                        console.log('点击按钮:', button.textContent.trim());
                        button.click();
                        return { clicked: true, text: button.textContent.trim(), element: button.tagName.toLowerCase() };
                    }
                }
                
                // 如果没有找到匹配的按钮，尝试查找类名包含submit的按钮
                const submitButton = buttons.find(b => {
                    const className = b.className || '';
                    return (className.includes('submit') || className.includes('primary')) && !className.includes('add');
                });
                
                if (submitButton) {
                    console.log('点击类名匹配的按钮:', submitButton.textContent.trim());
                    submitButton.click();
                    return { clicked: true, text: submitButton.textContent.trim(), element: submitButton.tagName.toLowerCase() };
                }
                
                return { clicked: false };
            }""")
            
            if clicked and clicked.get('clicked'):
                element_type = clicked.get('element', 'button')
                button_text = clicked.get('text', '')
                bilibili_logger.info(f"[-] JavaScript成功点击{element_type}元素: {button_text}")
                await asyncio.sleep(5)  # 等待点击后的反应
                success = await self.check_submit_success(page, start_url)
                if success:
                    return True
        except Exception as e:
            bilibili_logger.error(f"[-] JavaScript点击失败: {str(e)}")
        
        # 方法3: 使用Playwright的强制点击
        if not success:
            try:
                bilibili_logger.info("[-] 方法3: 使用Playwright强制点击")
                # 尝试多个选择器
                for selector in [
                    "button:has-text('立即投稿')",
                    "button:has-text('投稿')",
                    "button:has-text('发布')",
                    ".submit-btn",
                    "button.primary-btn"
                ]:
                    try:
                        button = page.locator(selector).first
                        if await button.count() > 0:
                            # 使用force=True强制点击
                            await button.click(force=True)
                            bilibili_logger.info(f"[-] 强制点击按钮: {selector}")
                            await asyncio.sleep(5)
                            success = await self.check_submit_success(page, start_url)
                            if success:
                                return True
                    except Exception as e:
                        bilibili_logger.info(f"[-] 强制点击 {selector} 失败: {str(e)}")
            except Exception as e:
                bilibili_logger.error(f"[-] 强制点击失败: {str(e)}")
        
        # 方法4: 使用键盘Tab和Enter
        if not success:
            try:
                bilibili_logger.info("[-] 方法4: 使用键盘Tab和Enter")
                # 先点击页面底部，然后使用Tab键导航到提交按钮
                await page.keyboard.press('End')  # 移动到页面底部
                await asyncio.sleep(1)
                
                # 按几次Tab键尝试聚焦到提交按钮
                for _ in range(10):
                    await page.keyboard.press('Tab')
                    await asyncio.sleep(0.5)
                
                # 按Enter键尝试点击
                await page.keyboard.press('Enter')
                bilibili_logger.info("[-] 使用键盘Enter尝试点击")
                await asyncio.sleep(5)
                success = await self.check_submit_success(page, start_url)
                if success:
                    return True
            except Exception as e:
                bilibili_logger.error(f"[-] 键盘操作失败: {str(e)}")
        
        # 最后一次检查是否提交成功
        return await self.check_submit_success(page, start_url)

    async def check_submit_success(self, page, start_url):
        """检查是否提交成功"""
        try:
            bilibili_logger.info("[-] 检查是否提交成功...")
             
            # 检查1: 检查是否有成功提示文本
            success_texts = ["提交成功", "已提交", "上传成功", "投稿成功", "稿件提交成功"]
            for text in success_texts:
                try:
                    success_elem = page.locator(f"text={text}")
                    if await success_elem.count() > 0:
                        bilibili_logger.success(f"[+] 检测到成功提示: '{text}'")
                        return True
                except:
                    pass
            
            # 检查2: 检查URL是否变化
            current_url = page.url
            if current_url != start_url:
                bilibili_logger.info(f"[-] 页面URL已变化，可能已提交成功: {current_url}")
                
                # 如果URL包含成功相关的参数，更可能是成功了
                if "success" in current_url or "submitted" in current_url:
                    bilibili_logger.success("[+] URL包含成功相关参数，提交可能成功!")
                    return True
                
                # 检查是否是B站上传成功后的frame页面
                if "platform/upload/video/frame" in current_url:
                    bilibili_logger.success("[+] 已跳转到frame页面，提交可能成功!")
                    return True
            
            # 检查3: 检查是否返回到视频管理页面
            if "member.bilibili.com/platform/upload/video/manage" in current_url:
                bilibili_logger.success("[+] 已返回到视频管理页面，提交成功!")
                return True
            
            # 检查4: 检查是否有成功状态元素
            try:
                # 尝试查找可能表示成功的元素
                success_selectors = [
                    ".success-info", 
                    ".success-message", 
                    ".success-icon",
                    ".upload-success",
                    ".result-success"
                ]
                
                for selector in success_selectors:
                    elem = page.locator(selector)
                    if await elem.count() > 0:
                        bilibili_logger.success(f"[+] 检测到成功元素: {selector}")
                        return True
            except:
                pass
            
            # 检查5: 使用JavaScript检查页面状态
            try:
                is_success = await page.evaluate("""() => {
                    // 检查页面文本是否包含成功相关词语
                    const pageText = document.body.innerText;
                    const successTexts = ['提交成功', '已提交', '上传成功', '投稿成功', '视频已上传', '稿件提交成功'];
                    
                    for (const text of successTexts) {
                        if (pageText.includes(text)) {
                            return { success: true, reason: `包含文本: ${text}` };
                        }
                    }
                    
                    // 检查是否有成功图标
                    const successIcons = document.querySelectorAll('.success-icon, .icon-success, .icon-check');
                    if (successIcons.length > 0) {
                        return { success: true, reason: '找到成功图标' };
                    }
                    
                    return { success: false };
                }""")
                
                if is_success and is_success.get('success'):
                    bilibili_logger.success(f"[+] JavaScript检测到成功状态: {is_success.get('reason', '')}")
                    return True
            except:
                pass
            
            # 检查6: 检查是否有需要额外确认的对话框
            try:
                # 检查是否有确认对话框
                confirm_buttons = [
                    "button:has-text('确认')",
                    "button:has-text('确定')",
                    "button:has-text('是')",
                    "button:has-text('提交')",
                    "button:has-text('投稿')",
                    "span.submit-add",
                    "span[data-reporter-id='28']"
                ]
                
                for selector in confirm_buttons:
                    button = page.locator(selector)
                    if await button.count() > 0 and await button.is_visible():
                        bilibili_logger.info(f"[-] 检测到确认按钮: {selector}，尝试点击")
                        await button.click()
                        await asyncio.sleep(3)
                        # 再次检查是否成功
                        return await self.check_submit_success(page, start_url)
            except Exception as e:
                bilibili_logger.info(f"[-] 检查确认对话框失败: {str(e)}")
            
            bilibili_logger.warning("[-] 未检测到明确的成功状态")
            return False
        except Exception as e:
            bilibili_logger.error(f"[-] 检查提交结果失败: {str(e)}")
            return False

    async def ensure_video_submitted(self, page, browser, context):
        """确保视频真正提交成功"""
        bilibili_logger.info("[-] 确保视频真正提交成功...")
        
        # 检查是否有任何确认对话框或按钮需要点击
        confirm_selectors = [
            "button:has-text('确认')",
            "button:has-text('确定')",
            "button:has-text('是')",
            "button:has-text('提交')",
            "button:has-text('投稿')",
            "span.submit-add",
            "span[data-reporter-id='28']"
        ]
        
        for selector in confirm_selectors:
            try:
                button = page.locator(selector)
                if await button.count() > 0 and await button.is_visible():
                    bilibili_logger.info(f"[-] 发现需要点击的按钮: {selector}")
                    await button.click(force=True)
                    await asyncio.sleep(3)
            except Exception as e:
                bilibili_logger.info(f"[-] 点击按钮 {selector} 失败: {str(e)}")
        
        # 使用JavaScript检查页面状态，查找是否有任何提交按钮或确认按钮
        try:
            buttons = await page.evaluate("""() => {
                const allButtons = Array.from(document.querySelectorAll('button, span.submit-add'));
                return allButtons
                    .filter(b => {
                        const text = b.textContent || '';
                        return (
                            text.includes('确认') || 
                            text.includes('确定') || 
                            text.includes('提交') || 
                            text.includes('投稿') ||
                            (b.className && b.className.includes('submit-add'))
                        ) && b.offsetParent !== null; // 只返回可见按钮
                    })
                    .map(b => ({
                        text: b.textContent.trim(),
                        tag: b.tagName.toLowerCase(),
                        visible: b.offsetParent !== null
                    }));
            }""")
            
            if buttons and len(buttons) > 0:
                bilibili_logger.info(f"[-] 发现可能需要点击的按钮: {buttons}")
                
                # 尝试点击这些按钮
                await page.evaluate("""() => {
                    const allButtons = Array.from(document.querySelectorAll('button, span.submit-add'));
                    const visibleButtons = allButtons.filter(b => {
                        const text = b.textContent || '';
                        return (
                            text.includes('确认') || 
                            text.includes('确定') || 
                            text.includes('提交') || 
                            text.includes('投稿') ||
                            (b.className && b.className.includes('submit-add'))
                        ) && b.offsetParent !== null;
                    });
                    
                    if (visibleButtons.length > 0) {
                        console.log('点击按钮:', visibleButtons[0].textContent.trim());
                        visibleButtons[0].click();
                    }
                }""")
                await asyncio.sleep(3)
        except Exception as e:
            bilibili_logger.error(f"[-] 检查并点击按钮失败: {str(e)}")
        
        # 等待较长时间，确保提交完成
        bilibili_logger.info("[-] 等待10秒，确保提交完成...")
        await asyncio.sleep(10)
        
        # 最后一次保存页面截图
        await page.screenshot(path=f"bilibili_final_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        # 检查当前URL是否是frame页面
        current_url = page.url
        if "platform/upload/video/frame" in current_url:
            bilibili_logger.success("[+] 已跳转到frame页面，判定为提交成功!")
            return True
            
        # 检查是否真正成功
        return await self.check_submit_success(page, "")

    async def set_thumbnail(self, page: Page):
        """设置视频封面"""
        if not self.thumbnail_path:
            bilibili_logger.info("  [-] 未指定封面，使用系统自动生成的封面")
            return
            
        bilibili_logger.info("  [-] 正在设置自定义封面...")
        try:
            # 点击自定义封面按钮
            custom_cover_button = page.locator("span:has-text('自定义封面')")
            await custom_cover_button.click()
            await asyncio.sleep(1)
            
            # 上传封面文件
            cover_input = page.locator("input[type='file'][accept='image/jpeg,image/png,image/gif,image/webp']")
            await cover_input.set_input_files(self.thumbnail_path)
            
            # 等待上传完成
            await page.wait_for_selector("text=上传成功", timeout=10000)
            bilibili_logger.info("  [-] 封面设置成功")
            
            # 点击确认按钮
            confirm_button = page.locator("button:has-text('确定')")
            await confirm_button.click()
            await asyncio.sleep(1)
        except Exception as e:
            bilibili_logger.error(f"  [-] 设置封面失败: {str(e)}")

    async def upload(self, playwright: Playwright) -> bool:
        """上传视频到B站"""
        # 检查并转换视频格式（如果需要）
        bilibili_logger.info(f"🔍 检查视频格式兼容性...")
        converted_file_path = convert_video_if_needed(self.file_path, platform="bilibili")
        if converted_file_path != self.file_path:
            bilibili_logger.info(f"✅ 使用转换后的视频文件: {os.path.basename(converted_file_path)}")
            # 临时更新文件路径
            self.file_path = converted_file_path
        
        try:
            # 启动浏览器
            browser_options = {
                'headless': False,
                'slow_mo': 100  # 减慢操作速度，增加稳定性
            }
            
            if self.local_executable_path:
                browser_options['executable_path'] = self.local_executable_path
                
            browser = await playwright.chromium.launch(**browser_options)
                
            # 创建浏览器上下文
            context = await browser.new_context(
                viewport={"width": 1600, "height": 900},
                storage_state=self.account_file
            )
            context = await set_init_script(context)
            
            # 创建新页面
            page = await context.new_page()
            
            # 设置页面默认超时时间
            page.set_default_timeout(60000)  # 60秒
            
            # 访问B站创作中心
            bilibili_logger.info(f'[+] 正在上传视频: {os.path.basename(self.file_path)}')
            bilibili_logger.info(f'[-] 正在打开B站创作中心...')
            
            try:
                # 访问B站创作中心
                await page.goto("https://member.bilibili.com/platform/upload/video", timeout=60000)
                
                # 等待页面加载完成
                bilibili_logger.info(f'[-] 等待页面加载完成...')
                await page.wait_for_load_state("networkidle", timeout=60000)
                
                # 检查是否被重定向到登录页面
                current_url = page.url
                if "passport.bilibili.com/login" in current_url:
                    bilibili_logger.error("[-] 被重定向到登录页面，cookie可能已失效")
                    await browser.close()
                    return False
                
                # 保存页面截图，用于调试
                bilibili_logger.info("[-] 保存页面截图用于调试...")
                
                # 等待页面元素加载完成
                bilibili_logger.info("[-] 等待页面元素加载...")
                
                # 尝试多种可能的文件输入选择器
                file_input_selectors = [
                    "#video-up-app input[type='file'][accept*='.mp4']",
                    "#b-uploader-input-container_BUploader_0 input[type='file']",
                    "input[type='file'][accept*='.mp4']:first-child",
                    "input[type='file'][multiple='multiple']"
                ]
                
                file_input = None
                for selector in file_input_selectors:
                    try:
                        bilibili_logger.info(f"[-] 尝试查找上传按钮: {selector}")
                        temp_input = page.locator(selector)
                        count = await temp_input.count()
                        if count > 0:
                            bilibili_logger.info(f"[-] 找到上传按钮: {selector}，匹配数量: {count}")
                            if count == 1:
                                file_input = temp_input
                                break
                            else:
                                # 如果有多个匹配，选择第一个
                                bilibili_logger.info(f"[-] 多个匹配，选择第一个元素")
                                file_input = temp_input.first
                                break
                    except Exception as e:
                        bilibili_logger.info(f"[-] 未找到选择器 {selector}: {str(e)}")
                
                if not file_input:
                    # 尝试使用JavaScript获取上传按钮
                    bilibili_logger.info("[-] 尝试使用JavaScript获取上传按钮...")
                    try:
                        file_input_js = await page.evaluate("""() => {
                            // 查找所有接受视频文件的input元素
                            const inputs = Array.from(document.querySelectorAll('input[type="file"]'));
                            // 过滤出接受视频文件的input
                            const videoInputs = inputs.filter(input => {
                                const accept = input.getAttribute('accept') || '';
                                return accept.includes('.mp4') || accept.includes('video');
                            });
                            // 返回第一个视频输入元素的选择器
                            if (videoInputs.length > 0) {
                                let input = videoInputs[0];
                                let path = '';
                                while (input && input !== document.body) {
                                    let selector = input.tagName.toLowerCase();
                                    if (input.id) {
                                        selector += '#' + input.id;
                                        path = selector + (path ? ' > ' + path : '');
                                        break;
                                    } else {
                                        let sibling = input, nth = 0;
                                        while (sibling) {
                                            if (sibling.nodeType === Node.ELEMENT_NODE) nth++;
                                            sibling = sibling.previousSibling;
                                        }
                                        selector += ':nth-child(' + nth + ')';
                                    }
                                    path = selector + (path ? ' > ' + path : '');
                                    input = input.parentNode;
                                }
                                return path;
                            }
                            return null;
                        }""")
                        
                        if file_input_js:
                            bilibili_logger.info(f"[-] JavaScript找到上传按钮: {file_input_js}")
                            file_input = page.locator(file_input_js)
                    except Exception as e:
                        bilibili_logger.error(f"[-] JavaScript获取上传按钮失败: {str(e)}")
                
                if not file_input:
                    bilibili_logger.error("[-] 无法找到文件上传按钮")
                    await page.screenshot(path=f"bilibili_error_no_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    await browser.close()
                    return False
                
            except Exception as e:
                bilibili_logger.error(f"[-] 页面加载失败: {str(e)}")
                # 尝试截图保存错误状态
                try:
                    await page.screenshot(path=f"bilibili_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    bilibili_logger.info("[-] 已保存错误截图")
                except:
                    pass
                await browser.close()
                return False
            
            # 上传视频文件
            bilibili_logger.info(f'[-] 正在上传视频文件...')
            try:
                await file_input.set_input_files(self.file_path)
                bilibili_logger.info(f'[-] 文件已选择，等待上传...')
            except Exception as e:
                bilibili_logger.error(f"[-] 文件上传失败: {str(e)}")
                await browser.close()
                return False
            
            # 等待视频上传完成
            bilibili_logger.info(f'[-] 等待视频上传完成...')
            upload_success = False
            upload_timeout = 600  # 10分钟上传超时
            start_time = time.time()
            
            while time.time() - start_time < upload_timeout:
                try:
                    # 检查是否出现上传完成的提示
                    success_text = page.locator("text=上传完成")
                    if await success_text.count() > 0:
                        bilibili_logger.info("[-] 视频上传完成!")
                        upload_success = True
                        break
                    
                    # 检查是否出现上传失败的提示
                    failed_text = page.locator("text=上传失败")
                    if await failed_text.count() > 0:
                        await self.handle_upload_error(page)
                        await asyncio.sleep(2)
                        continue
                    
                    # 继续等待
                    bilibili_logger.info("[-] 视频正在上传中...")
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    bilibili_logger.error(f"[-] 上传过程出错: {str(e)}")
                    await asyncio.sleep(2)
            
            if not upload_success:
                bilibili_logger.error("[-] 视频上传超时")
                await browser.close()
                return False
            
            # 等待一段时间，让页面完成处理
            bilibili_logger.info("[-] 等待页面处理上传的视频...")
            await asyncio.sleep(5)
            
            # 填写视频信息
            bilibili_logger.info(f'[-] 正在填写视频信息...')
            
            try:    
                # 填写标题
                bilibili_logger.info("[-] 填写视频标题...")
                title_selectors = [
                    "input[placeholder='请输入稿件标题']",
                    ".title-input input",
                    "#video-title-input"
                ]
                
                title_input = None
                for selector in title_selectors:
                    try:
                        temp_input = page.locator(selector)
                        if await temp_input.count() > 0:
                            title_input = temp_input
                            bilibili_logger.info(f"[-] 找到标题输入框: {selector}")
                            break
                    except:
                        pass
                
                if title_input:
                    await title_input.fill(self.title)
                else:
                    bilibili_logger.warning("[-] 未找到标题输入框，尝试使用JavaScript填写...")
                    await page.evaluate(f"""() => {{
                        const inputs = Array.from(document.querySelectorAll('input'));
                        const titleInput = inputs.find(input => 
                            input.placeholder === '请输入稿件标题' || 
                            input.id === 'video-title-input' ||
                            (input.className && input.className.includes('title'))
                        );
                        if (titleInput) titleInput.value = "{self.title}";
                    }}""")
                
                # 选择分区
                bilibili_logger.info(f'[-] 选择分区: {self.tid}')
                
                # 尝试多种方式选择分区
                try:
                    # 方法1: 点击分区选择器
                    category_selectors = [
                        "div.select-box-v2-container",
                        ".category-v2-container",
                        ".category-container"
                    ]
                    
                    category_clicked = False
                    for selector in category_selectors:
                        try:
                            category = page.locator(selector).first
                            if await category.count() > 0:
                                bilibili_logger.info(f"[-] 找到分区选择器: {selector}")
                                await category.click()
                                category_clicked = True
                                await asyncio.sleep(2)
                                break
                        except:
                            pass
                    
                    # 方法2: 如果无法点击分区选择器，尝试直接使用JavaScript设置分区
                    if not category_clicked:
                        bilibili_logger.info("[-] 尝试使用JavaScript设置分区...")
                        await page.evaluate(f"""() => {{
                            // 尝试查找分区相关元素并设置
                            const tidValue = {self.tid};
                            // 这里的实现取决于B站的具体页面结构
                            // 可能需要根据实际情况调整
                            const event = new Event('change', {{ bubbles: true }});
                            const tidInputs = Array.from(document.querySelectorAll('input[type="hidden"]')).filter(i => i.name === 'tid' || i.id === 'tid');
                            if (tidInputs.length > 0) {{
                                tidInputs[0].value = tidValue;
                                tidInputs[0].dispatchEvent(event);
                                return true;
                            }}
                            return false;
                        }}""")
                except Exception as e:
                    bilibili_logger.warning(f"[-] 设置分区失败: {str(e)}")
                
                # 填写视频简介
                bilibili_logger.info("[-] 填写视频简介...")
                desc_selectors = [
                    "textarea[placeholder='填写更全面的相关信息，让更多的人能找到你的视频吧～']",
                    ".desc-v2-container textarea",
                    "#video-desc-editor"
                ]
                
                desc_input = None
                for selector in desc_selectors:
                    try:
                        temp_input = page.locator(selector)
                        if await temp_input.count() > 0:
                            desc_input = temp_input
                            bilibili_logger.info(f"[-] 找到简介输入框: {selector}")
                            break
                    except:
                        pass
                
                if desc_input:
                    await desc_input.fill(self.desc)
                else:
                    bilibili_logger.warning("[-] 未找到简介输入框，尝试使用JavaScript填写...")
                    await page.evaluate(f"""() => {{
                        const textareas = Array.from(document.querySelectorAll('textarea'));
                        const descInput = textareas.find(textarea => 
                            textarea.placeholder && textarea.placeholder.includes('相关信息') || 
                            textarea.id === 'video-desc-editor'
                        );
                        if (descInput) descInput.value = "{self.desc}";
                    }}""")
                
                # 添加标签
                if self.tags and len(self.tags) > 0:
                    bilibili_logger.info(f'[-] 添加标签: {", ".join(self.tags)}')
                    tag_selectors = [
                        "input[placeholder='按回车键Enter创建标签']",
                        ".tag-input-container input",
                        "#video-tag-input"
                    ]
                    
                    tag_input = None
                    for selector in tag_selectors:
                        try:
                            temp_input = page.locator(selector)
                            if await temp_input.count() > 0:
                                tag_input = temp_input
                                bilibili_logger.info(f"[-] 找到标签输入框: {selector}")
                                break
                        except:
                            pass
                    
                    if tag_input:
                        for tag in self.tags:
                            await tag_input.fill(tag)
                            await page.keyboard.press("Enter")
                            await asyncio.sleep(0.5)
                    else:
                        bilibili_logger.warning("[-] 未找到标签输入框")
                
                # 设置封面
                if self.thumbnail_path:
                    bilibili_logger.info("[-] 设置自定义封面...")
                    try:
                        # 尝试多种可能的封面上传按钮选择器
                        cover_selectors = [
                            "span:has-text('自定义封面')",
                            ".cover-v2-container button",
                            ".cover-upload-btn"
                        ]
                        
                        cover_button = None
                        for selector in cover_selectors:
                            try:
                                temp_button = page.locator(selector)
                                if await temp_button.count() > 0:
                                    cover_button = temp_button
                                    bilibili_logger.info(f"[-] 找到封面上传按钮: {selector}")
                                    break
                            except:
                                pass
                        
                        if cover_button:
                            await cover_button.click()
                            await asyncio.sleep(1)
                            
                            # 尝试多种可能的文件输入选择器
                            cover_input_selectors = [
                                "input[type='file'][accept*='image']",
                                "input[type='file'][accept*='jpeg']",
                                ".cover-upload-container input[type='file']"
                            ]
                            
                            cover_input = None
                            for selector in cover_input_selectors:
                                try:
                                    temp_input = page.locator(selector)
                                    if await temp_input.count() > 0:
                                        cover_input = temp_input
                                        bilibili_logger.info(f"[-] 找到封面文件输入: {selector}")
                                        break
                                except:
                                    pass
                            
                            if cover_input:
                                await cover_input.set_input_files(self.thumbnail_path)
                                
                                # 等待上传完成
                                try:
                                    await page.wait_for_selector("text=上传成功", timeout=10000)
                                    bilibili_logger.info("[-] 封面设置成功")
                                    
                                    # 点击确认按钮
                                    confirm_selectors = [
                                        "button:has-text('确定')",
                                        ".cover-modal-footer button:last-child",
                                        ".modal-footer button:last-child"
                                    ]
                                    
                                    for selector in confirm_selectors:
                                        try:
                                            confirm_button = page.locator(selector)
                                            if await confirm_button.count() > 0:
                                                await confirm_button.click()
                                                await asyncio.sleep(1)
                                                break
                                        except:
                                            pass
                                except:
                                    bilibili_logger.warning("[-] 等待封面上传完成超时")
                            else:
                                bilibili_logger.warning("[-] 未找到封面文件输入")
                        else:
                            bilibili_logger.warning("[-] 未找到封面上传按钮")
                    except Exception as e:
                        bilibili_logger.error(f"[-] 设置封面失败: {str(e)}")
                else:
                    bilibili_logger.info("[-] 未指定封面，使用系统自动生成的封面")
                
                # 设置版权信息
                bilibili_logger.info("[-] 设置版权信息...")
                if self.copyright == 2 and self.source:
                    # 选择转载
                    copyright_selectors = ["label:has-text('转载')", ".copyright-v2-container label:nth-child(2)"]
                    for selector in copyright_selectors:
                        try:
                            copyright_btn = page.locator(selector)
                            if await copyright_btn.count() > 0:
                                await copyright_btn.click()
                                await asyncio.sleep(1)
                                
                                # 填写转载来源
                                source_input = page.locator("input[placeholder='填写转载来源']")
                                if await source_input.count() > 0:
                                    await source_input.fill(self.source)
                                break
                        except:
                            pass
                else:
                    # 选择自制
                    copyright_selectors = ["label:has-text('自制')", ".copyright-v2-container label:nth-child(1)"]
                    for selector in copyright_selectors:
                        try:
                            copyright_btn = page.locator(selector)
                            if await copyright_btn.count() > 0:
                                await copyright_btn.click()
                                await asyncio.sleep(1)
                                break
                        except:
                            pass
                
                # 设置定时发布
                if self.publish_date:
                    await self.set_schedule_time(page, self.publish_date)
                
                # 提交视频
                bilibili_logger.info(f'[-] 提交视频...')
                
                # 使用专门的方法处理提交按钮点击
                submit_success = await self.click_submit_button(page)
                success = False
                
                if submit_success:
                    bilibili_logger.success("[+] 使用专用方法成功点击提交按钮!")
                    # 等待较长时间，确保提交完成
                    bilibili_logger.info("[-] 等待5秒，确保提交进行中...")
                    await asyncio.sleep(5)
                    
                    # 确保视频真正提交成功
                    success = await self.ensure_video_submitted(page, browser, context)
                    if success:
                        bilibili_logger.success("[+] 视频已真正提交成功!")
                    else:
                        bilibili_logger.warning("[-] 无法确认视频是否真正提交成功，尝试常规方法...")
                
                if not success:
                    bilibili_logger.warning("[-] 专用方法未能成功点击提交按钮，尝试常规方法...")
                    
                    # 查找提交按钮
                    submit_button = None
                    submit_selectors = []
                    
                    if self.publish_date:
                        # 定时发布
                        submit_selectors = [
                            "button:has-text('立即定时')",
                            ".submit-container button:last-child",
                            ".submit-btn",
                            "button.submit-btn",
                            "button[class*='submit']"
                        ]
                    else:
                        # 立即发布 - 增加更多可能的选择器
                        submit_selectors = [
                            "span.submit-add[data-reporter-id='28']",  # 精确匹配用户提供的HTML结构
                            "span.submit-add",  # 匹配class
                            "span[data-reporter-id='28']",  # 匹配data-reporter-id
                            "button:has-text('立即投稿')",
                            "button:text('立即投稿')",
                            "button:text-is('立即投稿')",
                            "button.submit-btn:has-text('立即投稿')",
                            "button[type='submit']:has-text('立即投稿')",
                            "button.primary-btn:has-text('立即投稿')",
                            ".submit-container button:has-text('立即投稿')",
                            ".submit-container button:last-child",
                            ".submit-btn",
                            "button.submit-btn",
                            "button[class*='submit']",
                            "button.primary-btn"
                        ]
                    
                    # 等待更长时间确保按钮已加载
                    await asyncio.sleep(3)
                    
                    for selector in submit_selectors:
                        try:
                            bilibili_logger.info(f"[-] 尝试查找提交按钮: {selector}")
                            temp_button = page.locator(selector)
                            count = await temp_button.count()
                            if count > 0:
                                submit_button = temp_button.first
                                bilibili_logger.info(f"[-] 找到提交按钮: {selector}，匹配数量: {count}")
                                break
                        except Exception as e:
                            bilibili_logger.info(f"[-] 查找选择器 {selector} 失败: {str(e)}")
                    
                    if not submit_button:
                        # 尝试使用JavaScript查找提交按钮
                        bilibili_logger.info("[-] 尝试使用JavaScript查找提交按钮...")
                        try:
                            submit_button_js = await page.evaluate("""() => {
                                // 查找所有按钮元素
                                const buttons = Array.from(document.querySelectorAll('button'));
                                
                                // 查找可能的提交按钮，排除"添加分P"按钮
                                const submitButtons = buttons.filter(button => {
                                    const text = button.textContent || '';
                                    const className = button.className || '';
                                    
                                    // 排除"添加分P"按钮
                                    if (text.includes('添加分P') || text.includes('添加分集')) {
                                        return false;
                                    }
                                    
                                    return (
                                        text.includes('立即投稿') ||
                                        text.includes('投稿') || 
                                        text.includes('发布') || 
                                        text.includes('提交') || 
                                        text.includes('确认') ||
                                        text.includes('确定') ||
                                        text.includes('同意') ||
                                        text.includes('定时') ||
                                        (className.includes('submit') && !className.includes('add')) ||
                                        (className.includes('primary') && !className.includes('add'))
                                    );
                                });
                                
                                // 按优先级排序可能的提交按钮
                                submitButtons.sort((a, b) => {
                                    const textA = a.textContent || '';
                                    const textB = b.textContent || '';
                                    
                                    // 优先选择包含"立即投稿"的按钮
                                    if (textA.includes('立即投稿') && !textB.includes('立即投稿')) return -1;
                                    if (!textA.includes('立即投稿') && textB.includes('立即投稿')) return 1;
                                    
                                    // 其次选择包含"投稿"或"发布"的按钮
                                    if (textA.includes('投稿') && !textB.includes('投稿')) return -1;
                                    if (!textA.includes('投稿') && textB.includes('投稿')) return 1;
                                    if (textA.includes('发布') && !textB.includes('发布')) return -1;
                                    if (!textA.includes('发布') && textB.includes('发布')) return 1;
                                    
                                    return 0;
                                });
                                
                                // 打印找到的按钮文本，用于调试
                                const buttonTexts = submitButtons.map(b => b.textContent.trim());
                                console.log('找到的可能提交按钮:', buttonTexts);
                                
                                // 返回所有匹配按钮的信息
                                if (submitButtons.length > 0) {
                                    return submitButtons.map(button => {
                                        // 记录按钮文本，用于调试
                                        const buttonText = button.textContent.trim();
                                        
                                        // 构建更精确的选择器
                                        let selector = '';
                                        
                                        // 尝试使用data属性构建选择器
                                        const dataAttrs = Array.from(button.attributes)
                                            .filter(attr => attr.name.startsWith('data-'))
                                            .map(attr => `[${attr.name}="${attr.value}"]`)
                                            .join('');
                                        
                                        if (dataAttrs) {
                                            selector = `button${dataAttrs}`;
                                        } else if (button.id) {
                                            selector = `#${button.id}`;
                                        } else if (button.className) {
                                            const classes = button.className.split(' ').filter(c => c).join('.');
                                            if (classes) {
                                                selector = `button.${classes}`;
                                            }
                                        }
                                        
                                        if (!selector) {
                                            // 如果无法构建选择器，使用XPath
                                            let path = '';
                                            let element = button;
                                            while (element && element !== document.body) {
                                                let tag = element.tagName.toLowerCase();
                                                let siblings = Array.from(element.parentNode.children).filter(
                                                    child => child.tagName === element.tagName
                                                );
                                                if (siblings.length > 1) {
                                                    let index = siblings.indexOf(element) + 1;
                                                    tag += `:nth-child(${index})`;
                                                }
                                                path = tag + (path ? ' > ' + path : '');
                                                element = element.parentNode;
                                            }
                                            selector = path;
                                        }
                                        
                                        return {
                                            selector: selector,
                                            text: buttonText,
                                            visible: button.offsetParent !== null, // 检查按钮是否可见
                                            position: {
                                                x: button.getBoundingClientRect().left,
                                                y: button.getBoundingClientRect().top
                                            }
                                        };
                                    });
                                }
                                
                                return [];
                            }""")
                            
                            if submit_button_js and len(submit_button_js) > 0:
                                # 过滤出可见的按钮
                                visible_buttons = [btn for btn in submit_button_js if btn.get('visible', False)]
                                
                                if visible_buttons:
                                    # 优先选择"立即投稿"按钮
                                    priority_buttons = [btn for btn in visible_buttons if '立即投稿' in btn.get('text', '')]
                                    
                                    # 其次选择包含"投稿"或"发布"的按钮
                                    if not priority_buttons:
                                        priority_buttons = [btn for btn in visible_buttons if '投稿' in btn.get('text', '') or '发布' in btn.get('text', '')]
                                    
                                    if priority_buttons:
                                        selected_button = priority_buttons[0]
                                    else:
                                        selected_button = visible_buttons[0]
                                    
                                    selector = selected_button.get('selector')
                                    text = selected_button.get('text')
                                    
                                    bilibili_logger.info(f"[-] JavaScript找到提交按钮: {selector}，文本: {text}")
                                    
                                    # 使用更精确的选择器
                                    if '立即投稿' in text:
                                        # 如果是立即投稿按钮，直接使用文本内容定位
                                        submit_button = page.locator(f"button:has-text('{text}')")
                                    elif '投稿' in text or '发布' in text:
                                        # 如果是投稿或发布按钮，直接使用文本内容定位
                                        submit_button = page.locator(f"button:has-text('{text}')")
                                    else:
                                        # 否则使用构建的选择器，但添加:visible伪类
                                        submit_button = page.locator(f"{selector}:visible").first
                                else:
                                    bilibili_logger.warning("[-] 找到的按钮都不可见，尝试使用直接点击方法")
                                    submit_button = None
                            else:
                                bilibili_logger.warning("[-] JavaScript未找到任何可能的提交按钮")
                                submit_button = None
                        except Exception as e:
                            bilibili_logger.error(f"[-] JavaScript查找提交按钮失败: {str(e)}")
                            submit_button = None
                    
                    if not submit_button:
                        # 最后尝试直接使用JavaScript点击提交按钮
                        bilibili_logger.info("[-] 尝试直接使用JavaScript点击提交按钮...")
                        try:
                            clicked = await page.evaluate("""() => {
                                // 查找所有按钮元素
                                const buttons = Array.from(document.querySelectorAll('button'));
                                
                                // 查找可能的提交按钮，排除"添加分P"按钮
                                const submitButtons = buttons.filter(button => {
                                    const text = button.textContent || '';
                                    const className = button.className || '';
                                    
                                    // 排除"添加分P"按钮
                                    if (text.includes('添加分P') || text.includes('添加分集')) {
                                        return false;
                                    }
                                    
                                    return (
                                        text.includes('立即投稿') ||
                                        text.includes('投稿') || 
                                        text.includes('发布') || 
                                        text.includes('提交') || 
                                        text.includes('确认') ||
                                        text.includes('确定') ||
                                        text.includes('同意') ||
                                        text.includes('定时') ||
                                        (className.includes('submit') && !className.includes('add')) ||
                                        (className.includes('primary') && !className.includes('add'))
                                    );
                                });
                                
                                // 按优先级排序可能的提交按钮
                                submitButtons.sort((a, b) => {
                                    const textA = a.textContent || '';
                                    const textB = b.textContent || '';
                                    
                                    // 优先选择包含"立即投稿"的按钮
                                    if (textA.includes('立即投稿') && !textB.includes('立即投稿')) return -1;
                                    if (!textA.includes('立即投稿') && textB.includes('立即投稿')) return 1;
                                    
                                    // 其次选择包含"投稿"或"发布"的按钮
                                    if (textA.includes('投稿') && !textB.includes('投稿')) return -1;
                                    if (!textA.includes('投稿') && textB.includes('投稿')) return 1;
                                    if (textA.includes('发布') && !textB.includes('发布')) return -1;
                                    if (!textA.includes('发布') && textB.includes('发布')) return 1;
                                    
                                    return 0;
                                });
                                
                                // 打印找到的按钮文本，用于调试
                                const buttonTexts = submitButtons.map(b => b.textContent.trim());
                                console.log('找到的可能提交按钮:', buttonTexts);
                                
                                // 点击第一个匹配的按钮
                                if (submitButtons.length > 0) {
                                    submitButtons[0].click();
                                    return {
                                        clicked: true,
                                        text: submitButtons[0].textContent.trim()
                                    };
                                }
                                
                                return { clicked: false };
                            }""")
                            
                            if clicked and clicked.get('clicked'):
                                button_text = clicked.get('text', '')
                                bilibili_logger.info(f"[-] JavaScript成功点击提交按钮: {button_text}")
                                
                                # 如果点击的是"同意"按钮，可能需要额外的操作
                                if '同意' in button_text:
                                    bilibili_logger.info("[-] 检测到点击了'同意'按钮，等待弹窗后点击'立即投稿'按钮...")
                                    await asyncio.sleep(3)  # 等待弹窗或其他UI元素出现
                                    
                                    # 尝试查找并点击真正的提交按钮
                                    try:
                                        # 方法1: 使用更精确的选择器
                                        submit_button_selectors = [
                                            "span.submit-add[data-reporter-id='28']",  # 精确匹配用户提供的HTML结构
                                            "span.submit-add",  # 匹配class
                                            "span[data-reporter-id='28']",  # 匹配data-reporter-id
                                            "button:has-text('立即投稿')",
                                            "button.submit-btn:has-text('立即投稿')",
                                            "button.primary-btn:has-text('立即投稿')",
                                            "button:has-text('投稿')",
                                            ".submit-container button:last-child"
                                        ]
                                        
                                        for selector in submit_button_selectors:
                                            try:
                                                button = page.locator(selector)
                                                if await button.count() > 0:
                                                    await button.click(force=True)
                                                    bilibili_logger.info(f"[-] 点击了真正的提交按钮: {selector}")
                                                    break
                                            except Exception as e:
                                                bilibili_logger.info(f"[-] 点击选择器 {selector} 失败: {str(e)}")
                                        
                                        # 方法2: 使用JavaScript查找并点击
                                        await page.evaluate("""() => {
                                            // 查找所有按钮和span元素
                                            const elements = Array.from(document.querySelectorAll('button, span.submit-add, span[data-reporter-id="28"]'));
                                            
                                            // 首先尝试直接匹配span.submit-add元素
                                            const submitSpan = elements.find(el => 
                                                el.tagName.toLowerCase() === 'span' && 
                                                (el.className.includes('submit-add') || el.getAttribute('data-reporter-id') === '28')
                                            );
                                            
                                            if (submitSpan) {
                                                console.log('点击span元素:', submitSpan.textContent.trim());
                                                submitSpan.click();
                                                return true;
                                            }
                                            
                                            // 按钮文本优先级
                                            const buttonTexts = ['立即投稿', '投稿', '发布', '提交'];
                                            
                                            for (const text of buttonTexts) {
                                                const button = elements.find(b => (b.textContent || '').includes(text));
                                                if (button) {
                                                    console.log('点击真正的提交按钮:', button.textContent.trim());
                                                    button.click();
                                                    return true;
                                                }
                                            }
                                            
                                            // 如果没有找到匹配的按钮，尝试查找类名包含submit的按钮
                                            const submitButton = elements.find(b => {
                                                const className = b.className || '';
                                                return (className.includes('submit') || className.includes('primary')) && !className.includes('add');
                                            });
                                            
                                            if (submitButton) {
                                                console.log('点击类名匹配的按钮:', submitButton.textContent.trim());
                                                submitButton.click();
                                                return true;
                                            }
                                            
                                            return false;
                                        }""")
                                        bilibili_logger.info("[-] 尝试点击真正的提交按钮")
                                    except Exception as e:
                                        bilibili_logger.error(f"[-] 点击真正的提交按钮失败: {str(e)}")
                                
                                # 等待更长时间来等待提交完成
                                bilibili_logger.info("[-] 等待提交完成...")
                                try:
                                    # 等待成功提示，增加超时时间
                                    await page.wait_for_selector("text=提交成功", timeout=60000)
                                    bilibili_logger.success("[+] 视频提交成功!")
                                    success = True
                                except Exception as e:
                                    bilibili_logger.error(f"[-] 等待提交完成超时: {str(e)}")
                                    
                                    # 检查是否提交成功
                                    success = await self.check_submit_success(page, page.url)
                                    if success:
                                        bilibili_logger.success("[+] 检测到其他成功指标，视频可能已提交成功!")
                                    else:
                                        # 再次尝试点击可能的提交按钮
                                        bilibili_logger.info("[-] 再次尝试点击可能的提交按钮...")
                                        try:
                                            await page.evaluate("""() => {
                                                // 查找所有按钮
                                                const buttons = Array.from(document.querySelectorAll('button'));
                                                
                                                // 查找可能的提交按钮
                                                for (const text of ['投稿', '发布', '提交', '确认', '确定']) {
                                                    const button = buttons.find(b => (b.textContent || '').includes(text));
                                                    if (button) {
                                                        console.log('点击按钮:', button.textContent.trim());
                                                        button.click();
                                                        return true;
                                                    }
                                                }
                                                
                                                return false;
                                            }""")
                                        except Exception as e:
                                            bilibili_logger.error(f"[-] 再次点击提交按钮失败: {str(e)}")
                                            await page.screenshot(path=f"bilibili_no_submit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                                            await browser.close()
                                            return False
                            else:
                                bilibili_logger.error("[-] JavaScript未找到可点击的提交按钮")
                                await page.screenshot(path=f"bilibili_no_submit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                                await browser.close()
                                return False
                        except Exception as e:
                            bilibili_logger.error(f"[-] JavaScript点击提交按钮失败: {str(e)}")
                            await page.screenshot(path=f"bilibili_no_submit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                            await browser.close()
                            return False
                    
                    # 如果找到了提交按钮，尝试点击
                    if submit_button:
                        # 使用Playwright点击按钮
                        try:
                            await submit_button.click()
                            bilibili_logger.info("[-] 成功点击提交按钮")
                        except Exception as e:
                            bilibili_logger.error(f"[-] 点击提交按钮失败: {str(e)}")
                            await page.screenshot(path=f"bilibili_submit_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                            
                            # 尝试使用JavaScript点击
                            bilibili_logger.info("[-] 尝试使用JavaScript点击...")
                            try:
                                await page.evaluate("""() => {
                                    const buttons = Array.from(document.querySelectorAll('button'));
                                    
                                    // 过滤出可能的提交按钮，排除"添加分P"按钮
                                    const submitButton = buttons.find(b => {
                                        const text = b.textContent || '';
                                        // 排除添加分P按钮
                                        if (text.includes('添加分P') || text.includes('添加分集')) {
                                            return false;
                                        }
                                        return (
                                            text.includes('投稿') || 
                                            text.includes('发布') || 
                                            text.includes('提交') || 
                                            text.includes('确认') ||
                                            text.includes('定时')
                                        );
                                    });
                                    
                                    if (submitButton) {
                                        console.log('点击按钮:', submitButton.textContent.trim());
                                        submitButton.click();
                                    }
                                }""")
                            except Exception as e:
                                bilibili_logger.error(f"[-] JavaScript点击失败: {str(e)}")
                                await browser.close()
                                return False
                
                # 等待提交结果
                if not success:  # 如果前面的步骤没有设置success=True
                    try:
                        # 等待成功提示
                        await page.wait_for_selector("text=提交成功", timeout=30000)
                        bilibili_logger.success("[+] 视频提交成功!")
                        success = True
                    except Exception:
                        bilibili_logger.error("[-] 视频提交失败或超时")
                        # 尝试使用其他方式检查是否成功
                        success = await self.check_submit_success(page, "member.bilibili.com/platform/upload/video")
                        if success:
                            bilibili_logger.success("[+] 检测到其他成功指标，视频可能已提交成功!")
                        else:
                            # 最后尝试确保视频真正提交成功
                            success = await self.ensure_video_submitted(page, browser, context)
                            if success:
                                bilibili_logger.success("[+] 视频已真正提交成功!")
                
                # 保存cookie
                try:
                    await context.storage_state(path=self.account_file)
                    bilibili_logger.success('[-] cookie更新完毕！')
                except Exception as e:
                    bilibili_logger.error(f'[-] 保存cookie失败: {str(e)}')
                
                # 关闭浏览器前，确保视频真正提交成功
                if not success:
                    # 最后一次尝试确保视频真正提交成功
                    success = await self.ensure_video_submitted(page, browser, context)
                    if success:
                        bilibili_logger.success("[+] 最终确认：视频已真正提交成功!")
                
                # 关闭浏览器
                try:
                    await asyncio.sleep(2)
                    await context.close()
                    await browser.close()
                except Exception as e:
                    bilibili_logger.error(f'[-] 关闭浏览器失败: {str(e)}')
                
                # 如果页面URL变化了，即使没有明确的成功提示，也可能是成功了
                if not success and "member.bilibili.com/platform/upload/video" not in page.url:
                    bilibili_logger.info(f"[-] 页面URL已变化，视频可能已成功提交")
                    # 特别检查是否是frame页面，这是B站上传成功后的常见跳转
                    if "platform/upload/video/frame" in page.url:
                        bilibili_logger.success("[+] 已跳转到frame页面，判定为提交成功!")
                        return True
                    return True
                
                return success
                
            except Exception as e:
                bilibili_logger.error(f"[-] 填写视频信息失败: {str(e)}")
                # 尝试截图
                try:
                    await page.screenshot(path=f"bilibili_error_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                except:
                    pass
                await browser.close()
                return False
                
        except Exception as e:
            bilibili_logger.error(f"[-] 上传过程发生异常: {str(e)}")
            return False
        finally:
            # 清理转换生成的临时文件
            try:
                cleanup_converted_files()
            except Exception as e:
                bilibili_logger.warning(f"⚠️  清理临时文件时出错: {e}")

    async def main(self):
        """主函数，执行上传流程"""
        async with async_playwright() as playwright:
            return await self.upload(playwright)
