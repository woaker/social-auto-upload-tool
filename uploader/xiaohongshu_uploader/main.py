# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Page
import os
import asyncio

from config import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.log import xiaohongshu_logger
from douyin_config import get_browser_config, get_context_config, get_anti_detection_script


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.xiaohongshu.com/creator-micro/content/upload")
        try:
            await page.wait_for_url("https://creator.xiaohongshu.com/creator-micro/content/upload", timeout=5000)
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


async def xiaohongshu_setup(account_file, handle=False):
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # Todo alert message
            return False
        xiaohongshu_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await xiaohongshu_cookie_gen(account_file)
    return True


async def xiaohongshu_cookie_gen(account_file):
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
        await page.goto("https://creator.xiaohongshu.com/")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


class XiaoHongShuVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, thumbnail_path=None, location="北京市"):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.thumbnail_path = thumbnail_path
        self.location = location  # 地理位置

    async def set_schedule_time_xiaohongshu(self, page, publish_date):
        print("  [-] 正在设置定时发布时间...")
        print(f"publish_date: {publish_date}")

        # 使用文本内容定位元素
        # element = await page.wait_for_selector(
        #     'label:has-text("定时发布")',
        #     timeout=5000  # 5秒超时时间
        # )
        # await element.click()

        # # 选择包含特定文本内容的 label 元素
        label_element = page.locator("label:has-text('定时发布')")
        # # 在选中的 label 元素下点击 checkbox
        await label_element.click()
        await asyncio.sleep(1)
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")
        print(f"publish_date_hour: {publish_date_hour}")

        await asyncio.sleep(1)
        await page.locator('.el-input__inner[placeholder="选择日期和时间"]').click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")

        await asyncio.sleep(1)

    async def handle_upload_error(self, page):
        xiaohongshu_logger.info('视频出错了，重新上传中')
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)

    async def upload(self, playwright: Playwright) -> None:
        # 使用增强版云服务器优化配置
        launch_options, env = get_browser_config()
        
        if self.local_executable_path:
            launch_options["executable_path"] = self.local_executable_path
            
        browser = await playwright.chromium.launch(**launch_options)
        
        # 使用增强版上下文配置
        context_config = get_context_config()
        context_config["storage_state"] = f"{self.account_file}"
        context_config["viewport"] = {"width": 1600, "height": 900}  # 保持小红书特定的视口大小
        
        context = await browser.new_context(**context_config)
        
        # 使用增强版反检测脚本
        await context.add_init_script(get_anti_detection_script())
        
        context = await set_init_script(context)

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.xiaohongshu.com/publish/publish?from=homepage&target=video")
        xiaohongshu_logger.info(f'[+]正在上传-------{self.title}.mp4')
        # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
        xiaohongshu_logger.info(f'[-] 正在打开主页...')
        await page.wait_for_url("https://creator.xiaohongshu.com/publish/publish?from=homepage&target=video")
        
        # 等待上传区域加载完成
        await asyncio.sleep(2)
        
        # 查找并上传视频文件
        xiaohongshu_logger.info(f'[-] 正在选择视频文件...')
        try:
            # 多种可能的选择器
            upload_selectors = [
                "div[class^='upload-content'] input[class='upload-input']",
                "input.upload-input",
                "input[type='file'][class*='upload']",
                "input[accept*='video']"
            ]
            
            upload_success = False
            for selector in upload_selectors:
                try:
                    upload_element = await page.wait_for_selector(selector, timeout=5000)
                    if upload_element:
                        await upload_element.set_input_files(self.file_path)
                        xiaohongshu_logger.info(f'[-] 视频文件上传成功，使用选择器: {selector}')
                        upload_success = True
                        break
                except Exception as e:
                    xiaohongshu_logger.warning(f'[-] 选择器 {selector} 失败: {e}')
                    continue
            
            if not upload_success:
                raise Exception("无法找到视频上传元素")
                
        except Exception as e:
            xiaohongshu_logger.error(f'[-] 视频上传失败: {e}')
            raise

        # 等待视频上传处理完成
        xiaohongshu_logger.info(f'[-] 等待视频处理完成...')
        upload_completed = False
        max_wait_time = 300  # 最大等待5分钟
        wait_time = 0
        
        while not upload_completed and wait_time < max_wait_time:
            try:
                await asyncio.sleep(3)
                wait_time += 3
                
                # 检查多种上传完成的指示器
                success_indicators = [
                    'div.stage:has-text("上传成功")',
                    'div:has-text("上传完成")', 
                    'div:has-text("处理完成")',
                    'button:has-text("发布")',  # 如果出现发布按钮，说明上传完成
                    'div[class*="preview"]:visible',  # 预览区域出现
                ]
                
                for indicator in success_indicators:
                    if await page.locator(indicator).count() > 0:
                        xiaohongshu_logger.success(f'[-] 检测到上传完成指示器: {indicator}')
                        upload_completed = True
                        break
                
                if not upload_completed:
                    xiaohongshu_logger.info(f'[-] 视频处理中... ({wait_time}s/{max_wait_time}s)')
                    
            except Exception as e:
                xiaohongshu_logger.warning(f'[-] 检测上传状态时出错: {e}')
                continue
        
        if not upload_completed:
            xiaohongshu_logger.error(f'[-] 视频上传超时 ({max_wait_time}s)')
            raise Exception("视频上传处理超时")
        
        xiaohongshu_logger.success('[-] 视频上传处理完成!')
        await asyncio.sleep(2)  # 额外等待确保页面稳定

        # 填充标题和话题
        # 检查是否存在包含输入框的元素
        # 这里为了避免页面变化，故使用相对位置定位：作品标题父级右侧第一个元素的input子元素
        await asyncio.sleep(1)
        xiaohongshu_logger.info(f'  [-] 正在填充标题和话题...')
        
        # 小红书标题长度限制为20个字符，超出则自动截取
        truncated_title = self.title[:20] if len(self.title) > 20 else self.title
        if len(self.title) > 20:
            xiaohongshu_logger.info(f'  [-] 标题长度超过20字符，已自动截取: {self.title} -> {truncated_title}')
        
        title_container = page.locator('div.input.titleInput').locator('input.d-text')
        if await title_container.count():
            await title_container.fill(truncated_title)
        else:
            titlecontainer = page.locator(".notranslate")
            await titlecontainer.click()
            await page.keyboard.press("Backspace")
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")
            await page.keyboard.type(truncated_title)
            await page.keyboard.press("Enter")
        css_selector = ".ql-editor" # 不能加上 .ql-blank 属性，这样只能获取第一次非空状态
        for index, tag in enumerate(self.tags, start=1):
            await page.type(css_selector, "#" + tag)
            await page.press(css_selector, "Space")
        xiaohongshu_logger.info(f'总共添加{len(self.tags)}个话题')

        # while True:
        #     # 判断重新上传按钮是否存在，如果不存在，代表视频正在上传，则等待
        #     try:
        #         #  新版：定位重新上传
        #         number = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
        #         if number > 0:
        #             xiaohongshu_logger.success("  [-]视频上传完毕")
        #             break
        #         else:
        #             xiaohongshu_logger.info("  [-] 正在上传视频中...")
        #             await asyncio.sleep(2)

        #             if await page.locator('div.progress-div > div:has-text("上传失败")').count():
        #                 xiaohongshu_logger.error("  [-] 发现上传出错了... 准备重试")
        #                 await self.handle_upload_error(page)
        #     except:
        #         xiaohongshu_logger.info("  [-] 正在上传视频中...")
        #         await asyncio.sleep(2)
        
        # 上传视频封面
        # await self.set_thumbnail(page, self.thumbnail_path)

        # 设置地理位置为固定值
        await self.set_location(page, self.location)

        # # 頭條/西瓜
        # third_part_element = '[class^="info"] > [class^="first-part"] div div.semi-switch'
        # # 定位是否有第三方平台
        # if await page.locator(third_part_element).count():
        #     # 检测是否是已选中状态
        #     if 'semi-switch-checked' not in await page.eval_on_selector(third_part_element, 'div => div.className'):
        #         await page.locator(third_part_element).locator('input.semi-switch-native-control').click()

        if self.publish_date != 0:
            await self.set_schedule_time_xiaohongshu(page, self.publish_date)

        # 判断视频是否发布成功
        while True:
            try:
                # 等待包含"定时发布"文本的button元素出现并点击
                if self.publish_date != 0:
                    await page.locator('button:has-text("定时发布")').click()
                else:
                    await page.locator('button:has-text("发布")').click()
                await page.wait_for_url(
                    "https://creator.xiaohongshu.com/publish/success?**",
                    timeout=3000
                )  # 如果自动跳转到作品页面，则代表发布成功
                xiaohongshu_logger.success("  [-]视频发布成功")
                break
            except:
                xiaohongshu_logger.info("  [-] 视频正在发布中...")
                await page.screenshot(full_page=True)
                await asyncio.sleep(0.5)

        await context.storage_state(path=self.account_file)  # 保存cookie
        xiaohongshu_logger.success('  [-]cookie更新完毕！')
        await asyncio.sleep(2)  # 这里延迟是为了方便眼睛直观的观看
        # 关闭浏览器上下文和浏览器实例
        await context.close()
        await browser.close()
    
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

    async def set_location(self, page: Page, location: str = "青岛市"):
        print(f"开始设置位置: {location}")
        
        # 点击地点输入框
        print("等待地点输入框加载...")
        loc_ele = await page.wait_for_selector('div.d-text.d-select-placeholder.d-text-ellipsis.d-text-nowrap')
        print(f"已定位到地点输入框: {loc_ele}")
        await loc_ele.click()
        print("点击地点输入框完成")
        
        # 输入位置名称
        print(f"等待1秒后输入位置名称: {location}")
        await page.wait_for_timeout(1000)
        await page.keyboard.type(location)
        print(f"位置名称输入完成: {location}")
        
        # 等待下拉列表加载
        print("等待下拉列表加载...")
        dropdown_selector = 'div.d-popover.d-popover-default.d-dropdown.--size-min-width-large'
        await page.wait_for_timeout(3000)
        try:
            await page.wait_for_selector(dropdown_selector, timeout=3000)
            print("下拉列表已加载")
        except:
            print("下拉列表未按预期显示，可能结构已变化")
        
        # 增加等待时间以确保内容加载完成
        print("额外等待1秒确保内容渲染完成...")
        await page.wait_for_timeout(1000)
        
        # 尝试更灵活的XPath选择器
        print("尝试使用更灵活的XPath选择器...")
        flexible_xpath = (
            f'//div[contains(@class, "d-popover") and contains(@class, "d-dropdown")]'
            f'//div[contains(@class, "d-options-wrapper")]'
            f'//div[contains(@class, "d-grid") and contains(@class, "d-options")]'
            f'//div[contains(@class, "name") and text()="{location}"]'
        )
        await page.wait_for_timeout(3000)
        
        # 尝试定位元素
        print(f"尝试定位包含'{location}'的选项...")
        try:
            # 先尝试使用更灵活的选择器
            location_option = await page.wait_for_selector(
                flexible_xpath,
                timeout=3000
            )
            
            if location_option:
                print(f"使用灵活选择器定位成功: {location_option}")
            else:
                # 如果灵活选择器失败，再尝试原选择器
                print("灵活选择器未找到元素，尝试原始选择器...")
                location_option = await page.wait_for_selector(
                    f'//div[contains(@class, "d-popover") and contains(@class, "d-dropdown")]'
                    f'//div[contains(@class, "d-options-wrapper")]'
                    f'//div[contains(@class, "d-grid") and contains(@class, "d-options")]'
                    f'/div[1]//div[contains(@class, "name") and text()="{location}"]',
                    timeout=2000
                )
            
            # 滚动到元素并点击
            print("滚动到目标选项...")
            await location_option.scroll_into_view_if_needed()
            print("元素已滚动到视图内")
            
            # 增加元素可见性检查
            is_visible = await location_option.is_visible()
            print(f"目标选项是否可见: {is_visible}")
            
            # 点击元素
            print("准备点击目标选项...")
            await location_option.click()
            print(f"成功选择位置: {location}")
            return True
            
        except Exception as e:
            print(f"定位位置失败: {e}")
            
            # 打印更多调试信息
            print("尝试获取下拉列表中的所有选项...")
            try:
                all_options = await page.query_selector_all(
                    '//div[contains(@class, "d-popover") and contains(@class, "d-dropdown")]'
                    '//div[contains(@class, "d-options-wrapper")]'
                    '//div[contains(@class, "d-grid") and contains(@class, "d-options")]'
                    '/div'
                )
                print(f"找到 {len(all_options)} 个选项")
                
                # 打印前3个选项的文本内容
                for i, option in enumerate(all_options[:3]):
                    option_text = await option.inner_text()
                    print(f"选项 {i+1}: {option_text.strip()[:50]}...")
                    
            except Exception as e:
                print(f"获取选项列表失败: {e}")
                
            # 截图保存（取消注释使用）
            # await page.screenshot(path=f"location_error_{location}.png")
            return False

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)


