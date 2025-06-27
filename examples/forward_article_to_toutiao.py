#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文章链接转发到今日头条工具 v2.0
支持从各种网站抓取文章内容并转发到今日头条
优化排版，提升阅读体验
"""

import asyncio
import os
import sys
import re
import time
import hashlib
import textwrap
from datetime import datetime
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import markdown

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uploader.toutiao_uploader.main_final import TouTiaoArticle, toutiao_setup

class WechatSyncStyleFormatter:
    """优化版格式化器 - 解决空行过多、代码块显示和markdown渲染问题"""
    
    def __init__(self):
        self.code_languages = {
            'javascript': 'JavaScript', 'js': 'JavaScript',
            'typescript': 'TypeScript', 'ts': 'TypeScript', 
            'python': 'Python', 'py': 'Python',
            'java': 'Java', 'cpp': 'C++', 'c': 'C',
            'html': 'HTML', 'css': 'CSS', 'scss': 'SCSS',
            'shell': 'Shell', 'bash': 'Bash', 'sql': 'SQL',
            'json': 'JSON', 'xml': 'XML', 'yaml': 'YAML'
        }
    
    def html_to_text(self, html_content):
        """将HTML转换为清晰的文本格式 - 优化版"""
        if not html_content:
            return ""
        
        # 使用BeautifulSoup解析
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除不需要的元素
        for tag in soup(['script', 'style', 'meta', 'link', 'noscript', 'nav', 'header', 'footer']):
            tag.decompose()
        
        # 处理特殊元素
        self._preprocess_elements(soup)
        
        # 转换为文本
        result = self._element_to_text(soup)
        
        # 后处理 - 优化格式
        return self._postprocess_text(result)
    
    def _preprocess_elements(self, soup):
        """预处理HTML元素"""
        # 处理代码块
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code:
                language = self._detect_language(code)
                code_text = code.get_text()
                # 创建特殊标记
                marker = soup.new_tag('div')
                marker['data-type'] = 'codeblock'
                marker['data-language'] = language
                marker.string = code_text
                pre.replace_with(marker)
        
        # 处理内联代码
        for code in soup.find_all('code'):
            if code.parent.name != 'pre':
                code_text = code.get_text()
                marker = soup.new_tag('span')
                marker['data-type'] = 'inline-code'
                marker.string = code_text
                code.replace_with(marker)
        
        # 处理链接
        for a in soup.find_all('a'):
            href = a.get('href', '')
            text = a.get_text().strip()
            if text and href:
                marker = soup.new_tag('span')
                marker['data-type'] = 'link'
                marker['data-href'] = href
                marker.string = text
                a.replace_with(marker)
    
    def _detect_language(self, code_elem):
        """检测代码语言"""
        classes = code_elem.get('class', [])
        if isinstance(classes, list):
            for cls in classes:
                if cls.startswith('language-'):
                    lang = cls.replace('language-', '')
                    return self.code_languages.get(lang, lang.title())
                elif cls.startswith('lang-'):
                    lang = cls.replace('lang-', '')
                    return self.code_languages.get(lang, lang.title())
        
        # 尝试从父元素获取语言信息
        parent = code_elem.parent
        if parent and parent.get('class'):
            for cls in parent.get('class', []):
                if cls.startswith('language-'):
                    lang = cls.replace('language-', '')
                    return self.code_languages.get(lang, lang.title())
        
        return ''
    
    def _element_to_text(self, element):
        """将元素转换为文本 - 优化版"""
        if isinstance(element, NavigableString):
            return str(element).strip()
        
        if not hasattr(element, 'name'):
            return ""
        
        tag = element.name.lower()
        
        # 处理特殊数据类型
        if tag == 'div' and element.get('data-type') == 'codeblock':
            language = element.get('data-language', '')
            code_text = element.get_text()
            return self._format_code_block(code_text, language)
        
        elif tag == 'span' and element.get('data-type') == 'inline-code':
            return f"`{element.get_text()}`"
        
        elif tag == 'span' and element.get('data-type') == 'link':
            text = element.get_text()
            href = element.get('data-href', '')
            return f"[{text}]({href})"
        
        # 处理子元素
        children_text = []
        for child in element.children:
            child_text = self._element_to_text(child)
            if child_text:
                children_text.append(child_text)
        
        text = ' '.join(children_text) if children_text else element.get_text().strip()
        
        # 根据标签格式化 - 优化版
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag[1])
            return self._format_heading(text, level)
        
        elif tag == 'p':
            return text if text else ""  # 移除段落标签的额外换行
        
        elif tag in ['strong', 'b']:
            return f"**{text}**" if text else ""
        
        elif tag in ['em', 'i']:
            return f"*{text}*" if text else ""
        
        elif tag in ['ul', 'ol']:
            return self._format_list(element, tag)
        
        elif tag == 'li':
            return text
        
        elif tag == 'blockquote':
            return self._format_quote(text)
        
        elif tag == 'br':
            return "\n"
        
        elif tag == 'hr':
            return "\n---\n"
        
        elif tag in ['div', 'section', 'article']:
            return text if text else ""
        
        elif tag == 'table':
            return self._format_table(element)
        
        else:
            return text
    
    def _format_heading(self, text, level):
        """格式化标题 - 优化版"""
        if not text:
            return ""
        
        text = text.strip()
        
        if level == 1:
            return f"\n# {text}\n"
        elif level == 2:
            return f"\n## {text}\n"
        elif level == 3:
            return f"\n### {text}\n"
        elif level == 4:
            return f"\n#### {text}\n"
        elif level == 5:
            return f"\n##### {text}\n"
        else:
            return f"\n###### {text}\n"
    
    def _format_code_block(self, code_text, language=''):
        """格式化代码块 - 优化版"""
        if not code_text:
            return ""
        
        code_text = code_text.strip()
        
        if language:
            lang_display = self.code_languages.get(language.lower(), language)
            return f"\n```{language.lower()}\n{code_text}\n```\n"
        else:
            return f"\n```\n{code_text}\n```\n"
    
    def _format_list(self, element, list_type):
        """格式化列表 - 优化版"""
        items = []
        
        for i, li in enumerate(element.find_all('li', recursive=False), 1):
            li_text = self._element_to_text(li)
            if li_text:
                if list_type == 'ol':
                    items.append(f"{i}. {li_text}")
                else:
                    items.append(f"- {li_text}")
        
        if items:
            return f"\n" + "\n".join(items) + "\n"
        return ""
    
    def _format_quote(self, text):
        """格式化引用 - 优化版"""
        if not text:
            return ""
        
        text = text.strip()
        lines = text.split('\n')
        quoted_lines = [f"> {line.strip()}" for line in lines if line.strip()]
        
        if quoted_lines:
            return f"\n" + "\n".join(quoted_lines) + "\n"
        return ""
    
    def _format_table(self, table_element):
        """格式化表格 - 优化版"""
        if not table_element:
            return ""
        
        table_text = table_element.get_text().strip()
        return f"\n{table_text}\n" if table_text else ""
    
    def _postprocess_text(self, text):
        """后处理文本 - 优化版，解决空行过多问题"""
        if not text:
            return ""
        
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 先做基础的空行清理
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # 处理段落内容，智能添加换行
        lines = text.split('\n')
        processed_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            processed_lines.append(line)
            
            # 如果是标题，确保后面有空行
            if re.match(r'^#{1,6}\s', line):
                if i < len(lines) - 1 and lines[i + 1].strip():
                    processed_lines.append('')
            
            # 如果是代码块开始标记
            elif line.strip().startswith('```'):
                # 找到代码块结束标记
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('```'):
                    j += 1
                
                # 复制代码块内容
                for k in range(i + 1, j + 1):
                    if k < len(lines):
                        processed_lines.append(lines[k])
                
                # 确保代码块后有空行
                if j < len(lines) - 1 and lines[j + 1].strip():
                    processed_lines.append('')
                
                i = j  # 跳过已处理的代码块
            
            # 如果是列表项，不添加额外空行
            elif re.match(r'^[-*+]\s', line.strip()) or re.match(r'^\d+\.\s', line.strip()):
                pass  # 列表项之间不添加空行
            
            # 如果是引用，不添加额外空行
            elif line.strip().startswith('>'):
                pass  # 引用行之间不添加空行
            
            # 普通文本行的处理
            elif line.strip():
                # 检查下一行是否也是普通文本且够长
                if (i < len(lines) - 1 and 
                    lines[i + 1].strip() and
                    len(line.strip()) > 50 and  # 当前行足够长
                    len(lines[i + 1].strip()) > 50 and  # 下一行也足够长
                    not lines[i + 1].startswith(('#', '>', '-', '*', '+', '```', '|')) and
                    not line.endswith(('。', '！', '？', '；', '：', '，'))):  # 不是句子结尾
                    processed_lines.append('')  # 添加空行分隔段落
            
            i += 1
        
        result = '\n'.join(processed_lines)
        
        # 最终清理
        # 清理标题前后的多余空行
        result = re.sub(r'\n+(#{1,6}\s)', r'\n\n\1', result)
        result = re.sub(r'(#{1,6}\s[^\n]*)\n+', r'\1\n\n', result)
        
        # 清理代码块前后的多余空行
        result = re.sub(r'\n+(```)', r'\n\n\1', result)
        result = re.sub(r'(```[^\n]*\n[\s\S]*?\n```)\n+', r'\1\n\n', result)
        
        # 确保列表前后有适当的空行
        result = re.sub(r'\n+([-*+]\s)', r'\n\n\1', result)
        result = re.sub(r'((?:^[-*+]\s[^\n]*\n)+)\n*', r'\1\n', result, flags=re.MULTILINE)
        
        # 确保引用前后有适当的空行
        result = re.sub(r'\n+(>\s)', r'\n\n\1', result)
        result = re.sub(r'((?:^>\s[^\n]*\n)+)\n*', r'\1\n', result, flags=re.MULTILINE)
        
        # 最终清理：确保没有超过两个连续的空行
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        # 清理开头和结尾的空行
        result = result.strip()
        
        return result
    
    def markdown_to_text(self, markdown_content):
        """将Markdown转换为文本格式 - 优化版"""
        if not markdown_content:
            return ""
        
        # 先转换为HTML，再转换为文本
        try:
            md = markdown.Markdown(extensions=[
                'markdown.extensions.extra',
                'markdown.extensions.codehilite',
                'markdown.extensions.tables',
                'markdown.extensions.toc'
            ])
            html = md.convert(markdown_content)
            return self.html_to_text(html)
        except Exception as e:
            print(f"⚠️ Markdown转换失败，使用简化转换: {e}")
            return self._simple_markdown_to_text(markdown_content)
    
    def _simple_markdown_to_text(self, text):
        """简化的Markdown到文本转换 - 优化版"""
        if not text:
            return ""
        
        # 处理标题
        text = re.sub(r'^#{1}\s+(.+)$', r'\n# \1\n', text, flags=re.MULTILINE)
        text = re.sub(r'^#{2}\s+(.+)$', r'\n## \1\n', text, flags=re.MULTILINE)
        text = re.sub(r'^#{3}\s+(.+)$', r'\n### \1\n', text, flags=re.MULTILINE)
        text = re.sub(r'^#{4}\s+(.+)$', r'\n#### \1\n', text, flags=re.MULTILINE)
        text = re.sub(r'^#{5,6}\s+(.+)$', r'\n##### \1\n', text, flags=re.MULTILINE)
        
        # 处理代码块
        def replace_code_block(match):
            language = match.group(1) if match.group(1) else ''
            code = match.group(2)
            return self._format_code_block(code, language)
        
        text = re.sub(r'```(\w*)\n(.*?)\n```', replace_code_block, text, flags=re.DOTALL)
        
        # 处理内联代码
        text = re.sub(r'`([^`]+)`', r'`\1`', text)
        
        # 处理粗体和斜体
        text = re.sub(r'\*\*([^*]+)\*\*', r'**\1**', text)
        text = re.sub(r'\*([^*]+)\*', r'*\1*', text)
        
        # 处理引用
        text = re.sub(r'^>\s*(.+)$', r'> \1', text, flags=re.MULTILINE)
        
        # 处理列表
        text = re.sub(r'^[-*+]\s+(.+)$', r'- \1', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\.\s+(.+)$', r'1. \1', text, flags=re.MULTILINE)
        
        # 处理链接
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'[\1](\2)', text)
        
        # 处理分隔线
        text = re.sub(r'^---+$', '---', text, flags=re.MULTILINE)
        
        # 后处理
        return self._postprocess_text(text)

class EnhancedArticleForwarder:
    """增强版文章转发工具"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.site_configs = {
            'juejin.cn': self._extract_juejin,
            'cnblogs.com': self._extract_cnblogs,
            'csdn.net': self._extract_csdn,
            'jianshu.com': self._extract_jianshu,
            'zhihu.com': self._extract_zhihu,
            'segmentfault.com': self._extract_segmentfault,
            'oschina.net': self._extract_oschina,
        }
        
        # 初始化格式化器
        self.formatter = WechatSyncStyleFormatter()
        
        # 内容美化配置
        self.content_enhancers = {
            'emoji_mapping': {
                '前言': '📝', '介绍': '📖', '概述': '🔍',
                '安装': '⚙️', '配置': '🔧', '使用': '🚀',
                '示例': '💡', '例子': '💡', '代码': '💻',
                '总结': '📋', '结论': '🎯', '小结': '📝',
                '注意': '⚠️', '警告': '🚨', '提示': '💡',
                '优点': '✅', '缺点': '❌', '特点': '🎯',
                '步骤': '📝', '方法': '🔧', '技巧': '💡',
                '问题': '❓', '解决': '✅', '错误': '❌',
                '性能': '⚡', '安全': '🔒', '测试': '🧪'
            }
        }
    
    def _markdown_to_html(self, markdown_content):
        """将Markdown内容转换为HTML"""
        if not markdown_content:
            return ""
        
        try:
            # 重置转换器状态
            self.markdown_converter.reset()
            
            # 转换Markdown为HTML
            html_content = self.markdown_converter.convert(markdown_content)
            
            # 优化HTML格式
            html_content = self._optimize_html_format(html_content)
            
            return html_content
            
        except Exception as e:
            print(f"⚠️ Markdown转换失败: {e}")
            return markdown_content
    
    def _optimize_html_format(self, html_content):
        """优化HTML格式"""
        if not html_content:
            return ""
        
        # 为段落添加间距
        html_content = re.sub(r'<p>', '<p style="margin: 16px 0; line-height: 1.6;">', html_content)
        
        # 为标题添加样式
        html_content = re.sub(r'<h1>', '<h1 style="font-size: 24px; font-weight: bold; margin: 24px 0 16px 0; color: #333;">', html_content)
        html_content = re.sub(r'<h2>', '<h2 style="font-size: 22px; font-weight: bold; margin: 20px 0 14px 0; color: #333; border-bottom: 2px solid #eee; padding-bottom: 8px;">', html_content)
        html_content = re.sub(r'<h3>', '<h3 style="font-size: 20px; font-weight: bold; margin: 18px 0 12px 0; color: #333;">', html_content)
        html_content = re.sub(r'<h4>', '<h4 style="font-size: 18px; font-weight: bold; margin: 16px 0 10px 0; color: #333;">', html_content)
        html_content = re.sub(r'<h5>', '<h5 style="font-size: 16px; font-weight: bold; margin: 14px 0 8px 0; color: #333;">', html_content)
        html_content = re.sub(r'<h6>', '<h6 style="font-size: 14px; font-weight: bold; margin: 12px 0 6px 0; color: #333;">', html_content)
        
        # 为链接添加样式
        html_content = re.sub(r'<a ', '<a style="color: #1890ff; text-decoration: none;" ', html_content)
        
        # 为强调文本添加样式
        html_content = re.sub(r'<strong>', '<strong style="font-weight: bold; color: #333;">', html_content)
        html_content = re.sub(r'<em>', '<em style="font-style: italic; color: #666;">', html_content)
        
        # 为代码添加样式
        html_content = re.sub(
            r'<code>',
            '<code style="background-color: #f6f8fa; color: #d73a49; padding: 2px 4px; border-radius: 3px; font-family: monospace; font-size: 0.9em;">',
            html_content
        )
        
        # 为代码块添加样式
        html_content = re.sub(
            r'<pre>',
            '<pre style="background-color: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 6px; padding: 16px; overflow-x: auto; margin: 16px 0; font-family: monospace; font-size: 14px; line-height: 1.45;">',
            html_content
        )
        
        # 为引用块添加样式
        html_content = re.sub(
            r'<blockquote>',
            '<blockquote style="border-left: 4px solid #dfe2e5; margin: 16px 0; padding: 0 16px; color: #6a737d; background-color: #f8f9fa; border-radius: 0 6px 6px 0;">',
            html_content
        )
        
        # 为列表添加样式
        html_content = re.sub(r'<ul>', '<ul style="margin: 16px 0; padding-left: 24px;">', html_content)
        html_content = re.sub(r'<ol>', '<ol style="margin: 16px 0; padding-left: 24px;">', html_content)
        html_content = re.sub(r'<li>', '<li style="margin: 4px 0; line-height: 1.6;">', html_content)
        
        # 为表格添加样式
        html_content = re.sub(r'<table>', '<table style="border-collapse: collapse; width: 100%; border: 1px solid #e1e4e8; margin: 16px 0;">', html_content)
        html_content = re.sub(r'<th>', '<th style="background-color: #f6f8fa; border: 1px solid #e1e4e8; padding: 8px 12px; text-align: left; font-weight: bold;">', html_content)
        html_content = re.sub(r'<td>', '<td style="border: 1px solid #e1e4e8; padding: 8px 12px;">', html_content)
        
        return html_content
    
    def _markdown_to_rich_text(self, markdown_content):
        """将Markdown内容转换为富文本格式（不是HTML代码）"""
        if not markdown_content:
            return ""
        
        try:
            # 先转换为HTML
            html_content = self.markdown_converter.convert(markdown_content)
            
            # 将HTML转换为纯文本，但保留格式效果
            rich_text = self._html_to_formatted_text(html_content)
            
            return rich_text
            
        except Exception as e:
            print(f"⚠️ 富文本转换失败: {e}")
            return self._markdown_to_plain_text(markdown_content)
    
    def _html_to_formatted_text(self, html_content):
        """将HTML转换为格式化的纯文本"""
        if not html_content:
            return ""
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 递归处理HTML元素，转换为格式化文本
        def process_html_element(element, depth=0):
            if isinstance(element, NavigableString):
                return str(element).strip()
            
            if not hasattr(element, 'name'):
                return ""
            
            tag_name = element.name.lower()
            
            # 获取子元素内容
            children_text = []
            for child in element.children:
                child_text = process_html_element(child, depth + 1)
                if child_text:
                    children_text.append(child_text)
            
            content = ' '.join(children_text) if children_text else element.get_text().strip()
            
            # 根据HTML标签转换为相应的文本格式
            if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(tag_name[1])
                if content:
                    # 使用不同的装饰符表示标题层级
                    if level == 1:
                        return f"\n\n{'=' * 50}\n{content}\n{'=' * 50}\n\n"
                    elif level == 2:
                        return f"\n\n{'-' * 40}\n{content}\n{'-' * 40}\n\n"
                    elif level == 3:
                        return f"\n\n▶ {content}\n{'-' * len(content)}\n\n"
                    else:
                        return f"\n\n● {content}\n\n"
            
            elif tag_name == 'p':
                return f"\n\n{content}\n\n"
            
            elif tag_name in ['strong', 'b']:
                return f"【{content}】"  # 使用中文括号表示粗体
            
            elif tag_name in ['em', 'i']:
                return f"《{content}》"  # 使用书名号表示斜体
            
            elif tag_name == 'code':
                if content:
                    return f"「{content}」"  # 使用直角引号表示代码
            
            elif tag_name == 'pre':
                if content:
                    return f"\n\n┌─ 代码示例 ─┐\n{content}\n└─────────┘\n\n"
            
            elif tag_name in ['ul', 'ol']:
                if children_text:
                    return f"\n\n" + "\n".join(children_text) + "\n\n"
            
            elif tag_name == 'li':
                if content:
                    return f"• {content}"
            
            elif tag_name == 'blockquote':
                if content:
                    lines = content.split('\n')
                    quoted_lines = [f"┃ {line.strip()}" for line in lines if line.strip()]
                    return f"\n\n" + "\n".join(quoted_lines) + "\n\n"
            
            elif tag_name == 'a':
                href = element.get('href', '')
                if text_content and href:
                    return f"{text_content}（{href}）"
                else:
                    return text_content
            
            elif tag_name == 'table':
                return f"\n\n📊 表格数据：\n{content}\n\n"
            
            elif tag_name in ['th', 'td']:
                return f" {content} |"
            
            elif tag_name == 'tr':
                return f"|{content}\n"
            
            elif tag_name == 'hr':
                return f"\n\n{'─' * 50}\n\n"
            
            elif tag_name == 'br':
                return "\n"
            
            else:
                return content
        
        # 处理整个HTML文档
        result = process_html_element(soup)
        
        # 清理多余的空行
        if result:
            result = re.sub(r'\n{3,}', '\n\n', result)
            result = result.strip()
        
        return result
    
    def _markdown_to_plain_text(self, markdown_content):
        """将Markdown转换为纯文本（备用方案）"""
        if not markdown_content:
            return ""
        
        # 简单的Markdown到文本转换
        text = markdown_content
        
        # 处理标题
        text = re.sub(r'^#{1}\s+(.+)$', r'\n\n=== \1 ===\n\n', text, flags=re.MULTILINE)
        text = re.sub(r'^#{2}\s+(.+)$', r'\n\n--- \1 ---\n\n', text, flags=re.MULTILINE)
        text = re.sub(r'^#{3,6}\s+(.+)$', r'\n\n▶ \1\n\n', text, flags=re.MULTILINE)
        
        # 处理粗体和斜体
        text = re.sub(r'\*\*(.+?)\*\*', r'【\1】', text)
        text = re.sub(r'\*(.+?)\*', r'《\1》', text)
        
        # 处理代码
        text = re.sub(r'`(.+?)`', r'「\1」', text)
        text = re.sub(r'```[\w]*\n(.*?)\n```', r'\n\n┌─ 代码示例 ─┐\n\1\n└─────────┘\n\n', text, flags=re.DOTALL)
        
        # 处理引用
        text = re.sub(r'^>\s*(.+)$', r'┃ \1', text, flags=re.MULTILINE)
        
        # 处理列表
        text = re.sub(r'^[-*+]\s+(.+)$', r'- \1', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\.\s+(.+)$', r'• \1', text, flags=re.MULTILINE)
        
        # 处理链接
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1（\2）', text)
        
        # 处理分隔线
        text = re.sub(r'^---+$', '─' * 50, text, flags=re.MULTILINE)
        
        # 清理多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _clean_text(self, text):
        """清理文本内容"""
        if not text:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # 多个换行变为两个
        text = re.sub(r'[ \t]+', ' ', text)  # 多个空格变为一个
        text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)  # 去除行首行尾空格
        
        # 清理特殊字符
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)  # 零宽字符
        text = text.strip()
        
        return text
    
    def _remove_unwanted_elements(self, soup):
        """移除不需要的HTML元素"""
        # 移除script、style、nav等不需要的标签
        unwanted_tags = [
            'script', 'style', 'nav', 'header', 'footer', 'aside',
            'advertisement', 'ad', 'sidebar', 'menu', 'breadcrumb',
            'iframe', 'embed', 'object'
        ]
        
        for tag_name in unwanted_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # 移除常见的广告和无关内容的class/id
        unwanted_patterns = [
            r'ad[_-]', r'advertisement', r'sponsor', r'promo', 
            r'sidebar', r'related', r'comment', r'footer', 
            r'header', r'nav', r'breadcrumb', r'pagination', 
            r'share', r'social', r'tracking', r'analytics'
        ]
        
        for pattern in unwanted_patterns:
            for tag in soup.find_all(class_=re.compile(pattern, re.I)):
                tag.decompose()
            for tag in soup.find_all(id=re.compile(pattern, re.I)):
                tag.decompose()
        
        return soup
    
    def _enhance_title_with_emoji(self, title):
        """为标题添加合适的emoji"""
        title_lower = title.lower()
        
        for keyword, emoji in self.content_enhancers['emoji_mapping'].items():
            if keyword in title_lower:
                if not title.startswith(emoji):
                    return f"{emoji} {title}"
                break
        
        return title
    
    def _detect_code_language(self, code_elem):
        """检测代码语言"""
        # 从class属性检测
        class_attr = code_elem.get('class', [])
        if class_attr:
            for cls in class_attr:
                for lang_key, lang_name in self.content_enhancers['code_languages'].items():
                    if lang_key in cls.lower():
                        return lang_key
        
        # 从内容特征检测
        code_text = code_elem.get_text()[:200].lower()
        
        language_patterns = {
            'javascript': [r'function\s*\(', r'const\s+\w+', r'let\s+\w+', r'console\.log'],
            'python': [r'def\s+\w+\(', r'import\s+\w+', r'from\s+\w+\s+import', r'print\('],
            'java': [r'public\s+class', r'public\s+static\s+void', r'System\.out\.println'],
            'css': [r'\.\w+\s*{', r'#\w+\s*{', r'@media', r'flex'],
            'html': [r'<html', r'<div', r'<span', r'<!DOCTYPE'],
            'json': [r'^\s*[{\[]', r'"\w+":', r'},\s*"'],
            'sql': [r'SELECT\s+', r'FROM\s+', r'WHERE\s+', r'INSERT\s+INTO']
        }
        
        for lang, patterns in language_patterns.items():
            if any(re.search(pattern, code_text, re.I) for pattern in patterns):
                return lang
        
        return ''
    
    def _format_code_block(self, code_elem):
        """格式化代码块"""
        code_text = code_elem.get_text()
        
        # 检测语言
        language = self._detect_code_language(code_elem)
        lang_display = self.content_enhancers['code_languages'].get(language, language)
        
        # 清理代码文本
        code_text = code_text.strip()
        
        # 添加语言标注
        if lang_display:
            return f"\n\n💻 **{lang_display} 代码示例：**\n\n```{language}\n{code_text}\n```\n\n"
        else:
            return f"\n\n```\n{code_text}\n```\n\n"
    
    def _format_list_item(self, li_elem, list_type='ul', index=1):
        """格式化列表项"""
        text = li_elem.get_text().strip()
        
        if list_type == 'ol':
            prefix = f"{index}."
        else:
            # 根据内容选择不同的前缀
            if any(keyword in text.lower() for keyword in ['优点', '好处', '优势']):
                prefix = "✅"
            elif any(keyword in text.lower() for keyword in ['缺点', '问题', '不足']):
                prefix = "❌"
            elif any(keyword in text.lower() for keyword in ['注意', '警告', '小心']):
                prefix = "⚠️"
            elif any(keyword in text.lower() for keyword in ['重要', '关键', '核心']):
                prefix = "🔑"
            else:
                prefix = "•"
        
        return f"{prefix} {text}"
    
    def _extract_juejin(self, soup, url):
        """提取掘金文章内容"""
        # 移除不需要的元素
        soup = self._remove_unwanted_elements(soup)
        
        # 提取标题
        title_selectors = [
            'h1.article-title',
            '.article-title', 
            'h1',
            '[data-page-title]'
        ]
        
        title = "未知标题"
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text().strip()
                break
        
        # 查找文章内容容器
        content_selectors = [
            '.markdown-body',
            '.article-content', 
            '[data-v-md-line]',
            '.content',
            'article',
            '.post-content'
        ]
        
        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break
        
        if not content_elem:
            # 如果没找到特定容器，尝试找主要内容区域
            main_content = soup.find('main') or soup.find('div', class_=re.compile(r'content|article|post'))
            if main_content:
                content_elem = main_content
        
        content = ""
        if content_elem:
            # 使用新的格式化器转换HTML为文本
            content = self.formatter.html_to_text(str(content_elem))
        
        # 提取标签
        tags = self._extract_tags_juejin(soup)
        
        return title, content, tags
    
    def _extract_cnblogs(self, soup, url):
        """提取博客园文章内容"""
        soup = self._remove_unwanted_elements(soup)
        
        title_elem = soup.find('h1', class_='postTitle') or soup.find('h1')
        title = title_elem.get_text().strip() if title_elem else "未知标题"
        
        content_elem = soup.find('div', id='cnblogs_post_body') or soup.find('div', class_='postBody')
        content = self._html_to_markdown_enhanced(content_elem) if content_elem else ""
        
        tags = ['技术分享', '博客园']
        return title, content, tags
    
    def _extract_csdn(self, soup, url):
        """提取CSDN文章内容"""
        soup = self._remove_unwanted_elements(soup)
        
        title_elem = soup.find('h1', class_='title-article') or soup.find('h1')
        title = title_elem.get_text().strip() if title_elem else "未知标题"
        
        content_elem = soup.find('div', id='content_views') or soup.find('div', class_='markdown_views')
        content = self._html_to_markdown_enhanced(content_elem) if content_elem else ""
        
        # 提取CSDN标签
        tag_elems = soup.find_all('a', class_='tag-link')
        tags = [tag.get_text().strip() for tag in tag_elems[:5]] if tag_elems else ['技术分享', 'CSDN']
        
        return title, content, tags
    
    def _extract_jianshu(self, soup, url):
        """提取简书文章内容"""
        soup = self._remove_unwanted_elements(soup)
        
        title_elem = soup.find('h1', class_='title') or soup.find('h1')
        title = title_elem.get_text().strip() if title_elem else "未知标题"
        
        content_elem = soup.find('div', class_='show-content') or soup.find('article')
        content = self._html_to_markdown_enhanced(content_elem) if content_elem else ""
        
        tags = ['技术分享', '简书']
        return title, content, tags
    
    def _extract_zhihu(self, soup, url):
        """提取知乎文章内容"""
        soup = self._remove_unwanted_elements(soup)
        
        title_elem = soup.find('h1', class_='Post-Title') or soup.find('h1')
        title = title_elem.get_text().strip() if title_elem else "未知标题"
        
        content_elem = soup.find('div', class_='RichText') or soup.find('div', class_='Post-RichTextContainer')
        content = self._html_to_markdown_enhanced(content_elem) if content_elem else ""
        
        # 提取知乎话题标签
        topic_elems = soup.find_all('a', class_='TopicLink')
        tags = [topic.get_text().strip() for topic in topic_elems[:5]] if topic_elems else ['知识分享', '知乎']
        
        return title, content, tags
    
    def _extract_segmentfault(self, soup, url):
        """提取SegmentFault文章内容"""
        soup = self._remove_unwanted_elements(soup)
        
        title_elem = soup.find('h1', class_='article__title') or soup.find('h1')
        title = title_elem.get_text().strip() if title_elem else "未知标题"
        
        content_elem = soup.find('div', class_='article__content') or soup.find('div', class_='markdown-body')
        content = self._html_to_markdown_enhanced(content_elem) if content_elem else ""
        
        # 提取标签
        tag_elems = soup.find_all('a', class_='article-tag')
        tags = [tag.get_text().strip() for tag in tag_elems[:5]] if tag_elems else ['技术分享', 'SegmentFault']
        
        return title, content, tags
    
    def _extract_oschina(self, soup, url):
        """提取开源中国文章内容"""
        soup = self._remove_unwanted_elements(soup)
        
        title_elem = soup.find('h1', class_='article-box__title') or soup.find('h1')
        title = title_elem.get_text().strip() if title_elem else "未知标题"
        
        content_elem = soup.find('div', class_='article-detail') or soup.find('div', class_='content')
        content = self._html_to_markdown_enhanced(content_elem) if content_elem else ""
        
        tags = ['技术分享', '开源中国']
        return title, content, tags
    
    def _extract_tags_juejin(self, soup):
        """提取掘金文章标签"""
        tag_selectors = [
            '.tag-list .tag',
            '.article-tag',
            '.tag',
            '[data-tag]'
        ]
        
        tags = []
        for selector in tag_selectors:
            tag_elems = soup.select(selector)
            if tag_elems:
                tags = [tag.get_text().strip() for tag in tag_elems[:6] if tag.get_text().strip()]
                break
        
        if not tags:
            tags = ['技术分享', '掘金']
        
        return tags
    
    def _html_to_markdown_enhanced(self, element):
        """增强版HTML到Markdown转换"""
        if not element:
            return ""
        
        def process_element(elem, depth=0):
            """递归处理HTML元素"""
            if isinstance(elem, NavigableString):
                text = str(elem).strip()
                return text if text else ""
            
            if not isinstance(elem, Tag):
                return ""
            
            tag_name = elem.name.lower()
            
            # 跳过不需要的标签
            if tag_name in ['script', 'style', 'meta', 'link', 'head']:
                return ""
            
            # 获取子元素内容
            children_content = []
            for child in elem.children:
                child_result = process_element(child, depth + 1)
                if child_result:
                    children_content.append(child_result)
            
            text_content = ' '.join(children_content) if children_content else elem.get_text().strip()
            
            # 根据标签类型进行转换
            if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(tag_name[1])
                if text_content:
                    # 为标题添加emoji
                    enhanced_title = self._enhance_title_with_emoji(text_content)
                    return f"\n\n{'#' * level} {enhanced_title}\n\n"
            
            elif tag_name == 'p':
                if text_content:
                    return f"\n\n{text_content}\n\n"
            
            elif tag_name in ['strong', 'b']:
                if text_content:
                    return f"**{text_content}**"
            
            elif tag_name in ['em', 'i']:
                if text_content:
                    return f"*{text_content}*"
            
            elif tag_name == 'code' and elem.parent.name != 'pre':
                if text_content:
                    return f"`{text_content}`"
            
            elif tag_name == 'pre':
                # 处理代码块
                code_elem = elem.find('code')
                if code_elem:
                    return self._format_code_block(code_elem)
                else:
                    return f"\n\n```\n{text_content}\n```\n\n"
            
            elif tag_name in ['ul', 'ol']:
                # 处理列表
                list_items = []
                for i, li in enumerate(elem.find_all('li', recursive=False), 1):
                    li_content = process_element(li, depth + 1)
                    if li_content:
                        formatted_item = self._format_list_item(li, tag_name, i)
                        list_items.append(formatted_item)
                
                if list_items:
                    return f"\n\n" + "\n".join(list_items) + "\n\n"
            
            elif tag_name == 'li':
                return text_content
            
            elif tag_name == 'blockquote':
                if text_content:
                    # 处理引用块
                    quoted_lines = text_content.split('\n')
                    quoted_text = '\n'.join(f"> 💡 {line.strip()}" for line in quoted_lines if line.strip())
                    return f"\n\n{quoted_text}\n\n"
            
            elif tag_name == 'a':
                href = element.get('href', '')
                if text_content and href:
                    return f"[{text_content}]({href})"
                else:
                    return text_content
            
            elif tag_name == 'img':
                alt = element.get('alt', '图片')
                src = element.get('src', '')
                if src:
                    return f"\n\n![{alt}]({src})\n\n"
            
            elif tag_name in ['table']:
                return f"\n\n📊 **数据表格**\n\n{text_content}\n\n"
            
            elif tag_name in ['br']:
                return "\n"
            
            elif tag_name in ['hr']:
                return f"\n\n---\n\n"
            
            elif tag_name in ['div', 'section', 'article']:
                # 对于容器元素，返回子元素内容
                if children_content:
                    return ' '.join(children_content)
                else:
                    return text_content
            
            else:
                return text_content
        
        # 处理整个元素
        result = process_element(element)
        
        # 清理和格式化结果
        if result:
            result = self._clean_text(result)
            # 确保段落之间有适当的分隔
            result = re.sub(r'\n{3,}', '\n\n', result)
            # 清理列表格式
            result = re.sub(r'\n+(•|✅|❌|⚠️|🔑|\d+\.)\s+', r'\n\1 ', result)
            
        return result
    
    def _extract_generic(self, soup, url):
        """通用文章内容提取"""
        soup = self._remove_unwanted_elements(soup)
        
        # 尝试多种标题选择器
        title_selectors = ['h1', '.title', '.article-title', '.post-title', '[data-title]']
        title = "未知标题"
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text().strip()
                break
        
        # 尝试多种内容选择器
        content_selectors = [
            'article', '.content', '.article-content', '.post-content',
            '.markdown-body', '.article-body', '.entry-content',
            'main', '.main-content', '.post-body'
        ]
        content = ""
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = self._html_to_markdown_enhanced(content_elem)
                if len(content) > 100:  # 确保获取到足够的内容
                    break
        
        # 如果还是没有找到内容，尝试智能提取
        if not content or len(content) < 100:
            content = self._smart_content_extraction(soup)
        
        tags = ['文章转发', '技术分享']
        return title, content, tags
    
    def _smart_content_extraction(self, soup):
        """智能内容提取算法"""
        # 找到所有可能包含内容的div
        content_divs = soup.find_all('div')
        
        best_content = ""
        max_text_length = 0
        
        for div in content_divs:
            # 跳过明显的导航、广告等区域
            div_class = ' '.join(div.get('class', [])).lower()
            div_id = (div.get('id') or '').lower()
            
            skip_patterns = ['nav', 'menu', 'sidebar', 'footer', 'header', 'ad', 'comment']
            if any(pattern in div_class or pattern in div_id for pattern in skip_patterns):
                continue
            
            div_text = div.get_text().strip()
            
            # 选择文本最长的div作为主要内容
            if len(div_text) > max_text_length:
                max_text_length = len(div_text)
                best_content = self._html_to_markdown_enhanced(div)
        
        return best_content
    
    async def fetch_article(self, url):
        """获取文章内容"""
        print(f"🌐 正在获取文章: {url}")
        
        try:
            # 发送HTTP请求
            response = requests.get(url, headers=self.headers, timeout=30)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                return None, None, None
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 根据网站类型选择提取器
            domain = urlparse(url).netloc.lower()
            extractor = None
            
            for site, extract_func in self.site_configs.items():
                if site in domain:
                    extractor = extract_func
                    break
            
            if not extractor:
                extractor = self._extract_generic
            
            title, content, tags = extractor(soup, url)
            
            print(f"✅ 文章获取成功:")
            print(f"📝 标题: {title}")
            print(f"📊 内容长度: {len(content)} 字符")
            print(f"🏷️ 标签: {tags}")
            
            return title, content, tags
            
        except Exception as e:
            print(f"❌ 获取文章失败: {e}")
            return None, None, None
    
    def _enhance_content_format(self, title, content, url, use_rich_text=True):
        """增强内容格式 - wechatSync简洁风格"""
        # 构建基础内容结构
        enhanced_content = f"# {title}\n\n"
        
        # 添加来源信息 - 简洁样式
        enhanced_content += f"> **原文链接**: {url}\n"
        enhanced_content += f"> **转发时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        enhanced_content += f"> **内容优化**: 已优化排版格式，提升阅读体验\n\n"
        enhanced_content += "---\n\n"
        
        # 处理主要内容
        if content:
            # 使用简洁风格格式化器处理内容
            if use_rich_text:
                print("🎨 正在使用wechatSync简洁风格格式化器处理内容...")
                # 如果内容是HTML，直接转换
                if '<' in content and '>' in content:
                    formatted_content = self.formatter.html_to_text(content)
                else:
                    # 如果是Markdown，先转换
                    formatted_content = self.formatter.markdown_to_text(content)
                
                # 调整标题层级（避免与主标题冲突）
                formatted_content = re.sub(r'^# ', '## ', formatted_content, flags=re.MULTILINE)
                formatted_content = re.sub(r'^## ', '### ', formatted_content, flags=re.MULTILINE)
                
                enhanced_content += formatted_content
            else:
                # 简单文本处理
                content = self._clean_text(content)
                # 应用基本格式化
                content = self.formatter._simple_markdown_to_text(content)
                enhanced_content += content
        else:
            enhanced_content += "暂无内容摘要，请查看原文链接获取完整内容。\n\n"
        
        print(f"✅ 内容格式化完成，最终长度: {len(enhanced_content)} 字符")
        print(f"📝 格式化特性: 简洁标题、清晰代码块、适当段落间距")
        return enhanced_content
    
    def _optimize_content_spacing(self, content):
        """优化内容间距"""
        if not content:
            return ""
        
        # 确保代码块前后有空行
        content = re.sub(r'([^\n])\n(```)', r'\1\n\n\2', content)
        content = re.sub(r'(```[^\n]*\n.*?\n```)\n([^\n])', r'\1\n\n\2', content, flags=re.DOTALL)
        
        # 确保标题前后有空行
        content = re.sub(r'([^\n])\n(#{1,6}\s)', r'\1\n\n\2', content)
        content = re.sub(r'(#{1,6}\s[^\n]*)\n([^\n#])', r'\1\n\n\2', content)
        
        # 确保列表前后有空行
        content = re.sub(r'([^\n])\n([-*+]\s|[0-9]+\.\s)', r'\1\n\n\2', content)
        
        # 确保引用前后有空行
        content = re.sub(r'([^\n])\n(>\s)', r'\1\n\n\2', content)
        
        # 清理多余的空行
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        content = re.sub(r'\n{3}', '\n\n', content)
        
        return content
    
    def _smart_format_content(self, content):
        """智能格式化内容"""
        if not content:
            return ""
        
        # 确保标题层级正确（避免与主标题冲突）
        content = re.sub(r'^# ', '## ', content, flags=re.MULTILINE)
        content = re.sub(r'^## ', '### ', content, flags=re.MULTILINE)
        content = re.sub(r'^### ', '#### ', content, flags=re.MULTILINE)
        content = re.sub(r'^#### ', '##### ', content, flags=re.MULTILINE)
        
        # 修复代码块格式
        content = self._fix_code_blocks(content)
        
        # 优化段落分隔
        content = self._optimize_paragraphs(content)
        
        # 优化列表格式
        content = self._optimize_lists(content)
        
        # 添加emoji增强可读性
        content = self._add_contextual_emojis(content)
        
        return content
    
    def _fix_code_blocks(self, content):
        """修复代码块格式"""
        # 修复代码块格式（确保前后有空行）
        content = re.sub(r'```(\w*)\n', r'\n```\1\n', content)
        content = re.sub(r'\n```\n', r'\n```\n\n', content)
        
        # 修复内联代码格式（确保前后有适当空格）
        content = re.sub(r'([^\s])`([^`]+)`([^\s])', r'\1 `\2` \3', content)
        
        return content
    
    def _optimize_paragraphs(self, content):
        """优化段落分隔"""
        # 确保段落之间有适当的空行
        lines = content.split('\n')
        optimized_lines = []
        
        for i, line in enumerate(lines):
            optimized_lines.append(line)
            
            # 如果当前行不是空行，下一行也不是空行，且下一行不是特殊格式
            if (i < len(lines) - 1 and 
                line.strip() and 
                lines[i + 1].strip() and
                not lines[i + 1].startswith(('#', '>', '-', '*', '+', '1.', '```', '|')) and
                not line.startswith(('#', '>', '-', '*', '+', '```', '|'))):
                
                # 检查是否需要添加空行
                if not any(lines[i + 1].startswith(prefix) for prefix in ['•', '┃', '【', '《']):
                    optimized_lines.append('')
        
        return '\n'.join(optimized_lines)
    
    def _optimize_lists(self, content):
        """优化列表格式"""
        # 确保列表项前后有适当的空行
        content = re.sub(r'^([-*+•]\s.+)$', r'\n\1', content, flags=re.MULTILINE)
        content = re.sub(r'^(\d+\.\s.+)$', r'\n\1', content, flags=re.MULTILINE)
        
        # 清理多余的空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content
    
    def _add_contextual_emojis(self, content):
        """根据上下文添加emoji"""
        # 为特定关键词段落添加emoji
        emoji_patterns = {
            r'^(注意|警告|重要)': '⚠️',
            r'^(技巧|技术|方法)': '💡',
            r'^(示例|例子|演示)': '💻',
            r'^(总结|结论|小结)': '📋',
            r'^(优点|好处|优势)': '✅',
            r'^(缺点|问题|错误)': '❌',
            r'^(步骤|流程|过程)': '📝'
        }
        
        for pattern, emoji in emoji_patterns.items():
            content = re.sub(pattern, f'{emoji} \\1', content, flags=re.MULTILINE)
        
        return content
    
    def _markdown_to_rich_text_v2(self, markdown_content):
        """优化版Markdown到富文本转换 v2.0"""
        if not markdown_content:
            return ""
        
        try:
            # 先转换为HTML
            html_content = self.markdown_converter.convert(markdown_content)
            
            # 使用改进的HTML到文本转换
            rich_text = self._html_to_formatted_text_v2(html_content)
            
            return rich_text
            
        except Exception as e:
            print(f"⚠️ 富文本转换失败: {e}")
            return self._markdown_to_plain_text_v2(markdown_content)
    
    def _html_to_formatted_text_v2(self, html_content):
        """改进版HTML到格式化文本转换"""
        if not html_content:
            return ""
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        def process_element(element, depth=0):
            if isinstance(element, NavigableString):
                text = str(element).strip()
                return text if text else ""
            
            if not hasattr(element, 'name'):
                return ""
            
            tag_name = element.name.lower()
            
            # 获取所有子元素的文本
            children_texts = []
            for child in element.children:
                child_text = process_element(child, depth + 1)
                if child_text:
                    children_texts.append(child_text)
            
            content = ' '.join(children_texts) if children_texts else ""
            
            # 根据标签类型格式化
            if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(tag_name[1])
                if content:
                    if level <= 2:
                        return f"\n\n{'=' * 60}\n{'  ' * (level-1)}{content}\n{'=' * 60}\n\n"
                    elif level == 3:
                        return f"\n\n▶ {content}\n{'─' * min(len(content), 40)}\n\n"
                    else:
                        return f"\n\n● {content}\n\n"
                        
            elif tag_name == 'p':
                if content:
                    return f"\n\n{content}\n\n"
                    
            elif tag_name in ['strong', 'b']:
                return f"**{content}**" if content else ""
                
            elif tag_name in ['em', 'i']:
                return f"*{content}*" if content else ""
                
            elif tag_name == 'code':
                return f"`{content}`" if content else ""
            
            elif tag_name == 'pre':
                if content:
                    # 检测代码语言
                    code_elem = element.find('code')
                    language = ""
                    if code_elem and code_elem.get('class'):
                        classes = ' '.join(code_elem.get('class', []))
                        lang_match = re.search(r'language-(\w+)', classes)
                        if lang_match:
                            language = lang_match.group(1).upper()
                    
                    if language:
                        return f"\n\n💻 **{language} 代码示例：**\n```\n{content}\n```\n\n"
                    else:
                        return f"\n\n💻 **代码示例：**\n```\n{content}\n```\n\n"
                        
            elif tag_name in ['ul', 'ol']:
                if children_texts:
                    list_content = '\n'.join(children_texts)
                    return f"\n\n{list_content}\n\n"
                    
            elif tag_name == 'li':
                return f"• {content}" if content else ""
            
            elif tag_name == 'blockquote':
                if content:
                    lines = content.split('\n')
                    quoted_lines = [f"> {line.strip()}" for line in lines if line.strip()]
                    return f"\n\n" + '\n'.join(quoted_lines) + "\n\n"
                    
            elif tag_name == 'a':
                href = element.get('href', '')
                if text_content and href:
                    return f"[{text_content}]({href})"
                else:
                    return text_content
            
            elif tag_name == 'img':
                alt = element.get('alt', '图片')
                src = element.get('src', '')
                if src:
                    return f"\n\n![{alt}]({src})\n\n"
            
            elif tag_name in ['br']:
                return "\n"
            
            elif tag_name in ['hr']:
                return f"\n\n{'─' * 50}\n\n"
            
            elif tag_name in ['div', 'section', 'article']:
                # 对于容器元素，返回子元素内容
                if children_texts:
                    return ' '.join(children_texts)
                else:
                    return text_content
            
            else:
                return text_content
        
        # 处理整个文档
        result = process_element(soup)
        
        # 后处理：清理格式
        if result:
            # 清理多余的空行
            result = re.sub(r'\n{4,}', '\n\n\n', result)
            result = re.sub(r'\n{3}', '\n\n', result)
            
            # 确保代码块前后有空行
            result = re.sub(r'([^\n])\n(```)', r'\1\n\n\2', result)
            result = re.sub(r'(```)\n([^\n])', r'\1\n\n\2', result)
            
            # 确保标题前后有适当空行
            result = re.sub(r'([^\n])\n(▶|●|=)', r'\1\n\n\2', result)
            
            result = result.strip()
        
        return result
    
    def _markdown_to_plain_text_v2(self, markdown_content):
        """改进版Markdown到纯文本转换（备用方案）"""
        if not markdown_content:
            return ""
        
        text = markdown_content
        
        # 处理标题（保持层级但美化格式）
        text = re.sub(r'^#{1}\s+(.+)$', r'\n\n════════════════════════════════════════\n\1\n════════════════════════════════════════\n\n', text, flags=re.MULTILINE)
        text = re.sub(r'^#{2}\s+(.+)$', r'\n\n▶ \1\n────────────────────────────────\n\n', text, flags=re.MULTILINE)
        text = re.sub(r'^#{3,6}\s+(.+)$', r'\n\n● \1\n\n', text, flags=re.MULTILINE)
        
        # 处理代码块
        text = re.sub(r'```(\w*)\n(.*?)\n```', r'\n\n💻 **代码示例：**\n┌─────────────────────────────────┐\n\2\n└─────────────────────────────────┘\n\n', text, flags=re.DOTALL)
        
        # 处理内联代码
        text = re.sub(r'`([^`]+)`', r' `\1` ', text)
        
        # 处理粗体和斜体
        text = re.sub(r'\*\*([^*]+)\*\*', r'**\1**', text)
        text = re.sub(r'\*([^*]+)\*', r'*\1*', text)
        
        # 处理引用
        text = re.sub(r'^>\s*(.+)$', r'┃ \1', text, flags=re.MULTILINE)
        
        # 处理列表
        text = re.sub(r'^[-*+]\s+(.+)$', r'• \1', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\.\s+(.+)$', r'• \1', text, flags=re.MULTILINE)
        
        # 处理链接
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'[\1](\2)', text)
        
        # 处理分隔线
        text = re.sub(r'^---+$', '─' * 50, text, flags=re.MULTILINE)
        
        # 最终清理
        return self._postprocess_text_v2(text)
    
    def save_article_file(self, title, content, tags, url):
        """保存文章到文件"""
        # 创建文件名（使用URL的hash避免重复）
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)[:50]
        
        filename = f"forwarded-enhanced-{safe_title}-{url_hash}.md"
        
        # 确保目录存在
        today = datetime.now().strftime('%Y-%m-%d')
        target_dir = f"articles/{today}"
        os.makedirs(target_dir, exist_ok=True)
        
        file_path = os.path.join(target_dir, filename)
        
        # 增强内容格式（保存Markdown版本）
        enhanced_content = self._enhance_content_format(title, content, url, use_rich_text=False)
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_content)
        
        print(f"💾 文章已保存: {file_path}")
        return file_path
    
    async def forward_to_toutiao(self, title, content, tags, url, account_file):
        """转发文章到今日头条"""
        print("🚀 开始发布到今日头条...")
        
        try:
            # 增强内容格式并转换为富文本
            enhanced_content = self._enhance_content_format(title, content, url, use_rich_text=True)
            
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
            return False

async def forward_article_from_url(url, account_file="cookies/toutiao_uploader/account.json", save_file=True):
    """从URL转发文章到今日头条"""
    print("🔗 增强版文章链接转发工具 v2.1")
    print("=" * 60)
    
    # 检查登录状态
    print("🔐 检查登录状态...")
    if not await toutiao_setup(account_file):
        print("❌ 登录状态检查失败，请先登录")
        print("运行以下命令重新登录:")
        print("python examples/login_toutiao.py")
        return False
    
    print("✅ 登录状态正常")
    
    # 创建转发器
    forwarder = EnhancedArticleForwarder()
    
    # 获取文章内容
    title, content, tags = await forwarder.fetch_article(url)
    
    if not title or not content:
        print("❌ 无法获取文章内容")
        return False
    
    # 保存文章文件（可选）
    if save_file:
        file_path = forwarder.save_article_file(title, content, tags, url)
    
    # 确认发布
    print(f"\n⚠️ 即将转发文章到今日头条:")
    print(f"📰 标题: {title}")
    print(f"📊 内容长度: {len(content)} 字符")
    print(f"🏷️ 标签: {tags}")
    print(f"🔗 来源: {url}")
    print(f"🎨 排版: 已启用增强排版模式")
    print(f"🔄 格式: Markdown → 富文本格式")
    print(f"🔒 验证码: 如遇验证码将等待用户输入")
    
    try:
        confirm = input("\n确认转发吗？(y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ 用户取消转发")
            return False
    except EOFError:
        # 处理管道输入的情况
        print("\n📋 检测到非交互模式，自动确认转发")
        print("⚠️ 注意: 如遇验证码，请在浏览器中手动输入")
    
    # 转发到今日头条
    success = await forwarder.forward_to_toutiao(title, content, tags, url, account_file)
    
    if success:
        print("\n🎉 文章转发完成！")
        print("📱 请登录今日头条查看发布结果")
        print("✨ 排版已优化，阅读体验更佳")
        print("🔄 内容已转换为富文本格式，无HTML代码")
    else:
        print("\n❌ 文章转发失败")
    
    return success

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='增强版文章链接转发到今日头条工具 v3.0 (wechatSync风格)')
    parser.add_argument('url', help='要转发的文章链接')
    parser.add_argument('--account', default='cookies/toutiao_uploader/account.json', help='账号cookie文件路径')
    parser.add_argument('--no-save', action='store_true', help='不保存文章到本地文件')
    parser.add_argument('--preview', action='store_true', help='仅预览格式化效果，不发布到头条')
    
    args = parser.parse_args()
    
    # 检查URL格式
    if not args.url.startswith(('http://', 'https://')):
        print("❌ 请提供有效的URL链接")
        return
    
    # 如果是预览模式，不检查账号文件
    if not args.preview:
        # 检查账号文件
        if not os.path.exists(args.account):
            print(f"❌ 账号文件不存在: {args.account}")
            print("请先运行登录脚本: python examples/login_toutiao.py")
            return
    
    print(f"🔗 目标链接: {args.url}")
    if not args.preview:
        print(f"🔑 账号文件: {args.account}")
    print(f"💾 保存文件: {'否' if args.no_save else '是'}")
    print(f"👀 预览模式: {'是' if args.preview else '否'}")
    print(f"✨ 版本: WechatSync风格排版 v3.0 (增强代码块、标题美化)")
    
    # 运行转发或预览
    if args.preview:
        asyncio.run(preview_article_format(args.url, not args.no_save))
    else:
        asyncio.run(forward_article_from_url(args.url, args.account, not args.no_save))

async def preview_article_format(url, save_file=True):
    """预览文章格式化效果"""
    print("👁️ 文章格式化预览模式")
    print("=" * 60)
    
    # 创建转发器
    forwarder = EnhancedArticleForwarder()
    
    # 获取文章内容
    title, content, tags = await forwarder.fetch_article(url)
    
    if not title or not content:
        print("❌ 无法获取文章内容")
        return False
    
    # 保存文章文件（可选）
    if save_file:
        file_path = forwarder.save_article_file(title, content, tags, url)
        print(f"📁 预览文件已保存: {file_path}")
    
    # 生成格式化内容预览
    print(f"\n📝 文章格式化预览:")
    print(f"📰 标题: {title}")
    print(f"📊 原始内容长度: {len(content)} 字符")
    print(f"🏷️ 标签: {tags}")
    print("=" * 60)
    
    # 增强内容格式并显示
    enhanced_content = forwarder._enhance_content_format(title, content, url, use_rich_text=True)
    
    print("\n🎨 格式化后内容预览:")
    print("─" * 60)
    print(enhanced_content[:1000] + "..." if len(enhanced_content) > 1000 else enhanced_content)
    if len(enhanced_content) > 1000:
        print(f"\n... (内容太长，仅显示前1000字符，完整内容共{len(enhanced_content)}字符)")
    print("─" * 60)
    
    print("\n✨ 格式化特性说明:")
    print("  📖 标题: 使用emoji和分隔线美化")
    print("  💻 代码块: 带边框和语言标识")
    print("  🔹 段落: 适当间距和层级结构")
    print("  📝 列表: 使用美观的项目符号")
    print("  💡 引用: 带竖线和emoji装饰")
    print("  🔗 链接: 保留原始链接格式")
    
    print(f"\n🎯 预览完成！如需发布到头条，请移除 --preview 参数")
    return True

if __name__ == "__main__":
    main() 