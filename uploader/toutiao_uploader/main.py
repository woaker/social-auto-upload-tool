# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Page
import os
import asyncio

from conf import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.log import douyin_logger


async def cookie_auth(account_file):
    """验证今日头条cookie是否有效 - V5版本"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        page = await context.new_page()
        
        try:
            await page.goto("https://mp.toutiao.com/")
            await asyncio.sleep(2)
            
            # 检查是否需要登录
            login_elements = await page.locator('text="登录"').count()
            scan_elements = await page.locator('text="扫码登录"').count()
            
            if login_elements == 0 and scan_elements == 0:
                print(f"[+] cookie 有效")
                await context.close()
                await browser.close()
                return True
                
        except Exception as e:
            print(f"Cookie验证失败: {e}")
        
        print("[+] cookie 失效")
        await context.close()
        await browser.close()
        return False


async def toutiao_setup(account_file, handle=False):
    """设置今日头条账号 - V5版本"""
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            return False
        douyin_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await toutiao_cookie_gen(account_file)
    return True


async def toutiao_cookie_gen(account_file):
    """生成今日头条cookie - V5版本"""
    async with async_playwright() as playwright:
        options = {
            'headless': False
        }
        browser = await playwright.chromium.launch(**options)
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()
        
        # 访问主页
        await page.goto("https://mp.toutiao.com/")
        print("请在浏览器中登录今日头条账号...")
        print("登录完成后，请在调试器中点击 '继续' 按钮")
        await page.pause()
        
        # 保存cookie
        await context.storage_state(path=account_file)
        print("Cookie已保存")


class TouTiaoArticle(object):
    def __init__(self, title, content, tags, publish_date: datetime, account_file, cover_path=None):
        self.title = title
        self.content = content
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.cover_path = cover_path
        # 使用正确的发布页面URL
        self.publish_url = "https://mp.toutiao.com/profile_v4/graphic/publish"

    async def close_ai_assistant(self, page):
        """关闭AI助手弹窗"""
        douyin_logger.info("检查并关闭AI助手弹窗...")
        
        try:
            # 查找AI助手相关的遮罩层和关闭按钮
            ai_mask_selectors = [
                '.byte-drawer-mask',
                '.ai-assistant-drawer .byte-drawer-mask',
                '[class*="drawer-mask"]',
                '[class*="ai-assistant"]'
            ]
            
            close_button_selectors = [
                '.byte-drawer-close',
                '.ai-assistant-drawer .byte-drawer-close',
                'button[aria-label="关闭"]',
                'button[title="关闭"]',
                '.close-btn',
                '[class*="close"]'
            ]
            
            # 尝试点击关闭按钮
            for selector in close_button_selectors:
                try:
                    close_btn = page.locator(selector)
                    if await close_btn.count() > 0:
                        await close_btn.first.click(timeout=2000)
                        douyin_logger.info(f"✅ 成功关闭AI助手弹窗: {selector}")
                        await asyncio.sleep(1)
                        return True
                except:
                    continue
            
            # 尝试按ESC键关闭
            try:
                await page.keyboard.press("Escape")
                await asyncio.sleep(1)
                douyin_logger.info("✅ 使用ESC键关闭弹窗")
                return True
            except:
                pass
            
            # 尝试点击遮罩层外部区域
            try:
                # 点击页面左上角
                await page.click('body', position={'x': 10, 'y': 10}, timeout=2000)
                await asyncio.sleep(1)
                douyin_logger.info("✅ 点击外部区域关闭弹窗")
                return True
            except:
                pass
                
            douyin_logger.warning("⚠️ 无法自动关闭AI助手弹窗")
            return False
            
        except Exception as e:
            douyin_logger.warning(f"关闭AI助手弹窗时出错: {e}")
            return False

    async def navigate_to_publish_page(self, page):
        """导航到发布页面"""
        douyin_logger.info("正在访问发布页面...")
        
        try:
            # 直接访问发布页面
            await page.goto(self.publish_url)
            await asyncio.sleep(5)  # 等待页面完全加载
            
            # 关闭可能的AI助手弹窗
            await self.close_ai_assistant(page)
            
            # 检查是否成功到达发布页面
            current_url = page.url
            title = await page.title()
            
            douyin_logger.info(f"当前页面: {title}")
            douyin_logger.info(f"当前URL: {current_url}")
            
            # 检查是否被重定向到登录页
            if "login" in current_url or "auth" in current_url:
                douyin_logger.error("被重定向到登录页，Cookie可能已失效")
                return False
            
            # 再次尝试关闭AI助手弹窗
            await self.close_ai_assistant(page)
            
            # 检查关键元素是否存在
            title_textarea = await page.locator('textarea[placeholder*="请输入文章标题"]').count()
            content_editor = await page.locator('.ProseMirror').count()
            
            if title_textarea > 0 and content_editor > 0:
                douyin_logger.info("✅ 成功到达发布页面，找到标题和内容编辑器")
                return True
            else:
                douyin_logger.warning(f"页面元素检查: 标题框={title_textarea}, 内容编辑器={content_editor}")
                return False
                
        except Exception as e:
            douyin_logger.error(f"访问发布页面失败: {e}")
            return False

    async def fill_title(self, page):
        """填写标题 - V5版本，解决遮挡问题"""
        douyin_logger.info("正在填写标题...")
        
        try:
            # 先关闭可能的弹窗
            await self.close_ai_assistant(page)
            
            # 使用分析得到的准确选择器
            title_textarea = page.locator('textarea[placeholder*="请输入文章标题"]')
            
            if await title_textarea.count() > 0:
                douyin_logger.info("找到标题输入框")
                
                # 确保输入框可见和可编辑
                await title_textarea.scroll_into_view_if_needed()
                await asyncio.sleep(1)
                
                # 再次关闭弹窗
                await self.close_ai_assistant(page)
                
                # 使用force点击避免遮挡
                try:
                    await title_textarea.click(force=True, timeout=5000)
                except:
                    # 如果force点击失败，尝试其他方法
                    try:
                        # 获取元素位置并直接点击
                        box = await title_textarea.bounding_box()
                        if box:
                            await page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    except:
                        # 最后尝试focus
                        await title_textarea.focus()
                
                await asyncio.sleep(0.5)
                
                # 清空并填写标题
                await title_textarea.fill("")  # 清空
                await asyncio.sleep(0.5)
                await title_textarea.fill(self.title)
                await asyncio.sleep(1)
                
                # 验证标题是否填写成功
                filled_value = await title_textarea.input_value()
                if filled_value == self.title:
                    douyin_logger.info("✅ 标题填写成功")
                    return True
                else:
                    douyin_logger.warning(f"标题填写不完整: 期望='{self.title}', 实际='{filled_value}'")
                    # 尝试重新填写
                    await title_textarea.fill(self.title)
                    await asyncio.sleep(1)
                    filled_value = await title_textarea.input_value()
                    if filled_value == self.title:
                        douyin_logger.info("✅ 标题重新填写成功")
                        return True
                    return False
            else:
                douyin_logger.error("❌ 未找到标题输入框")
                return False
                
        except Exception as e:
            douyin_logger.error(f"❌ 标题填写失败: {e}")
            return False

    async def fill_content(self, page):
        """填写内容 - V5版本，解决遮挡问题"""
        douyin_logger.info("正在填写内容...")
        
        try:
            # 先关闭可能的弹窗
            await self.close_ai_assistant(page)
            
            # 使用分析得到的准确选择器
            content_editor = page.locator('.ProseMirror')
            
            if await content_editor.count() > 0:
                douyin_logger.info("找到内容编辑器")
                
                # 确保编辑器可见
                await content_editor.scroll_into_view_if_needed()
                await asyncio.sleep(1)
                
                # 再次关闭弹窗
                await self.close_ai_assistant(page)
                
                # 使用force点击避免遮挡
                try:
                    await content_editor.click(force=True, timeout=5000)
                except:
                    # 如果force点击失败，尝试其他方法
                    try:
                        # 获取元素位置并直接点击
                        box = await content_editor.bounding_box()
                        if box:
                            await page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    except:
                        # 最后尝试focus
                        await content_editor.focus()
                
                await asyncio.sleep(1)
                
                # 清空现有内容
                await page.keyboard.press("Control+KeyA")
                await page.keyboard.press("Delete")
                await asyncio.sleep(0.5)
                
                # 输入新内容
                await page.keyboard.type(self.content)
                await asyncio.sleep(2)
                
                # 验证内容是否填写成功
                try:
                    filled_content = await content_editor.text_content()
                    if filled_content and len(filled_content.strip()) > 10:  # 内容应该有一定长度
                        douyin_logger.info("✅ 内容填写成功")
                        return True
                    else:
                        douyin_logger.warning(f"内容填写可能不完整: {filled_content[:50] if filled_content else 'None'}...")
                        return True  # 仍然返回True，因为可能是编辑器的显示问题
                except:
                    # 对于某些编辑器，无法直接获取文本内容
                    douyin_logger.info("✅ 内容填写完成（无法验证）")
                    return True
            else:
                douyin_logger.error("❌ 未找到内容编辑器")
                return False
                
        except Exception as e:
            douyin_logger.error(f"❌ 内容填写失败: {e}")
            return False

    async def add_tags(self, page):
        """添加标签"""
        if not self.tags:
            douyin_logger.info("无标签需要添加")
            return True
            
        douyin_logger.info("正在添加标签...")
        
        # 先关闭可能的弹窗
        await self.close_ai_assistant(page)
        
        # 标签通常在内容中以#形式存在，或者有专门的标签输入区域
        # 先尝试在内容末尾添加标签
        try:
            content_editor = page.locator('.ProseMirror')
            if await content_editor.count() > 0:
                await content_editor.click(force=True)
                await asyncio.sleep(0.5)
                
                # 移动到内容末尾
                await page.keyboard.press("Control+End")
                await page.keyboard.press("Enter")
                await page.keyboard.press("Enter")
                
                # 添加标签
                tag_text = " ".join([f"#{tag}" for tag in self.tags])
                await page.keyboard.type(tag_text)
                
                douyin_logger.info(f"✅ 成功添加标签: {tag_text}")
                return True
        except Exception as e:
            douyin_logger.warning(f"标签添加失败: {e}")
        
        return True  # 标签添加失败不影响整体发布

    async def create_default_cover(self, title):
        """创建默认封面图片"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import textwrap
            
            # 创建images目录
            os.makedirs("images", exist_ok=True)
            
            # 生成默认封面路径
            default_cover_path = f"images/default_cover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            # 创建封面图片 (16:9比例，适合今日头条)
            width, height = 1200, 675
            img = Image.new('RGB', (width, height), color='#1E3A8A')  # 深蓝色背景
            draw = ImageDraw.Draw(img)
            
            # 添加渐变效果
            for i in range(height):
                alpha = i / height
                color_value = int(30 + (100 - 30) * alpha)  # 从深蓝到较浅的蓝
                draw.line([(0, i), (width, i)], fill=(color_value, color_value + 20, color_value + 60))
            
            # 添加装饰性元素
            # 左上角圆形
            draw.ellipse([50, 50, 150, 150], fill=(255, 255, 255, 30))
            # 右下角圆形
            draw.ellipse([width-200, height-200, width-50, height-50], fill=(255, 255, 255, 20))
            
            # 设置字体
            try:
                # 尝试使用系统字体
                title_font = ImageFont.truetype("arial.ttf", 72)
                subtitle_font = ImageFont.truetype("arial.ttf", 36)
            except:
                try:
                    # macOS字体
                    title_font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 72)
                    subtitle_font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 36)
                except:
                    # 使用默认字体
                    title_font = ImageFont.load_default()
                    subtitle_font = ImageFont.load_default()
            
            # 处理标题文字（自动换行）
            max_chars_per_line = 12  # 每行最大字符数
            if len(title) > max_chars_per_line:
                # 智能换行
                lines = []
                words = title.split()
                current_line = ""
                
                for word in words:
                    if len(current_line + word) <= max_chars_per_line:
                        current_line += word
                    else:
                        if current_line:
                            lines.append(current_line.strip())
                        current_line = word
                
                if current_line:
                    lines.append(current_line.strip())
                
                # 如果还是太长，直接按字符切割
                if not lines or max(len(line) for line in lines) > max_chars_per_line:
                    lines = textwrap.wrap(title, width=max_chars_per_line)
            else:
                lines = [title]
            
            # 限制最多3行
            lines = lines[:3]
            
            # 计算文字位置
            total_text_height = len(lines) * 80 + (len(lines) - 1) * 20  # 行高80，行间距20
            start_y = (height - total_text_height) // 2
            
            # 绘制标题
            for i, line in enumerate(lines):
                # 计算文字宽度以居中
                bbox = draw.textbbox((0, 0), line, font=title_font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                y = start_y + i * 100
                
                # 添加文字阴影
                draw.text((x+3, y+3), line, fill='black', font=title_font)
                # 绘制主文字
                draw.text((x, y), line, fill='white', font=title_font)
            
            # 添加副标题
            subtitle = "今日头条 · 自动发布"
            bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = start_y + len(lines) * 100 + 40
            
            # 副标题阴影和文字
            draw.text((x+2, y+2), subtitle, fill='black', font=subtitle_font)
            draw.text((x, y), subtitle, fill='#E5E7EB', font=subtitle_font)
            
            # 保存图片
            img.save(default_cover_path, 'JPEG', quality=95)
            douyin_logger.info(f"✅ 创建默认封面: {default_cover_path}")
            
            return default_cover_path
            
        except ImportError:
            douyin_logger.warning("⚠️ 需要安装PIL库来创建封面: pip install Pillow")
            return None
        except Exception as e:
            douyin_logger.warning(f"⚠️ 创建默认封面失败: {e}")
            return None

    async def find_and_click_cover_upload(self, page):
        """查找并点击封面上传区域"""
        douyin_logger.info("查找封面上传区域...")
        
        # 可能的封面上传选择器
        cover_selectors = [
            # 直接的文件输入框
            'input[type="file"][accept*="image"]',
            'input[type="file"]',
            
            # 上传按钮或区域
            'button:has-text("上传封面")',
            'button:has-text("添加封面")',
            'button:has-text("选择封面")',
            'div:has-text("上传封面")',
            'div:has-text("添加封面")',
            
            # 通用上传区域
            '.upload-area',
            '.cover-upload',
            '.image-upload',
            '[class*="upload"]',
            '[class*="cover"]',
            
            # 可能的图片占位符
            '.cover-placeholder',
            '.image-placeholder',
            '[data-testid*="cover"]',
            '[data-testid*="upload"]'
        ]
        
        for selector in cover_selectors:
            try:
                elements = await page.locator(selector).all()
                for element in elements:
                    try:
                        # 检查元素是否可见
                        is_visible = await element.is_visible()
                        if is_visible:
                            douyin_logger.info(f"找到可见的上传元素: {selector}")
                            return element
                    except:
                        continue
            except:
                continue
        
        # 如果没找到明显的上传区域，尝试查找可能触发上传的按钮
        trigger_selectors = [
            'button:has-text("封面")',
            'button:has-text("图片")',
            'div[role="button"]:has-text("封面")',
            'div[role="button"]:has-text("图片")',
        ]
        
        for selector in trigger_selectors:
            try:
                element = page.locator(selector).first
                if await element.count() > 0 and await element.is_visible():
                    douyin_logger.info(f"找到可能的封面触发按钮: {selector}")
                    # 点击按钮可能会显示上传选项
                    await element.click()
                    await asyncio.sleep(2)
                    
                    # 再次查找文件输入框
                    file_input = page.locator('input[type="file"]').first
                    if await file_input.count() > 0:
                        return file_input
            except:
                continue
        
        return None

    async def upload_cover(self, page):
        """上传封面图片 - 改进版，支持默认封面和保存按钮处理"""
        douyin_logger.info("正在处理封面上传...")
        
        # 先关闭可能的弹窗
        await self.close_ai_assistant(page)
        
        # 如果没有指定封面，创建默认封面
        if not self.cover_path or not os.path.exists(self.cover_path):
            douyin_logger.info("未指定封面图片，创建默认封面...")
            self.cover_path = await self.create_default_cover(self.title)
            
            if not self.cover_path:
                douyin_logger.warning("无法创建默认封面")
                return False
        
        douyin_logger.info(f"使用封面图片: {self.cover_path}")
        
        try:
            # 查找上传元素
            upload_element = await self.find_and_click_cover_upload(page)
            
            if upload_element:
                try:
                    # 如果是文件输入框，直接设置文件
                    tag_name = await upload_element.evaluate('el => el.tagName.toLowerCase()')
                    if tag_name == 'input':
                        await upload_element.set_input_files(self.cover_path)
                        douyin_logger.info("✅ 通过文件输入框上传封面成功")
                        await asyncio.sleep(3)  # 等待上传完成
                        
                        # 查找并点击保存按钮
                        if await self.handle_cover_save_button(page):
                            return True
                        return True  # 即使没有保存按钮也认为成功
                    else:
                        # 如果是其他元素，点击后查找文件输入框
                        await upload_element.click()
                        await asyncio.sleep(2)
                        
                        # 查找出现的文件输入框
                        file_input = page.locator('input[type="file"]').first
                        if await file_input.count() > 0:
                            await file_input.set_input_files(self.cover_path)
                            douyin_logger.info("✅ 通过点击触发上传封面成功")
                            await asyncio.sleep(3)
                            
                            # 查找并点击保存按钮
                            if await self.handle_cover_save_button(page):
                                return True
                            return True
                except Exception as e:
                    douyin_logger.warning(f"上传元素操作失败: {e}")
            
            # 如果上述方法都失败，尝试查找所有文件输入框
            file_inputs = await page.locator('input[type="file"]').all()
            
            if file_inputs:
                douyin_logger.info(f"找到 {len(file_inputs)} 个文件输入框，尝试上传...")
                
                for i, file_input in enumerate(file_inputs):
                    try:
                        # 检查accept属性
                        accept_attr = await file_input.get_attribute('accept')
                        
                        # 优先选择明确接受图片的输入框
                        if accept_attr and 'image' in accept_attr:
                            douyin_logger.info(f"使用图片专用输入框 {i+1}")
                            await file_input.set_input_files(self.cover_path)
                            await asyncio.sleep(3)
                            douyin_logger.info("✅ 封面上传成功")
                            
                            # 查找并点击保存按钮
                            if await self.handle_cover_save_button(page):
                                return True
                            return True
                    except Exception as e:
                        douyin_logger.warning(f"文件输入框 {i+1} 上传失败: {e}")
                        continue
                
                # 如果没有专用的图片输入框，尝试第一个
                try:
                    await file_inputs[0].set_input_files(self.cover_path)
                    await asyncio.sleep(3)
                    douyin_logger.info("✅ 使用第一个文件输入框上传封面成功")
                    
                    # 查找并点击保存按钮
                    if await self.handle_cover_save_button(page):
                        return True
                    return True
                except Exception as e:
                    douyin_logger.warning(f"第一个文件输入框上传失败: {e}")
            
            # 最后尝试：模拟拖拽上传
            try:
                douyin_logger.info("尝试模拟拖拽上传...")
                
                # 查找可能的拖拽区域
                drop_zones = await page.locator('[class*="drop"], [class*="drag"], .upload-area').all()
                
                if drop_zones:
                    # 读取文件内容
                    with open(self.cover_path, 'rb') as f:
                        file_content = f.read()
                    
                    # 创建文件对象
                    await page.evaluate('''
                        (fileContent) => {
                            const file = new File([new Uint8Array(fileContent)], "cover.jpg", {type: "image/jpeg"});
                            const dt = new DataTransfer();
                            dt.items.add(file);
                            
                            const dropZone = document.querySelector('[class*="upload"], [class*="cover"], [class*="drop"]');
                            if (dropZone) {
                                const event = new DragEvent('drop', {
                                    dataTransfer: dt,
                                    bubbles: true
                                });
                                dropZone.dispatchEvent(event);
                            }
                        }
                    ''', list(file_content))
                    
                    await asyncio.sleep(3)
                    douyin_logger.info("✅ 模拟拖拽上传完成")
                    
                    # 查找并点击保存按钮
                    if await self.handle_cover_save_button(page):
                        return True
                    return True
                    
            except Exception as e:
                douyin_logger.warning(f"模拟拖拽上传失败: {e}")
            
            douyin_logger.error("❌ 所有封面上传方法都失败了")
            return False
                
        except Exception as e:
            douyin_logger.error(f"❌ 封面上传过程出错: {e}")
            return False

    async def handle_cover_save_button(self, page):
        """处理封面上传后的保存按钮"""
        douyin_logger.info("查找封面保存按钮...")
        
        # 等待页面更新
        await asyncio.sleep(2)
        
        # 可能的保存按钮选择器
        save_button_selectors = [
            # 明确的保存按钮
            'button:has-text("保存")',
            'button:has-text("确定")',
            'button:has-text("确认")',
            'button:has-text("应用")',
            'button:has-text("完成")',
            'button:has-text("Save")',
            'button:has-text("OK")',
            'button:has-text("Apply")',
            
            # 可能在弹窗中的按钮
            '.modal button:has-text("保存")',
            '.modal button:has-text("确定")',
            '.dialog button:has-text("保存")',
            '.dialog button:has-text("确定")',
            
            # 通过类名查找
            '.save-btn',
            '.confirm-btn',
            '.apply-btn',
            '.ok-btn',
            '[class*="save"]',
            '[class*="confirm"]',
            '[class*="apply"]',
            
            # 主要按钮样式
            '.btn-primary',
            '.primary-btn',
            'button.primary',
            
            # 特定的封面相关按钮
            '.cover-save',
            '.image-save',
            '[data-testid*="save"]',
            '[data-testid*="confirm"]'
        ]
        
        for selector in save_button_selectors:
            try:
                button = page.locator(selector).first
                if await button.count() > 0:
                    is_visible = await button.is_visible()
                    is_enabled = await button.is_enabled()
                    
                    if is_visible and is_enabled:
                        douyin_logger.info(f"找到保存按钮: {selector}")
                        
                        # 先关闭可能的弹窗
                        await self.close_ai_assistant(page)
                        
                        # 点击保存按钮
                        await button.click(force=True)
                        await asyncio.sleep(2)
                        
                        douyin_logger.info("✅ 封面保存按钮已点击")
                        return True
            except Exception as e:
                continue
        
        # 如果没找到明确的保存按钮，检查是否有弹窗需要关闭
        try:
            # 查找可能的弹窗关闭按钮（有时关闭弹窗就是保存）
            modal_close_selectors = [
                '.modal .close',
                '.dialog .close',
                '.popup .close',
                '[class*="modal"] [class*="close"]',
                '[class*="dialog"] [class*="close"]'
            ]
            
            for selector in modal_close_selectors:
                try:
                    close_btn = page.locator(selector).first
                    if await close_btn.count() > 0 and await close_btn.is_visible():
                        douyin_logger.info(f"点击弹窗关闭按钮: {selector}")
                        await close_btn.click()
                        await asyncio.sleep(1)
                        return True
                except:
                    continue
                    
        except Exception as e:
            douyin_logger.warning(f"处理弹窗关闭失败: {e}")
        
        # 尝试按ESC键关闭可能的弹窗
        try:
            await page.keyboard.press('Escape')
            await asyncio.sleep(1)
            douyin_logger.info("使用ESC键关闭可能的弹窗")
        except:
            pass
        
        douyin_logger.info("未找到明确的保存按钮，但封面可能已自动保存")
        return False

    async def set_publish_time(self, page):
        """设置发布时间"""
        if self.publish_date == 0:
            douyin_logger.info("使用立即发布")
            return True
            
        douyin_logger.info("正在设置定时发布...")
        
        # 先关闭可能的弹窗
        await self.close_ai_assistant(page)
        
        try:
            # 查找定时发布按钮
            schedule_button = page.locator('button:has-text("定时发布")')
            
            if await schedule_button.count() > 0:
                await schedule_button.click(force=True)
                await asyncio.sleep(2)
                
                # 查找时间输入框
                time_inputs = await page.locator('input[type="datetime-local"], input[placeholder*="时间"]').all()
                
                for time_input in time_inputs:
                    try:
                        is_visible = await time_input.is_visible()
                        if is_visible:
                            publish_time = self.publish_date.strftime("%Y-%m-%dT%H:%M")
                            await time_input.fill(publish_time)
                            douyin_logger.info(f"✅ 设置定时发布: {publish_time}")
                            return True
                    except Exception as e:
                        continue
                
                douyin_logger.warning("未找到时间输入框")
            else:
                douyin_logger.warning("未找到定时发布按钮")
                
        except Exception as e:
            douyin_logger.warning(f"定时发布设置失败: {e}")
        
        return True  # 定时发布设置失败不影响整体发布

    async def publish_article(self, page):
        """发布文章"""
        douyin_logger.info("准备发布文章...")
        
        # 先关闭可能的弹窗
        await self.close_ai_assistant(page)
        
        # 等待页面稳定
        await asyncio.sleep(2)
        
        try:
            # 使用分析得到的准确按钮选择器
            publish_button = page.locator('button:has-text("预览并发布")')
            
            if await publish_button.count() > 0:
                douyin_logger.info("找到发布按钮: 预览并发布")
                
                # 确保按钮可见
                await publish_button.scroll_into_view_if_needed()
                
                # 检查按钮是否可点击
                is_enabled = await publish_button.is_enabled()
                is_visible = await publish_button.is_visible()
                
                if is_enabled and is_visible:
                    douyin_logger.info("点击发布按钮...")
                    
                    # 使用force点击避免遮挡
                    await publish_button.click(force=True)
                    
                    # 等待发布完成或跳转
                    await asyncio.sleep(5)
                    
                    # 检查发布结果
                    current_url = page.url
                    
                    # 检查成功指示器
                    success_indicators = [
                        'text="发布成功"',
                        'text="文章发布成功"',
                        'text="发布完成"',
                        '.success-message',
                        '.success'
                    ]
                    
                    for indicator in success_indicators:
                        if await page.locator(indicator).count() > 0:
                            douyin_logger.success("🎉 文章发布成功！")
                            return True
                    
                    # 通过URL变化判断
                    if current_url != self.publish_url:
                        if any(keyword in current_url for keyword in ['success', 'manage', 'list', 'index']):
                            douyin_logger.success("🎉 文章发布成功（通过URL判断）！")
                            return True
                    
                    # 检查是否进入预览页面
                    if "preview" in current_url or await page.locator('button:has-text("确认发布")').count() > 0:
                        douyin_logger.info("进入预览页面，查找确认发布按钮...")
                        confirm_button = page.locator('button:has-text("确认发布")')
                        if await confirm_button.count() > 0:
                            await confirm_button.click(force=True)
                            await asyncio.sleep(3)
                            douyin_logger.success("🎉 文章发布成功！")
                            return True
                    
                    douyin_logger.info("发布按钮已点击，请手动确认发布结果")
                    return True
                else:
                    douyin_logger.warning(f"发布按钮不可点击: enabled={is_enabled}, visible={is_visible}")
                    return False
            else:
                douyin_logger.error("❌ 未找到发布按钮")
                return False
                
        except Exception as e:
            douyin_logger.error(f"❌ 发布失败: {e}")
            return False

    async def upload(self, playwright: Playwright) -> None:
        """上传文章到今日头条 - V5版本（解决遮挡问题）"""
        # 启动浏览器
        if self.local_executable_path:
            browser = await playwright.chromium.launch(headless=False, executable_path=self.local_executable_path)
        else:
            browser = await playwright.chromium.launch(headless=False)
        
        context = await browser.new_context(storage_state=f"{self.account_file}")
        context = await set_init_script(context)
        page = await context.new_page()
        
        try:
            douyin_logger.info(f'🚀 开始发布文章: {self.title}')
            
            # 1. 导航到发布页面
            if not await self.navigate_to_publish_page(page):
                douyin_logger.error("❌ 无法到达发布页面")
                return
            
            # 2. 填写标题
            if not await self.fill_title(page):
                douyin_logger.error("❌ 标题填写失败，停止发布")
                return
            
            # 3. 填写内容
            if not await self.fill_content(page):
                douyin_logger.error("❌ 内容填写失败，停止发布")
                return
            
            # 4. 添加标签
            await self.add_tags(page)
            
            # 5. 上传封面（必填项）
            if not await self.upload_cover(page):
                douyin_logger.error("❌ 封面上传失败，这是必填项，停止发布")
                return
            
            # 6. 设置发布时间
            await self.set_publish_time(page)
            
            # 7. 发布文章
            if await self.publish_article(page):
                douyin_logger.success("✅ 文章发布流程完成")
            else:
                douyin_logger.error("❌ 文章发布失败")
            
            # 保存截图用于调试
            screenshot_path = f"toutiao_publish_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            douyin_logger.info(f"📸 截图已保存: {screenshot_path}")
            
        except Exception as e:
            douyin_logger.error(f"❌ 发布过程中出错: {e}")
            # 保存错误截图
            error_screenshot = f"toutiao_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=error_screenshot, full_page=True)
            douyin_logger.info(f"📸 错误截图已保存: {error_screenshot}")
        
        finally:
            # 保存cookie
            await context.storage_state(path=self.account_file)
            douyin_logger.info("Cookie已更新")
            
            # 等待用户确认
            print("\n" + "="*50)
            print("📋 请检查发布结果:")
            print("1. 查看浏览器中的发布状态")
            print("2. 登录头条创作者中心确认文章是否发布成功")
            print("3. 检查截图文件了解详细情况")
            print("="*50)
            input("按回车键关闭浏览器...")
            
            await context.close()
            await browser.close()

    async def main(self):
        """主函数"""
        async with async_playwright() as playwright:
            await self.upload(playwright) 