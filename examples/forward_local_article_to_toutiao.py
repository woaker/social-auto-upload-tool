#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
本地文章转发到今日头条工具
支持从本地Markdown文件读取文章内容并转发到今日头条
优化排版，提升阅读体验
"""

import asyncio
import os
import sys
import re
import time
import argparse
import traceback
from datetime import datetime
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import markdown
from typing import Optional, Dict, List
import json

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uploader.toutiao_uploader.main_final import TouTiaoArticle, toutiao_setup
from examples.forward_article_to_toutiao import WechatSyncStyleFormatter, AIContentEnhancer

class LocalArticleForwarder:
    """本地文章转发工具"""
    
    def __init__(self):
        # 初始化格式化器
        self.formatter = WechatSyncStyleFormatter()
    
    def read_local_article(self, file_path):
        """从本地文件读取文章内容"""
        print(f"📄 正在读取本地文件: {file_path}")
        
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                print(f"❌ 文件不存在: {file_path}")
                return None, None, None
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取标题（假设第一行是标题）
            lines = content.split('\n')
            title = lines[0].strip()
            
            # 如果标题是Markdown格式的标题，去掉#号
            title = re.sub(r'^#+\s*', '', title)
            
            # 默认标签
            tags = ['文章转发', '技术分享']
            
            # 尝试从文件名或内容中提取更多标签
            filename_tags = self._extract_tags_from_filename(file_path)
            content_tags = self._extract_tags_from_content(content)
            
            if filename_tags:
                tags.extend(filename_tags)
            if content_tags:
                tags.extend(content_tags)
            
            # 去重
            tags = list(set(tags))[:5]  # 最多5个标签
            
            print(f"✅ 文章读取成功:")
            print(f"📝 标题: {title}")
            print(f"📊 内容长度: {len(content)} 字符")
            print(f"🏷️ 标签: {tags}")
            
            return title, content, tags
            
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            traceback.print_exc()
            return None, None, None
    
    def _extract_tags_from_filename(self, file_path):
        """从文件名中提取可能的标签"""
        filename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(filename)[0]
        
        # 提取可能的标签（例如：react-tutorial.md -> ['react', 'tutorial']）
        words = re.findall(r'[a-zA-Z0-9\u4e00-\u9fff]+', name_without_ext)
        
        # 过滤掉太短的词
        return [word for word in words if len(word) > 2]
    
    def _extract_tags_from_content(self, content):
        """从内容中提取可能的标签"""
        # 常见技术关键词列表
        tech_keywords = [
            'Python', 'JavaScript', 'Java', 'React', 'Vue', 'Angular', 
            'Node.js', 'TypeScript', 'Docker', 'Kubernetes', 'AWS', 
            'DevOps', 'AI', '人工智能', '机器学习', '深度学习', '前端', 
            '后端', '全栈', '数据库', 'SQL', 'NoSQL', 'MongoDB', 
            'Redis', 'Git', 'GitHub', 'CI/CD', '微服务', '云计算', 
            '区块链', '安全', '测试', 'Linux', 'Windows', 'MacOS', 
            'iOS', 'Android', '移动开发', 'Web开发', '算法', '数据结构'
        ]
        
        # 检查内容中是否包含这些关键词
        found_tags = []
        for keyword in tech_keywords:
            if keyword.lower() in content.lower():
                found_tags.append(keyword)
        
        return found_tags[:3]  # 最多返回3个标签
    
    def _enhance_content_format(self, title, content, use_rich_text=True):
        """增强内容格式化"""
        if not content:
            return ""
        
        # 处理正文内容
        content = content.strip()
        
        # 1. 不再添加标题到内容中，因为今日头条已经有单独的标题字段
        # 如果内容第一行是标题，移除它
        if content.startswith('# ') and title in content.split('\n')[0]:
            content = '\n'.join(content.split('\n')[1:]).strip()
        
        # 2. 优化段落格式
        paragraphs = content.split('\n\n')
        formatted_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # 处理标题 - 确保markdown标题正确转换
            if re.match(r'^#{1,6}\s+', para):
                # 确保标题格式正确，例如 "## 标题" 而不是 "#＃ 标题"
                para = re.sub(r'^(#{1,6})\s*', r'\1 ', para)
                formatted_paragraphs.append(f"\n{para}\n")
                continue
            
            # 处理可能被错误格式化的标题（例如 "##前言" 没有空格）
            if re.match(r'^#{1,6}[^#\s]', para):
                para = re.sub(r'^(#{1,6})([^#\s])', r'\1 \2', para)
                formatted_paragraphs.append(f"\n{para}\n")
                continue
            
            # 处理代码块
            if para.startswith('```'):
                formatted_paragraphs.append(para)
                continue
            
            # 处理引用块
            if para.startswith('>'):
                lines = para.split('\n')
                formatted_lines = []
                for line in lines:
                    if line.startswith('>'):
                        formatted_lines.append(line)
                    else:
                        formatted_lines.append(f"> {line}")
                formatted_paragraphs.append('\n'.join(formatted_lines))
                continue
            
            # 处理列表
            if re.match(r'^[-*+]\s|^\d+\.\s', para):
                lines = para.split('\n')
                # 保持列表项的原始缩进
                formatted_paragraphs.append('\n'.join(lines))
                continue
            
            # 处理普通段落
            # 将段落内的多个空格合并为一个
            para = re.sub(r'\s+', ' ', para)
            # 确保中文和英文之间有空格
            para = re.sub(r'([a-zA-Z])([\u4e00-\u9fff])', r'\1 \2', para)
            para = re.sub(r'([\u4e00-\u9fff])([a-zA-Z])', r'\1 \2', para)
            # 修复中文标点后面的空格
            para = re.sub(r'([，。！？；：、])\s+', r'\1', para)
            
            formatted_paragraphs.append(para)
        
        # 3. 合并处理后的内容
        content = '\n\n'.join(formatted_paragraphs)
        
        # 4. 最终的格式清理
        content = re.sub(r'\n{3,}', '\n\n', content)  # 删除多余的空行
        content = re.sub(r'[ \t]+\n', '\n', content)  # 删除行尾空格
        content = content.strip()
        
        if use_rich_text:
            print("🎨 正在将Markdown转换为富文本格式...")
            
            # 使用 markdown 库将 Markdown 转换为 HTML
            html_content = markdown.markdown(
                content,
                extensions=[
                    'markdown.extensions.extra',
                    'markdown.extensions.codehilite',
                    'markdown.extensions.tables',
                    'markdown.extensions.nl2br'
                ]
            )
            
            # 添加基本样式
            html_content = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif; line-height: 1.6; color: #333;">
                {html_content}
            </div>
            """
            
            # 使用今日头条富文本编辑器支持的格式
            # 替换标题样式
            html_content = re.sub(r'<h1>(.*?)</h1>', r'<h1 style="font-size: 24px; font-weight: bold; margin: 20px 0 10px;">\1</h1>', html_content)
            html_content = re.sub(r'<h2>(.*?)</h2>', r'<h2 style="font-size: 20px; font-weight: bold; margin: 18px 0 9px;">\1</h2>', html_content)
            html_content = re.sub(r'<h3>(.*?)</h3>', r'<h3 style="font-size: 18px; font-weight: bold; margin: 16px 0 8px;">\1</h3>', html_content)
            
            # 替换代码块样式
            html_content = re.sub(
                r'<pre><code>(.*?)</code></pre>',
                r'<pre style="background-color: #f6f8fa; border-radius: 3px; padding: 10px; overflow: auto;"><code>\1</code></pre>',
                html_content,
                flags=re.DOTALL
            )
            
            # 替换行内代码样式
            html_content = re.sub(
                r'<code>(.*?)</code>',
                r'<code style="background-color: #f6f8fa; border-radius: 3px; padding: 2px 4px; font-family: monospace;">\1</code>',
                html_content
            )
            
            # 替换引用块样式
            html_content = re.sub(
                r'<blockquote>(.*?)</blockquote>',
                r'<blockquote style="border-left: 4px solid #ddd; padding-left: 10px; margin-left: 0; color: #666;">\1</blockquote>',
                html_content,
                flags=re.DOTALL
            )
            
            # 替换列表样式
            html_content = re.sub(r'<ul>', r'<ul style="padding-left: 20px;">', html_content)
            html_content = re.sub(r'<ol>', r'<ol style="padding-left: 20px;">', html_content)
            
            print(f"✅ HTML格式化完成，最终长度: {len(html_content)} 字符")
            print("📝 格式化特性: HTML富文本、美化标题、代码高亮、适当段落间距")
            
            return html_content
        else:
            # 返回 Markdown 格式（用于保存文件）
            return content
    
    def save_article_file(self, title, content, tags):
        """保存文章到文件"""
        # 创建文件名
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)[:50]
        
        filename = f"forwarded-enhanced-{safe_title}.md"
        
        # 确保目录存在
        today = datetime.now().strftime('%Y-%m-%d')
        target_dir = f"articles/{today}"
        os.makedirs(target_dir, exist_ok=True)
        
        file_path = os.path.join(target_dir, filename)
        
        # 增强内容格式（保存Markdown版本）
        enhanced_content = self._enhance_content_format(title, content, use_rich_text=False)
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_content)
        
        print(f"💾 文章已保存: {file_path}")
        return file_path
    
    async def forward_to_toutiao(self, title, content, tags, account_file):
        """转发文章到今日头条"""
        print("🚀 开始发布到今日头条...")
        
        try:
            # 增强内容格式并转换为富文本
            enhanced_content = self._enhance_content_format(title, content, use_rich_text=True)
            
            # 创建文章发布对象
            article = TouTiaoArticle(
                title=title,
                content=enhanced_content,
                tags=tags,
                publish_date=0,  # 立即发布
                account_file=account_file,
                cover_path=None  # 自动生成封面
            )
            
            # 发布文章
            async with async_playwright() as playwright:
                await article.upload(playwright)
            
            print(f"✅ 文章发布成功: {title}")
            return True
            
        except Exception as e:
            print(f"❌ 文章发布失败: {e}")
            traceback.print_exc()
            return False

async def forward_article_from_file(file_path, account_file="cookiesFile/toutiao_cookie.json", save_file=True):
    """从本地文件转发文章到今日头条"""
    try:
        # 检查登录状态
        print("🔐 检查登录状态...")
        if not await toutiao_setup(account_file):
            print("❌ 登录状态失效，请重新登录")
            print("提示: 运行 python examples/login_toutiao.py 重新登录")
            return None
        print("✅ 登录状态正常")
        
        # 创建转发器
        forwarder = LocalArticleForwarder()
        
        # 获取文章内容
        title, content, tags = forwarder.read_local_article(file_path)
        
        if not title or not content:
            print("❌ 文章读取失败")
            return None
            
        print("✅ 文章读取成功:")
        print(f"📝 标题: {title}")
        print(f"📊 内容长度: {len(content)} 字符")
        print(f"🏷️ 标签: {tags}")
        
        # 保存文章（可选）
        if save_file:
            file_path = forwarder.save_article_file(title, content, tags)
            if file_path:
                print(f"💾 文章已保存: {file_path}")
        
        return {
            'title': title,
            'content': content,
            'tags': tags
        }
        
    except Exception as e:
        print(f"❌ 读取文章失败: {str(e)}")
        traceback.print_exc()
        return None

async def publish_article_to_toutiao(title, content, tags, account_file="cookiesFile/toutiao_cookie.json"):
    """发布文章到今日头条"""
    print(f"\n⚠️ 即将转发文章到今日头条:")
    print(f"📰 标题: {title}")
    print(f"📊 内容长度: {len(content)} 字符")
    print(f"🏷️ 标签: {tags}")
    print(f"🎨 排版: 已启用增强排版模式")
    print(f"🔄 格式: Markdown → 富文本格式")
    print(f"🔒 验证码: 如遇验证码将等待用户输入")
    
    # 自动确认转发，不再需要用户输入y
    print("\n📋 自动确认转发")
    print("⚠️ 注意: 如遇验证码，请在浏览器中手动输入")
    
    # 创建转发器
    forwarder = LocalArticleForwarder()
    
    # 转发到今日头条
    print("🚀 开始发布到今日头条...")
    success = await forwarder.forward_to_toutiao(title, content, tags, account_file)
    
    if success:
        print("\n🎉 文章转发完成！")
        print("📱 请登录今日头条查看发布结果")
        print("✨ 排版已优化，阅读体验更佳")
        print("🔄 内容已转换为富文本格式，无HTML代码")
    else:
        print("\n❌ 文章转发失败")
    
    return success

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='从本地文件转发文章到今日头条')
    parser.add_argument('file_path', help='要转发的本地Markdown文件路径')
    parser.add_argument('--no-save', action='store_false', dest='save_file',
                      help='不保存文章到本地')
    parser.add_argument('--preview', action='store_true',
                      help='预览模式，只显示文章内容不发布')
    parser.add_argument('--no-ai', action='store_false', dest='use_ai',
                      help='不使用AI增强功能')
    args = parser.parse_args()

    # 显示参数信息
    print(f"📄 目标文件: {args.file_path}")
    print(f"🔑 账号文件: cookiesFile/toutiao_cookie.json")
    print(f"💾 保存文件: {'是' if args.save_file else '否'}")
    print(f"👀 预览模式: {'是' if args.preview else '否'}")
    print(f"🤖 AI增强: {'是' if args.use_ai else '否'}")
    print(f"✨ 版本: WechatSync风格排版 v3.0 (增强代码块、标题美化)")
    print("🔗 本地文章转发工具 v1.0")
    print("=" * 60)

    try:
        # 获取文章内容
        article = await forward_article_from_file(
            args.file_path,
            save_file=args.save_file
        )
        
        if not article:
            print("❌ 文章获取失败")
            return

        article_title = article.get('title', '')
        article_content = article.get('content', '')
        article_tags = article.get('tags', [])
        
        # 使用AI增强内容
        if args.use_ai:
            try:
                from conf import OPENAI_API_KEY
                ai_enhancer = AIContentEnhancer(api_key=OPENAI_API_KEY)
                
                # AI增强内容
                enhanced = ai_enhancer.enhance_content(
                    title=article_title,
                    content=article_content,
                    tags=article_tags
                )
                article_title = enhanced["title"]
                article_content = enhanced["content"]
                
                # 生成优化的标签
                ai_tags = ai_enhancer.generate_seo_tags(article_title, article_content)
                if ai_tags:
                    article_tags.extend(ai_tags)
                    article_tags = list(set(article_tags))  # 去重
            except ImportError:
                print("⚠️ 未找到OpenAI API配置，跳过AI增强")
            except Exception as e:
                print(f"⚠️ AI增强过程出现错误: {str(e)}")

        if args.preview:
            print("\n📝 预览文章内容:")
            print("=" * 60)
            print(f"标题: {article_title}")
            print(f"标签: {article_tags}")
            print("-" * 60)
            print(article_content)
            print("=" * 60)
            return

        # 发布文章
        await publish_article_to_toutiao(
            title=article_title,
            content=article_content,
            tags=article_tags
        )

    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 