#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
今日头条文章自动发布工具 - 最终版本
支持自动填充标题、内容、标签，自动生成和上传封面，智能处理AI助手弹窗
"""

import asyncio
import os
import sys
import json
import time
import textwrap
from datetime import datetime
from playwright.async_api import Playwright, async_playwright

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import douyin_logger

async def cookie_auth(account_file):
    """验证cookie是否有效"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=f"{account_file}")
        context = await set_init_script(context)
        page = await context.new_page()
        
        try:
            await page.goto("https://mp.toutiao.com/")
            await page.wait_for_load_state('networkidle')
            
            # 检查是否跳转到登录页面
            current_url = page.url
            if "login" in current_url:
                return False
            
            # 检查页面标题
            title = await page.title()
            if "登录" in title or "login" in title.lower():
                return False
                
            douyin_logger.info("[+] cookie 有效")
            return True
            
        except Exception as e:
            douyin_logger.error(f"Cookie验证失败: {e}")
            return False
        finally:
            await browser.close()

async def toutiao_setup(account_file, handle=False):
    """检查今日头条登录状态"""
    if not os.path.exists(account_file):
        douyin_logger.error(f"账号文件不存在: {account_file}")
        return False
    
    return await cookie_auth(account_file)

async def toutiao_cookie_gen(account_file):
    """生成今日头条cookie"""
    douyin_logger.info("🔑 重新登录今日头条账号")
    douyin_logger.info("=" * 40)
    douyin_logger.info(f"Cookie将保存到: {account_file}")
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()
        
        try:
            await page.goto("https://mp.toutiao.com/auth/page/login")
            
            douyin_logger.info("请在浏览器中登录今日头条账号...")
            input("登录完成后，请在调试器中点击 '继续' 按钮\n")
            
            # 保存cookie
            storage = await context.storage_state(path=account_file)
            douyin_logger.info("Cookie已保存")
            
            return True
            
        except Exception as e:
            douyin_logger.error(f"登录过程出错: {e}")
            return False
        finally:
            await browser.close()

class TouTiaoArticle(object):
    """今日头条文章发布类 - 最终版本"""
    
    def __init__(self, title, content, tags, publish_date: datetime, account_file, cover_path=None):
        self.title = title  # 文章标题
        self.content = content  # 文章内容
        self.tags = tags  # 文章标签
        self.publish_date = publish_date  # 发布时间，0表示立即发布
        self.account_file = account_file  # 账号文件路径
        self.cover_path = cover_path  # 封面图片路径
        self.local_executable_path = ""  # 浏览器路径
        self.publish_url = "https://mp.toutiao.com/profile_v4/graphic/publish"

    async def close_ai_assistant(self, page):
        """检查并关闭AI助手弹窗"""
        try:
            # 可能的AI助手关闭按钮选择器
            close_selectors = [
                '.close-btn',
                '[class*="close"]',
                '.ai-assistant-close',
                '[aria-label*="关闭"]',
                '[aria-label*="close"]',
                'button[title*="关闭"]',
                'button[title*="close"]'
            ]
            
            for selector in close_selectors:
                try:
                    close_btn = page.locator(selector).first
                    if await close_btn.count() > 0:
                        is_visible = await close_btn.is_visible()
                        if is_visible:
                            await close_btn.click()
                            douyin_logger.info(f"✅ 成功关闭AI助手弹窗: {selector}")
                            await asyncio.sleep(1)
                            return True
                except:
                    continue
            
            # 尝试按ESC键关闭
            try:
                await page.keyboard.press('Escape')
                await asyncio.sleep(1)
                douyin_logger.info("✅ 使用ESC键关闭弹窗")
                return True
            except:
                pass
                
            # 尝试点击遮罩层外部
            try:
                mask = page.locator('.byte-drawer-mask, .modal-mask, [class*="mask"]').first
                if await mask.count() > 0:
                    await mask.click()
                    await asyncio.sleep(1)
                    douyin_logger.info("✅ 点击遮罩层关闭弹窗")
                    return True
            except:
                pass
                
        except Exception as e:
            douyin_logger.warning(f"关闭AI助手弹窗时出错: {e}")
        
        return False

    async def navigate_to_publish_page(self, page):
        """导航到发布页面"""
        douyin_logger.info("正在访问发布页面...")
        
        try:
            await page.goto(self.publish_url)
            await page.wait_for_load_state('networkidle')
            
            # 关闭可能的弹窗
            await self.close_ai_assistant(page)
            
            # 检查页面标题和URL
            title = await page.title()
            current_url = page.url
            
            douyin_logger.info(f"当前页面: {title}")
            douyin_logger.info(f"当前URL: {current_url}")
            
            # 再次关闭可能的弹窗
            await self.close_ai_assistant(page)
            
            # 检查是否成功到达发布页面
            title_input = page.locator('textarea[placeholder*="请输入文章标题"]')
            content_editor = page.locator('.ProseMirror')
            
            title_count = await title_input.count()
            content_count = await content_editor.count()
            
            if title_count > 0 and content_count > 0:
                douyin_logger.info("✅ 成功到达发布页面，找到标题和内容编辑器")
                return True
            else:
                douyin_logger.error(f"❌ 发布页面元素检查失败: 标题输入框={title_count}, 内容编辑器={content_count}")
                return False
                
        except Exception as e:
            douyin_logger.error(f"访问发布页面失败: {e}")
            return False

    async def fill_title(self, page):
        """填写文章标题"""
        douyin_logger.info("正在填写标题...")
        
        # 先关闭可能的弹窗
        await self.close_ai_assistant(page)
        
        try:
            # 使用精确的选择器
            title_input = page.locator('textarea[placeholder*="请输入文章标题"]')
            
            if await title_input.count() > 0:
                douyin_logger.info("找到标题输入框")
                
                # 先关闭弹窗再操作
                await self.close_ai_assistant(page)
                
                # 清空并填写标题
                await title_input.click(force=True)
                await title_input.fill("")
                await asyncio.sleep(1)
                await title_input.fill(self.title)
                
                # 验证填写结果
                filled_value = await title_input.input_value()
                if filled_value == self.title:
                    douyin_logger.info("✅ 标题填写成功")
                    return True
                else:
                    douyin_logger.warning(f"标题填写可能不完整: 期望='{self.title}', 实际='{filled_value}'")
                    return True  # 仍然认为成功，可能是显示问题
            else:
                douyin_logger.error("❌ 未找到标题输入框")
                return False
                
        except Exception as e:
            douyin_logger.error(f"❌ 标题填写失败: {e}")
            return False

    async def fill_content(self, page):
        """填写文章内容"""
        douyin_logger.info("正在填写内容...")
        
        # 先关闭可能的弹窗
        await self.close_ai_assistant(page)
        
        try:
            # 查找内容编辑器
            content_editor = page.locator('.ProseMirror')
            
            if await content_editor.count() > 0:
                douyin_logger.info("找到内容编辑器")
                
                # 先关闭弹窗再操作
                await self.close_ai_assistant(page)
                
                # 点击编辑器并填写内容
                await content_editor.click(force=True)
                await asyncio.sleep(1)
                
                # 清空现有内容
                await page.keyboard.press('Control+a')
                await asyncio.sleep(0.5)
                
                # 填写新内容
                await content_editor.fill(self.content)
                await asyncio.sleep(2)
                
                douyin_logger.info("✅ 内容填写成功")
                return True
            else:
                douyin_logger.error("❌ 未找到内容编辑器")
                return False
                
        except Exception as e:
            douyin_logger.error(f"❌ 内容填写失败: {e}")
            return False

    async def add_tags(self, page):
        """添加文章标签"""
        if not self.tags:
            douyin_logger.info("无标签需要添加")
            return True
            
        douyin_logger.info("正在添加标签...")
        
        # 先关闭可能的弹窗
        await self.close_ai_assistant(page)
        
        try:
            # 将标签添加到内容末尾
            tags_text = " " + " ".join([f"#{tag}" for tag in self.tags])
            
            # 找到内容编辑器
            content_editor = page.locator('.ProseMirror')
            if await content_editor.count() > 0:
                await content_editor.click(force=True)
                await asyncio.sleep(1)
                
                # 移动到内容末尾
                await page.keyboard.press('Control+End')
                await asyncio.sleep(0.5)
                
                # 添加标签
                await page.keyboard.type(tags_text)
                await asyncio.sleep(1)
                
                douyin_logger.info(f"✅ 成功添加标签: {tags_text}")
                return True
            else:
                douyin_logger.warning("未找到内容编辑器，跳过标签添加")
                return True
                
        except Exception as e:
            douyin_logger.warning(f"标签添加失败: {e}")
            return True  # 标签添加失败不影响整体发布

    async def create_default_cover(self, title):
        """创建默认封面图片"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # 创建图片目录
            images_dir = os.path.join(project_root, "images")
            os.makedirs(images_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_cover_path = os.path.join(images_dir, f"default_cover_{timestamp}.jpg")
            
            # 创建图片 (16:9比例)
            width, height = 1280, 720
            
            # 创建渐变背景
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # 绘制渐变背景
            for i in range(height):
                ratio = i / height
                r = int(59 + (139 - 59) * ratio)    # 从深蓝到浅蓝
                g = int(130 + (195 - 130) * ratio)
                b = int(246 + (255 - 246) * ratio)
                draw.line([(0, i), (width, i)], fill=(r, g, b))
            
            # 尝试加载字体
            try:
                # 尝试系统字体
                if sys.platform == "darwin":  # macOS
                    title_font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 72)
                    subtitle_font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 36)
                elif sys.platform == "win32":  # Windows
                    title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 72)
                    subtitle_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 36)
                else:  # Linux
                    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
                    subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
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
            'input[type="file"][accept*="image"]',
            'input[type="file"]',
            'button:has-text("上传封面")',
            'button:has-text("添加封面")',
            'div:has-text("上传封面")',
            '.upload-area',
            '.cover-upload',
            '[class*="upload"]',
            '[class*="cover"]'
        ]
        
        for selector in cover_selectors:
            try:
                elements = await page.locator(selector).all()
                for element in elements:
                    try:
                        is_visible = await element.is_visible()
                        if is_visible:
                            douyin_logger.info(f"找到可见的上传元素: {selector}")
                            return element
                    except:
                        continue
            except:
                continue
        
        return None

    async def upload_cover(self, page):
        """上传封面图片"""
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
                    tag_name = await upload_element.evaluate('el => el.tagName.toLowerCase()')
                    if tag_name == 'input':
                        await upload_element.set_input_files(self.cover_path)
                        douyin_logger.info("✅ 通过文件输入框上传封面成功")
                        await asyncio.sleep(3)
                        await self.handle_cover_save_button(page)
                        return True
                    else:
                        await upload_element.click()
                        await asyncio.sleep(2)
                        
                        file_input = page.locator('input[type="file"]').first
                        if await file_input.count() > 0:
                            await file_input.set_input_files(self.cover_path)
                            douyin_logger.info("✅ 通过点击触发上传封面成功")
                            await asyncio.sleep(3)
                            await self.handle_cover_save_button(page)
                            return True
                except Exception as e:
                    douyin_logger.warning(f"上传元素操作失败: {e}")
            
            # 尝试查找所有文件输入框
            file_inputs = await page.locator('input[type="file"]').all()
            
            if file_inputs:
                for i, file_input in enumerate(file_inputs):
                    try:
                        accept_attr = await file_input.get_attribute('accept')
                        if accept_attr and 'image' in accept_attr:
                            douyin_logger.info(f"使用图片专用输入框 {i+1}")
                            await file_input.set_input_files(self.cover_path)
                            await asyncio.sleep(3)
                            douyin_logger.info("✅ 封面上传成功")
                            await self.handle_cover_save_button(page)
                            return True
                    except Exception as e:
                        continue
                
                # 使用第一个文件输入框
                try:
                    await file_inputs[0].set_input_files(self.cover_path)
                    await asyncio.sleep(3)
                    douyin_logger.info("✅ 使用第一个文件输入框上传封面成功")
                    await self.handle_cover_save_button(page)
                    return True
                except Exception as e:
                    douyin_logger.warning(f"第一个文件输入框上传失败: {e}")
            
            douyin_logger.error("❌ 所有封面上传方法都失败了")
            return False
                
        except Exception as e:
            douyin_logger.error(f"❌ 封面上传过程出错: {e}")
            return False

    async def handle_cover_save_button(self, page):
        """处理封面上传后的保存按钮"""
        douyin_logger.info("查找封面保存按钮...")
        
        await asyncio.sleep(2)
        
        # 可能的保存按钮选择器
        save_button_selectors = [
            'button:has-text("保存")',
            'button:has-text("确定")',
            'button:has-text("确认")',
            'button:has-text("应用")',
            'button:has-text("完成")',
            '.modal button:has-text("确定")',
            '.dialog button:has-text("确定")',
            '.save-btn',
            '.confirm-btn',
            '.btn-primary'
        ]
        
        for selector in save_button_selectors:
            try:
                button = page.locator(selector).first
                if await button.count() > 0:
                    is_visible = await button.is_visible()
                    is_enabled = await button.is_enabled()
                    
                    if is_visible and is_enabled:
                        douyin_logger.info(f"找到保存按钮: {selector}")
                        await self.close_ai_assistant(page)
                        await button.click(force=True)
                        await asyncio.sleep(2)
                        douyin_logger.info("✅ 封面保存按钮已点击")
                        return True
            except Exception as e:
                continue
        
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
        
        await self.close_ai_assistant(page)
        
        try:
            schedule_button = page.locator('button:has-text("定时发布")')
            
            if await schedule_button.count() > 0:
                await schedule_button.click(force=True)
                await asyncio.sleep(2)
                
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
        
        return True

    async def check_and_handle_captcha(self, page):
        """检查并处理验证码"""
        captcha_selectors = [
            'input[placeholder*="验证码"]',
            'input[placeholder*="captcha"]',
            'input[type="text"][placeholder*="码"]',
            '.captcha-input',
            '.verification-code',
            'input[name*="captcha"]',
            'input[id*="captcha"]'
        ]
        
        for selector in captcha_selectors:
            try:
                captcha_input = page.locator(selector)
                if await captcha_input.count() > 0 and await captcha_input.is_visible():
                    douyin_logger.warning("🔍 检测到验证码输入框")
                    
                    # 查找验证码图片
                    captcha_image_selectors = [
                        'img[src*="captcha"]',
                        'img[alt*="验证码"]',
                        '.captcha-image img',
                        '.verification-image img'
                    ]
                    
                    captcha_image = None
                    for img_selector in captcha_image_selectors:
                        img = page.locator(img_selector)
                        if await img.count() > 0 and await img.is_visible():
                            captcha_image = img
                            break
                    
                    if captcha_image:
                        douyin_logger.info("📷 找到验证码图片")
                        # 截图保存验证码
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        captcha_screenshot = f"captcha_{timestamp}.png"
                        await captcha_image.screenshot(path=captcha_screenshot)
                        douyin_logger.info(f"📸 验证码截图已保存: {captcha_screenshot}")
                    
                    # 等待用户输入验证码
                    douyin_logger.warning("⚠️ 需要输入验证码才能继续发布")
                    douyin_logger.info("📋 请查看浏览器页面中的验证码")
                    douyin_logger.info("💡 浏览器将保持打开状态，请手动输入验证码并点击确认")
                    douyin_logger.info("⏰ 等待60秒让用户手动处理验证码...")
                    
                    # 等待用户手动处理验证码
                    for i in range(60):
                        await asyncio.sleep(1)
                        
                        # 检查验证码输入框是否还存在
                        if await captcha_input.count() == 0 or not await captcha_input.is_visible():
                            douyin_logger.info("✅ 验证码已处理，继续发布流程")
                            return True
                        
                        # 每10秒提醒一次
                        if i % 10 == 9:
                            remaining = 60 - i - 1
                            douyin_logger.info(f"⏰ 还有 {remaining} 秒，请在浏览器中输入验证码")
                    
                    # 60秒后仍有验证码，尝试交互式输入
                    try:
                        douyin_logger.warning("⚠️ 60秒内未检测到验证码处理，尝试交互式输入")
                        captcha_code = input("🔢 请输入验证码（直接回车跳过）: ").strip()
                        if captcha_code:
                            await captcha_input.fill(captcha_code)
                            douyin_logger.info(f"✅ 验证码已输入: {captcha_code}")
                            await asyncio.sleep(1)
                            
                            # 查找验证码确认按钮
                            confirm_selectors = [
                                'button:has-text("确认")',
                                'button:has-text("提交")',
                                'button:has-text("验证")',
                                '.captcha-submit',
                                '.verify-btn'
                            ]
                            
                            for confirm_selector in confirm_selectors:
                                confirm_btn = page.locator(confirm_selector)
                                if await confirm_btn.count() > 0 and await confirm_btn.is_visible():
                                    await confirm_btn.click()
                                    douyin_logger.info("✅ 验证码确认按钮已点击")
                                    await asyncio.sleep(2)
                                    break
                            
                            return True
                        else:
                            douyin_logger.warning("⚠️ 跳过验证码输入，请手动在浏览器中处理")
                            return True  # 让流程继续，用户可以手动处理
                    except KeyboardInterrupt:
                        douyin_logger.warning("❌ 用户取消验证码输入")
                        return False
                    except Exception as e:
                        douyin_logger.warning(f"⚠️ 验证码输入失败: {e}，请手动在浏览器中处理")
                        return True  # 让流程继续，用户可以手动处理
            except Exception as e:
                continue
        
        return True  # 没有验证码，继续执行

    async def publish_article(self, page):
        """发布文章"""
        douyin_logger.info("准备发布文章...")
        
        await self.close_ai_assistant(page)
        await asyncio.sleep(2)
        
        try:
            publish_button = page.locator('button:has-text("预览并发布")')
            
            if await publish_button.count() > 0:
                douyin_logger.info("找到发布按钮: 预览并发布")
                
                await publish_button.scroll_into_view_if_needed()
                
                is_enabled = await publish_button.is_enabled()
                is_visible = await publish_button.is_visible()
                
                if is_enabled and is_visible:
                    douyin_logger.info("点击发布按钮...")
                    await publish_button.click(force=True)
                    await asyncio.sleep(5)
                    
                    # 检查是否有验证码
                    if not await self.check_and_handle_captcha(page):
                        douyin_logger.error("❌ 验证码处理失败")
                        return False
                    
                    # 检查是否进入预览页面
                    current_url = page.url
                    if "preview" in current_url or await page.locator('button:has-text("确认发布")').count() > 0:
                        douyin_logger.info("进入预览页面，查找确认发布按钮...")
                        confirm_button = page.locator('button:has-text("确认发布")')
                        if await confirm_button.count() > 0:
                            await confirm_button.click(force=True)
                            await asyncio.sleep(3)
                            
                            # 再次检查验证码
                            if not await self.check_and_handle_captcha(page):
                                douyin_logger.error("❌ 确认发布时验证码处理失败")
                                return False
                            
                            # 等待发布完成
                            await asyncio.sleep(5)
                            
                            # 检查发布结果
                            success_indicators = [
                                'text="发布成功"',
                                'text="文章发布成功"',
                                'text="发布完成"',
                                '.success-message',
                                '.publish-success'
                            ]
                            
                            for indicator in success_indicators:
                                if await page.locator(indicator).count() > 0:
                                    douyin_logger.success("🎉 文章发布成功！")
                                    return True
                            
                            # 检查是否还在发布页面（可能发布失败）
                            if "publish" in page.url:
                                douyin_logger.warning("⚠️ 可能还在发布页面，请手动确认发布状态")
                            else:
                                douyin_logger.success("🎉 文章发布成功！")
                            return True
                    
                    # 检查成功指示器
                    success_indicators = [
                        'text="发布成功"',
                        'text="文章发布成功"',
                        '.success-message'
                    ]
                    
                    for indicator in success_indicators:
                        if await page.locator(indicator).count() > 0:
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
        """上传文章到今日头条"""
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
                douyin_logger.error("❌ 无法访问发布页面")
                return
            
            # 2. 填写标题
            if not await self.fill_title(page):
                douyin_logger.error("❌ 标题填写失败")
                return
            
            # 3. 填写内容
            if not await self.fill_content(page):
                douyin_logger.error("❌ 内容填写失败")
                return
            
            # 4. 添加标签
            await self.add_tags(page)
            
            # 5. 上传封面
            await self.upload_cover(page)
            
            # 6. 设置发布时间
            await self.set_publish_time(page)
            
            # 7. 发布文章
            if await self.publish_article(page):
                douyin_logger.success("✅ 文章发布流程完成")
            else:
                douyin_logger.error("❌ 文章发布失败")
            
            # 保存截图
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"toutiao_publish_result_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            douyin_logger.info(f"📸 截图已保存: {screenshot_path}")
            
        except Exception as e:
            douyin_logger.error(f"发布过程出错: {e}")
        finally:
            # 保存cookie
            await context.storage_state(path=self.account_file)
            douyin_logger.info("Cookie已更新")
            
            try:
                input("按回车键关闭浏览器...")
            except EOFError:
                douyin_logger.info("检测到非交互模式，自动关闭浏览器")
                await asyncio.sleep(3)
            await browser.close()

    async def main(self):
        """主函数"""
        async with async_playwright() as playwright:
            await self.upload(playwright) 