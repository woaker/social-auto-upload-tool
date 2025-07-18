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
import openai
from typing import Optional, Dict, List
import json
import argparse
import traceback
import math
import random
import logging
import types

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uploader.toutiao_uploader.main_final import TouTiaoArticle, toutiao_setup

logger = logging.getLogger("toutiao_forward")
logger.setLevel(logging.INFO)
if not logger.handlers:
    from logging.handlers import RotatingFileHandler
    handler = RotatingFileHandler("/Users/yongjun.xiao/Downloads/workspace/python/social-auto-upload/logs/toutiao_forward_debug.log", maxBytes=5*1024*1024, backupCount=2)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

logger.info(f"当前工作目录: {os.getcwd()}")
logger.info(f"logs 目录是否存在: {os.path.exists('logs')}")

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
        self.markdown_converter = markdown.Markdown(extensions=['fenced_code', 'tables'])
    
    def _simple_markdown_to_text(self, text):
        """简化的Markdown到文本转换 - 优化版"""
        if not text:
            return ""
        
        # 处理没有空格的标题格式（例如 "##前言" 变成 "## 前言"）
        text = re.sub(r'^(#{1,6})([^#\s])', r'\1 \2', text, flags=re.MULTILINE)
        
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
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', text)
        
        # 处理分隔线
        text = re.sub(r'^---+$', '---', text, flags=re.MULTILINE)
        
        # 后处理
        return self._postprocess_text(text)
    
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
            return f"{text}"  # 不显示链接URL，保持文章整洁
        
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
            return text + "\n\n" if text else ""
        
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
            return text + "\n\n" if text else ""
        
        elif tag == 'table':
            return self._format_table(element)
        
        else:
            return text
    
    def _format_heading(self, text, level):
        """格式化标题 - 优化版"""
        if not text:
            return ""
        
        text = text.strip()
        prefix = "#" * level
        
        # 为标题添加表情符号，使其更加醒目
        if level <= 3 and len(text) < 30:  # 只为较短的主要标题添加表情符号
            for keyword, emoji in self.code_languages.items():
                if keyword.lower() in text.lower():
                    text = f"{emoji} {text}"
                    break
        
        # 确保标题前后有足够的空行
        return f"\n\n{prefix} {text}\n\n"
    
    def _format_code_block(self, code_text, language=''):
        """格式化代码块 - 优化版"""
        if not code_text:
            return ""
        
        code_text = code_text.strip()
        lang_text = f" ({language})" if language else ""
        
        return f"\n```{language.lower()}\n{code_text}\n```\n\n"
    
    def _format_list(self, element, list_type):
        """格式化列表 - 优化版"""
        items = []
        index = 1
        
        for li in element.find_all('li', recursive=False):
            text = self._element_to_text(li).strip()
            if text:
                if list_type == 'ol':
                    items.append(f"{index}. {text}")
                    index += 1
                else:
                    items.append(f"- {text}")
        
        return "\n" + "\n".join(items) + "\n\n" if items else ""
    
    def _format_quote(self, text):
        """格式化引用块 - 优化版"""
        if not text:
            return ""
        
        lines = text.strip().split('\n')
        quoted_lines = [f"> {line.strip()}" for line in lines if line.strip()]
        
        return "\n" + "\n".join(quoted_lines) + "\n\n"
    
    def _format_table(self, table_element):
        """格式化表格 - 优化版"""
        rows = []
        header_cells = []
        
        # 处理表头
        header_row = table_element.find('tr')
        if header_row:
            for th in header_row.find_all(['th', 'td']):
                text = th.get_text().strip()
                header_cells.append(text)
            
            if header_cells:
                rows.append("| " + " | ".join(header_cells) + " |")
                rows.append("| " + " | ".join(['---'] * len(header_cells)) + " |")
        
        # 处理数据行
        for tr in table_element.find_all('tr')[1:]:
            cells = []
            for td in tr.find_all('td'):
                text = td.get_text().strip()
                cells.append(text)
            if cells:
                rows.append("| " + " | ".join(cells) + " |")
        
        return "\n" + "\n".join(rows) + "\n\n" if rows else ""
    
    def _postprocess_text(self, text):
        """后处理文本 - 优化版"""
        if not text:
            return ""
        
        # 清理多余的空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 确保代码块前后有空行
        text = re.sub(r'([^\n])\n```', r'\1\n\n```', text)
        text = re.sub(r'```\n([^\n])', r'```\n\n\1', text)
        
        # 确保标题前后有空行
        text = re.sub(r'([^\n])\n(#{1,6} )', r'\1\n\n\2', text)
        text = re.sub(r'(#{1,6} .*)\n([^\n])', r'\1\n\n\2', text)
        
        # 确保引用块前后有空行
        text = re.sub(r'([^\n])\n>', r'\1\n\n>', text)
        text = re.sub(r'>\s*\n([^\n>])', r'>\n\n\1', text)
        
        # 确保列表项之间没有空行，但列表前后有空行
        text = re.sub(r'\n\n([-*+]|\d+\.)\s', r'\n\1 ', text)
        text = re.sub(r'([^\n])\n([-*+]|\d+\.)\s', r'\1\n\n\2 ', text)
        text = re.sub(r'([-*+]|\d+\.)\s.*\n([^\n-*+\d])', r'\1\n\n\2', text)
        
        return text.strip()
    
    def markdown_to_text(self, markdown_content):
        """将Markdown转换为优化的文本格式"""
        if not markdown_content:
            return ""
        
        try:
            # 将Markdown转换为HTML
            html_content = self.markdown_converter.convert(markdown_content)
            
            # 将HTML转换为优化的文本格式
            return self.html_to_text(html_content)
        except Exception as e:
            print(f"⚠️ Markdown转换失败，使用简化转换: {e}")
            return self._simple_markdown_to_text(markdown_content)

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
            },
            'code_languages': {
                'python': 'Python',
                'java': 'Java',
                'javascript': 'JavaScript',
                'js': 'JavaScript',
                'typescript': 'TypeScript',
                'ts': 'TypeScript',
                'html': 'HTML',
                'css': 'CSS',
                'php': 'PHP',
                'ruby': 'Ruby',
                'go': 'Go',
                'rust': 'Rust',
                'c': 'C',
                'cpp': 'C++',
                'csharp': 'C#',
                'swift': 'Swift',
                'kotlin': 'Kotlin',
                'sql': 'SQL',
                'bash': 'Bash',
                'shell': 'Shell',
                'json': 'JSON',
                'xml': 'XML',
                'yaml': 'YAML',
                'markdown': 'Markdown',
                'md': 'Markdown',
                'plaintext': '纯文本',
                'text': '纯文本'
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
                    return f"\n\n{content}\n\n"
            
            elif tag_name == 'p':
                return f"\n\n{content}\n\n"
            
            elif tag_name in ['strong', 'b']:
                return content  # 不添加特殊标记，依赖编辑器的富文本功能
            
            elif tag_name in ['em', 'i']:
                return content  # 不添加特殊标记，依赖编辑器的富文本功能
            
            elif tag_name == 'code':
                if content:
                    return content  # 不添加特殊标记，依赖编辑器的富文本功能
            
            elif tag_name == 'pre':
                if content:
                    return f"\n\n{content}\n\n"
            
            elif tag_name in ['ul', 'ol']:
                if children_text:
                    return f"\n\n" + "\n".join(children_text) + "\n\n"
            
            elif tag_name == 'li':
                if content:
                    return f"• {content}"
            
            elif tag_name == 'blockquote':
                if content:
                    return f"\n\n{content}\n\n"
            
            elif tag_name == 'a':
                href = element.get('href', '')
                if content and href:
                    return content  # 不显示链接URL，保持文章整洁
                else:
                    return content
            
            elif tag_name == 'table':
                return f"\n\n{content}\n\n"
            
            elif tag_name in ['th', 'td']:
                return f"{content} |"
            
            elif tag_name == 'tr':
                return f"|{content}\n"
            
            elif tag_name == 'hr':
                return "\n\n---\n\n"
            
            elif tag_name == 'br':
                return "\n"
            
            else:
                return content
        
        # 处理整个HTML文档
        result = process_html_element(soup)
        
        # 清理多余的空行和空格
        if result:
            result = re.sub(r'\n{3,}', '\n\n', result)  # 将3个以上的换行替换为2个
            result = re.sub(r'[ \t]+', ' ', result)  # 将多个空格替换为1个
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
        lang_display = self.content_enhancers.get('code_languages', {}).get(language, language)
        
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
            # 检查是否为知乎链接
            if 'zhihu.com' in url:
                return await self._fetch_zhihu_article(url)
            
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
            
            print(f"✅ 文章获取成功: 标题={title}, 标签={tags}, 内容长度={len(content) if content else 0}")
            print(f"📝 标题: {title}")
            print(f"📊 内容长度: {len(content)} 字符")
            print(f"🏷️ 标签: {tags}")
            
            return title, content, tags
            
        except Exception as e:
            print(f"❌ 获取文章失败: {e}")
            return None, None, None
            
    async def _fetch_zhihu_article(self, url):
        """使用Playwright模拟浏览器获取知乎文章内容"""
        print("🔍 检测到知乎链接，使用浏览器模拟访问...")
        
        try:
            # 从URL中提取文章ID
            article_id = url.split('/')[-1]
            print(f"📝 知乎文章ID: {article_id}")
            
            # 使用Playwright模拟浏览器访问
            async with async_playwright() as playwright:
                # 使用有界面模式以便观察
                browser = await playwright.chromium.launch(headless=False)
                
                # 创建上下文并添加反爬虫措施
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                    device_scale_factor=1,
                )
                
                # 添加stealth.js脚本来绕过反爬虫检测
                stealth_js_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "utils/stealth.min.js")
                if os.path.exists(stealth_js_path):
                    with open(stealth_js_path, "r") as f:
                        stealth_js = f.read()
                    await context.add_init_script(stealth_js)
                
                # 创建页面
                page = await context.new_page()
                
                # 设置超时
                page.set_default_timeout(60000)  # 60秒超时
                
                # 访问知乎文章页面
                print(f"🌐 正在访问知乎文章: {url}")
                await page.goto(url)
                
                # 检查是否有验证码或登录弹窗
                print("⏳ 等待页面加载，检查是否有验证码...")
                await page.wait_for_load_state("networkidle")
                
                # 等待一段时间，让页面完全加载
                await page.wait_for_timeout(5000)
                
                # 检查是否需要处理验证码
                if await page.query_selector('.Captcha') or await page.query_selector('.SignFlowInput'):
                    print("⚠️ 检测到验证码或登录弹窗，需要人工处理")
                    print("请在打开的浏览器中完成验证，然后脚本将继续...")
                    
                    # 等待用户处理验证码
                    await page.wait_for_selector('.Post-Title, .QuestionHeader-title, .ArticleHeader-title', timeout=120000)
                
                # 再次等待页面加载
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(2000)
                
                # 截图用于调试
                screenshot_path = "zhihu_debug.png"
                await page.screenshot(path=screenshot_path)
                print(f"📸 页面截图已保存: {screenshot_path}")
                
                # 尝试获取标题
                title_selectors = [
                    '.Post-Title', 
                    '.QuestionHeader-title', 
                    '.ArticleHeader-title',
                    'h1'
                ]
                
                title = "未知标题"
                for selector in title_selectors:
                    title_element = await page.query_selector(selector)
                    if title_element:
                        title = await title_element.text_content()
                        title = title.strip()
                        if title:
                            break
                
                # 尝试获取内容
                content_selectors = [
                    '.Post-RichTextContainer', 
                    '.QuestionRichText',
                    '.RichText',
                    '.Post-RichText',
                    'article'
                ]
                
                content_html = ""
                for selector in content_selectors:
                    try:
                        content_html = await page.evaluate(f"""() => {{
                            const element = document.querySelector('{selector}');
                            return element ? element.innerHTML : '';
                        }}""")
                        
                        if content_html:
                            break
                    except Exception as e:
                        print(f"尝试选择器 {selector} 失败: {e}")
                
                if not content_html:
                    # 如果所有选择器都失败，尝试获取整个页面内容
                    content_html = await page.content()
                
                # 使用BeautifulSoup解析HTML
                soup = BeautifulSoup(content_html, 'html.parser')
                
                # 移除不需要的元素
                for unwanted in soup.select('.CommentBox, .Reward, .FollowButton, .VoteButton, .ContentItem-actions'):
                    if unwanted:
                        unwanted.decompose()
                
                # 转换为Markdown
                content = self._html_to_markdown_enhanced(soup)
                
                # 提取标签
                tags = []
                tag_selectors = ['.Tag-content .Tag-label', '.TopicLink', '.Tag']
                
                for selector in tag_selectors:
                    tag_elements = await page.query_selector_all(selector)
                    for tag_element in tag_elements:
                        tag_text = await tag_element.text_content()
                        if tag_text and tag_text.strip():
                            tags.append(tag_text.strip())
                    
                    if tags:
                        break
                
                # 如果没有找到标签，使用默认标签
                if not tags:
                    tags = ['知乎', '文章转发']
                
                # 关闭浏览器
                await browser.close()
                
                # 检查内容是否有效
                if len(content) < 100:
                    print(f"⚠️ 获取的内容过短，可能未成功抓取: {len(content)} 字符")
                    return None, None, None
                
                print(f"✅ 知乎文章获取成功:")
                print(f"📝 标题: {title}")
                print(f"📊 内容长度: {len(content)} 字符")
                print(f"🏷️ 标签: {tags}")
                
                return title, content, tags
                
        except Exception as e:
            print(f"❌ 知乎文章获取失败: {e}")
            traceback.print_exc()  # 打印完整错误堆栈，便于调试
            return None, None, None
    
    def _enhance_content_format(self, title, content, url, use_rich_text=True):
        """增强内容格式化 - V3版本"""
        if not content:
            return ""
        
        # 移除原文链接和转发时间信息，今日头条不需要这些
        # source_info = f"""
        # > **原文链接**: {url}
        # > **转发时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        # > **内容优化**: 已优化排版格式，提升阅读体验

        # ---

        # """
        
        # 处理正文内容
        content = content.strip()
        
        # 1. 不再添加标题到内容中，因为今日头条已经有单独的标题字段
        # if title and not content.startswith('# '):
        #     content = f"# {title}\n\n{content}"
        
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
        
        # 4. 不再添加文章来源信息
        # content = source_info + content
        
        # 5. 最终的格式清理
        content = re.sub(r'\n{3,}', '\n\n', content)  # 删除多余的空行
        content = re.sub(r'[ \t]+\n', '\n', content)  # 删除行尾空格
        content = content.strip()
        
        if use_rich_text:
            print("🎨 正在将Markdown转换为富文本格式...")
            
            # 使用 markdown 库将 Markdown 转换为 HTML
            import markdown
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
    
    def _optimize_content_spacing(self, content):
        """优化内容间距 - V2版本"""
        if not content:
            return ""
        
        # 1. 标准化换行符
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # 2. 处理标题间距
        content = re.sub(r'\n(#{1,6}\s+[^\n]+)\n', r'\n\n\1\n\n', content)
        
        # 3. 处理代码块间距
        content = re.sub(r'\n```([^\n]*)\n', r'\n\n```\1\n', content)
        content = re.sub(r'\n```\n', r'\n```\n\n', content)
        
        # 4. 处理列表格式
        def format_list(match):
            list_content = match.group(0)
            lines = list_content.split('\n')
            # 保持列表项之间的紧凑性，但在列表前后添加空行
            return f"\n\n{list_content}\n\n"
        
        content = re.sub(r'((?:^[-*+]\s+[^\n]+\n?)+)', format_list, content, flags=re.MULTILINE)
        content = re.sub(r'((?:^\d+\.\s+[^\n]+\n?)+)', format_list, content, flags=re.MULTILINE)
        
        # 5. 处理引用块格式
        def format_quote(match):
            quote_content = match.group(0)
            lines = quote_content.split('\n')
            formatted_lines = []
            for line in lines:
                if line.strip():
                    if not line.startswith('>'):
                        line = f"> {line}"
                    formatted_lines.append(line)
            return '\n\n' + '\n'.join(formatted_lines) + '\n\n'
        
        content = re.sub(r'((?:^>\s+[^\n]+\n?)+)', format_quote, content, flags=re.MULTILINE)
        
        # 6. 优化段落间距
        paragraphs = content.split('\n\n')
        formatted_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if para:
                # 处理段落内的换行
                lines = para.split('\n')
                # 如果是普通段落且行数大于1，进行特殊处理
                if len(lines) > 1 and not any(line.startswith(('#', '>', '-', '*', '+', '```', '|')) for line in lines):
                    # 将多行合并为一个段落
                    para = ' '.join(line.strip() for line in lines)
                formatted_paragraphs.append(para)
        
        content = '\n\n'.join(formatted_paragraphs)
        
        # 7. 最终清理
        content = re.sub(r'\n{3,}', '\n\n', content)  # 删除多余的空行
        content = re.sub(r'[ \t]+\n', '\n', content)  # 删除行尾空格
        
        return content.strip()
    
    def _smart_format_content(self, content):
        """智能格式化内容 - V2版本"""
        if not content:
            return ""
        
        # 1. 优化代码块
        content = self._fix_code_blocks(content)
        
        # 2. 优化段落
        content = self._optimize_paragraphs(content)
        
        # 3. 优化列表
        content = self._optimize_lists(content)
        
        # 4. 添加上下文表情符号
        content = self._add_contextual_emojis(content)
        
        return content
    
    def _fix_code_blocks(self, content):
        """修复代码块格式"""
        if not content:
            return ""
        
        # 确保代码块有语言标识
        def replace_code_block(match):
            lang = match.group(1) or ''
            code = match.group(2)
            
            # 检测代码语言
            if not lang:
                # 简单的语言检测逻辑
                if 'function' in code or 'var' in code or 'const' in code:
                    lang = 'javascript'
                elif 'def' in code or 'import' in code:
                    lang = 'python'
                elif '<' in code and '>' in code:
                    lang = 'html'
                else:
                    lang = 'plaintext'
            
            return f"```{lang}\n{code.strip()}\n```"
        
        content = re.sub(r'```(\w*)\n(.*?)\n```', replace_code_block, content, flags=re.DOTALL)
        
        return content
    
    def _optimize_paragraphs(self, content):
        """优化段落格式"""
        if not content:
            return ""
        
        # 1. 处理段落间距
        paragraphs = content.split('\n\n')
        formatted_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 特殊块保持原格式
            if any(para.startswith(prefix) for prefix in ('#', '```', '>', '-', '*', '+', '|')):
                formatted_paragraphs.append(para)
                continue
            
            # 普通段落处理
            # 合并多行
            lines = para.split('\n')
            if len(lines) > 1:
                # 将多行合并为一个段落，除非行结束有标点
                merged_lines = []
                current_line = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if current_line and not any(line.endswith(punct) for punct in '。！？；：，.!?;:,'): 
                        current_line.append(line)
                    else:
                        if current_line:
                            merged_lines.append(' '.join(current_line))
                        current_line = [line]
                
                if current_line:
                    merged_lines.append(' '.join(current_line))
                
                para = '\n'.join(merged_lines)
            
            formatted_paragraphs.append(para)
        
        return '\n\n'.join(formatted_paragraphs)
    
    def _optimize_lists(self, content):
        """优化列表格式"""
        if not content:
            return ""
        
        # 处理无序列表
        def format_unordered_list(match):
            items = match.group(0).split('\n')
            return '\n'.join(f"- {item.lstrip('- ').strip()}" for item in items if item.strip())
        
        content = re.sub(r'(?:^|\n)(?:[-*+]\s+[^\n]+\n?)+', format_unordered_list, content)
        
        # 处理有序列表
        def format_ordered_list(match):
            items = match.group(0).split('\n')
            formatted_items = []
            for i, item in enumerate(items, 1):
                if item.strip():
                    item_content = re.sub(r'^\d+\.\s*', '', item).strip()
                    formatted_items.append(f"{i}. {item_content}")
            return '\n'.join(formatted_items)
        
        content = re.sub(r'(?:^|\n)(?:\d+\.\s+[^\n]+\n?)+', format_ordered_list, content)
        
        return content
    
    def _add_contextual_emojis(self, content):
        """添加上下文表情符号"""
        if not content:
            return ""
        
        # 标题表情映射 - 扩展版
        title_emoji_map = {
            # 基础章节
            '介绍': '📝', '简介': '📝', '前言': '📝', '概述': '📝',
            '背景': '🔍', '目标': '🎯', '动机': '💡', '原理': '🔬',
            
            # 技术相关
            '安装': '⚙️', '配置': '⚙️', '设置': '⚙️', '环境': '⚙️',
            '使用': '🔨', '用法': '🔨', '实践': '🔨', '操作': '🔨',
            '示例': '💡', '例子': '💡', '案例': '💡', '演示': '💡',
            '代码': '💻', '实现': '💻', '编码': '💻', '程序': '💻',
            '架构': '🏗️', '设计': '📐', '模式': '🧩', '结构': '🔧',
            '测试': '🧪', '调试': '🔍', '优化': '⚡', '性能': '⚡',
            
            # 提示和警告
            '注意': '⚠️', '警告': '⚠️', '提示': '💡', '建议': '💡',
            '问题': '❓', '解决': '✅', '错误': '❌', '异常': '⚠️',
            '常见问题': '❓', 'FAQ': '❓', '疑难解答': '🔧',
            
            # 总结类
            '总结': '📌', '结论': '📌', '小结': '📌', '回顾': '📌',
            '展望': '🔭', '未来': '🔮', '计划': '📅', '路线图': '🗺️',
            
            # 功能和特性
            '特性': '✨', '功能': '✨', '特点': '✨', '亮点': '✨',
            '优点': '👍', '缺点': '👎', '优势': '👍', '劣势': '👎',
            
            # 流程和步骤
            '步骤': '📋', '流程': '📋', '过程': '📋', '阶段': '📋',
            '方法': '🔧', '技巧': '💡', '策略': '🎯', '实战': '⚔️',
            
            # 面试相关
            '面试': '🎯', '题目': '📝', '解答': '✅', '分析': '🔍',
            
            # 框架和语言
            'Vue': '💚', 'React': '⚛️', 'Angular': '🅰️', 'Node': '📦',
            'Python': '🐍', 'Java': '☕', 'JavaScript': '📜', 'TypeScript': '📘',
            'Go': '🐹', 'Rust': '🦀', 'C++': '⚙️', 'PHP': '🐘',
            
            # 数据相关
            '数据': '📊', '统计': '📈', '分析': '📉', '可视化': '📊',
            '算法': '🧮', '模型': '🧠', '学习': '📚', '训练': '🏋️'
        }
        
        # 为标题添加表情
        def add_title_emoji(match):
            title = match.group(2)
            level = len(match.group(1))
            
            # 查找标题中是否包含关键词
            emoji = None
            for keyword, e in title_emoji_map.items():
                if keyword in title:
                    emoji = e
                    break
            
            if emoji:
                return f"{'#' * level} {emoji} {title}"
            
            # 如果没有匹配的关键词，根据标题级别添加默认表情
            if level == 1:
                return f"# 📑 {title}"  # 主标题
            elif level == 2:
                return f"## 📌 {title}"  # 二级标题
            elif level == 3:
                return f"### 📎 {title}"  # 三级标题
            
            return match.group(0)
        
        # 处理标准格式的标题
        content = re.sub(r'^(#{1,6})\s+(.+)$', add_title_emoji, content, flags=re.MULTILINE)
        
        # 处理可能没有空格的标题格式
        content = re.sub(r'^(#{1,6})([^#\s].+)$', r'\1 \2', content, flags=re.MULTILINE)
        # 再次应用表情符号
        content = re.sub(r'^(#{1,6})\s+(.+)$', add_title_emoji, content, flags=re.MULTILINE)
        
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
        """改进版HTML到格式化文本转换 - 适配今日头条编辑器"""
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
            
            content = ' '.join(children_texts) if children_texts else element.get_text().strip()
            
            # 根据标签类型格式化
            if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(tag_name[1])
                if content:
                    prefix = '#' * level + ' '
                    return f"\n\n{prefix}{content}\n\n"
                    
            elif tag_name == 'p':
                if content:
                    return f"\n\n{content}\n\n"
                    
            elif tag_name in ['strong', 'b']:
                return content  # 依赖编辑器的加粗功能
                
            elif tag_name in ['em', 'i']:
                return content  # 依赖编辑器的斜体功能
                
            elif tag_name == 'code':
                if content:
                    return content  # 依赖编辑器的代码格式功能
            
            elif tag_name == 'pre':
                if content:
                    # 检测代码语言
                    code_elem = element.find('code')
                    language = ""
                    if code_elem and code_elem.get('class'):
                        classes = ' '.join(code_elem.get('class', []))
                        lang_match = re.search(r'language-(\w+)', classes)
                        if lang_match:
                            language = lang_match.group(1)
                    
                    return f"\n\n{content}\n\n"  # 依赖编辑器的代码块功能
                        
            elif tag_name in ['ul', 'ol']:
                if children_texts:
                    list_content = '\n'.join(children_texts)
                    return f"\n\n{list_content}\n\n"
                    
            elif tag_name == 'li':
                parent = element.parent
                if parent and parent.name == 'ol':
                    # 有序列表
                    index = 1
                    for sibling in element.previous_siblings:
                        if sibling.name == 'li':
                            index += 1
                    return f"{index}. {content}"
                else:
                    # 无序列表
                    return f"• {content}"
            
            elif tag_name == 'blockquote':
                if content:
                    return f"\n\n{content}\n\n"  # 依赖编辑器的引用功能
                    
            elif tag_name == 'a':
                href = element.get('href', '')
                if content and href:
                    return content  # 依赖编辑器的链接功能
                else:
                    return content
            
            elif tag_name == 'img':
                alt = element.get('alt', '图片')
                src = element.get('src', '')
                if src:
                    return f"\n\n[图片]\n\n"  # 图片需要手动上传
            
            elif tag_name in ['br']:
                return "\n"
            
            elif tag_name in ['hr']:
                return "\n\n---\n\n"
            
            elif tag_name in ['div', 'section', 'article']:
                if children_texts:
                    return ' '.join(children_texts)
                else:
                    return content
            
            else:
                return content
        
        # 处理整个文档
        result = process_element(soup)
        
        # 后处理：清理格式
        if result:
            # 清理多余的空行
            result = re.sub(r'\n{3,}', '\n\n', result)
            # 清理多余的空格
            result = re.sub(r'[ \t]+', ' ', result)
            # 确保段落间有空行
            result = re.sub(r'([^\n])\n([^\n])', r'\1\n\n\2', result)
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

class AIContentEnhancer:
    """AI内容增强器 - 使用OpenAI优化文章排版和内容"""
    
    def __init__(self, api_key: Optional[str] = None):
        """初始化AI内容增强器"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        print(f"API Key: {self.api_key}")
        if self.api_key:
            openai.api_key = self.api_key
        self.model = "gpt-3.5-turbo-16k"
    
    def enhance_content(self, title: str, content: str, tags: List[str]) -> Dict[str, str]:
        """使用AI增强内容质量"""
        if not self.api_key:
            print("⚠️ 未配置OpenAI API Key，跳过AI增强")
            return {"title": title, "content": content}
            
        try:
            print("🤖 正在使用AI优化内容...")
            
            # 构建提示词
            prompt = f"""作为一个专业的技术文章编辑，请帮我优化以下文章的排版和内容，要求：
            1. 保持原文的核心内容和技术准确性
            2. 优化标题使其更吸引人，但不要过分夸张
            3. 改进文章结构，使其更有逻辑性
            4. 优化段落分布，使文章更易读
            5. 适当添加小标题和分隔符
            6. 在关键点添加合适的emoji
            7. 确保代码块格式正确
            8. 适当添加要点符号
            9. 保持专业性和可读性的平衡
            10. 输出格式必须是Markdown
            11. 不要在内容开头添加文章标题，标题将单独处理

            原标题: {title}
            标签: {', '.join(tags)}
            
            原文内容:
            {content}
            """
            
            # 调用OpenAI API
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的技术文章编辑，精通技术写作和排版优化。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            # 解析响应
            enhanced_content = response.choices[0].message.content.strip()
            
            # 提取优化后的标题（如果AI生成了新标题）
            new_title = title
            if enhanced_content.startswith('# '):
                # 提取AI生成的标题
                first_line = enhanced_content.split('\n')[0]
                potential_title = first_line.lstrip('# ').strip()
                if potential_title:  # 如果有内容，使用它作为新标题
                    new_title = potential_title
                # 无论如何，从内容中移除标题行
                enhanced_content = '\n'.join(enhanced_content.split('\n')[1:]).strip()
            
            # 再次检查是否有标题格式的行（有时AI会添加多个标题）
            if enhanced_content.startswith('# '):
                enhanced_content = re.sub(r'^#\s+.*?\n', '', enhanced_content, count=1, flags=re.MULTILINE)
            
            print("✨ AI内容优化完成")
            return {
                "title": new_title,
                "content": enhanced_content
            }
            
        except Exception as e:
            print(f"⚠️ AI增强过程出现错误: {str(e)}")
            return {"title": title, "content": content}
    
    def generate_seo_tags(self, title: str, content: str) -> List[str]:
        """使用AI生成SEO优化的标签"""
        if not self.api_key:
            return []
            
        try:
            print("🏷️ 正在使用AI生成优化标签...")
            
            # 构建提示词
            prompt = f"""作为SEO专家，请为以下技术文章生成3-5个最相关的标签，要求：
            1. 标签要准确反映文章核心主题
            2. 包含技术领域和具体技术点
            3. 考虑搜索热度和相关性
            4. 不要使用过于宽泛的标签
            5. 输出格式：每行一个标签，不要包含#号

            文章标题: {title}
            
            文章内容:
            {content[:2000]}  # 只使用前2000个字符
            """
            
            # 调用OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个SEO专家，精通技术文章标签优化。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            # 解析响应
            tags = [tag.strip() for tag in response.choices[0].message.content.strip().split('\n')]
            print(f"✨ AI标签生成完成: {tags}")
            return tags
            
        except Exception as e:
            print(f"⚠️ AI标签生成出现错误: {str(e)}")
            return []

async def forward_article_from_url(url, account_file="cookiesFile/toutiao_cookie.json", save_file=True):
    """从URL转发文章到今日头条"""
    try:
        logger.info(f"🔐 检查登录状态... account_file={account_file}")
        if not await toutiao_setup(account_file):
            logger.error("❌ 登录状态失效，请重新登录")
            logger.error("提示: 运行 python examples/login_toutiao.py 重新登录")
            return None
        logger.info("✅ 登录状态正常")
        
        forwarder = EnhancedArticleForwarder()
        logger.info("准备获取文章内容")
        try:
            title, content, tags = await forwarder.fetch_article(url)
        except Exception as e:
            logger.error(f"fetch_article 异常: {e}", exc_info=True)
        logger.info("fetch_article 执行完毕")
        logger.info(f"获取结果: title={title}, content={content}, tags={tags}")
        
        if not title or not content:
            logger.error("❌ 文章获取失败")
            return None
        
        if save_file:
            file_path = forwarder.save_article_file(title, content, tags, url)
            if file_path:
                logger.info(f"💾 文章已保存: {file_path}")
        
        return {
            'title': title,
            'content': content,
            'tags': tags
        }
        
    except Exception as e:
        logger.error(f"❌ 获取文章失败: {str(e)}", exc_info=True)
        return None

async def publish_article_to_toutiao(title, content, tags, url, account_file="cookiesFile/toutiao_cookie.json"):
    try:
        logger.info(f"⚠️ 即将转发文章到今日头条: 标题={title}, 标签={tags}, 来源={url}")
        logger.info(f"🎨 排版: 已启用增强排版模式, 🔄 格式: Markdown → 富文本格式")
        logger.info(f"🔒 验证码: 如遇验证码将等待用户输入")
        forwarder = EnhancedArticleForwarder()
        logger.info("🚀 开始发布到今日头条... 准备调用forward_to_toutiao")
        logger.info("调用forward_to_toutiao前")
        success = await forwarder.forward_to_toutiao(title, content, tags, url, account_file)
        logger.info(f"调用forward_to_toutiao后，结果: {success}")
        if success:
            logger.info("🎉 文章转发完成！请登录今日头条查看发布结果")
        else:
            logger.error("❌ 文章转发失败")
        return success
    except Exception as e:
        logger.error(f"❌ 发布文章到头条异常: {str(e)}", exc_info=True)
        return False

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='从URL转发文章到今日头条')
    parser.add_argument('url', help='要转发的文章URL')
    parser.add_argument('--no-save', action='store_false', dest='save_file',
                      help='不保存文章到本地')
    parser.add_argument('--preview', action='store_true',
                      help='预览模式，只显示文章内容不发布')
    parser.add_argument('--no-ai', action='store_false', dest='use_ai',
                      help='不使用AI增强功能')
    args = parser.parse_args()

    # 显示参数信息
    print(f"🔗 目标链接: {args.url}")
    print(f"🔑 账号文件: cookiesFile/toutiao_cookie.json")
    print(f"💾 保存文件: {'是' if args.save_file else '否'}")
    print(f"👀 预览模式: {'是' if args.preview else '否'}")
    print(f"🤖 AI增强: {'是' if args.use_ai else '否'}")
    print(f"✨ 版本: WechatSync风格排版 v3.0 (增强代码块、标题美化)")
    print("🔗 增强版文章链接转发工具 v2.1")
    print("=" * 60)

    try:
        # 获取文章内容
        article = await forward_article_from_url(
            args.url,
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
            tags=article_tags,
            url=args.url
        )

    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 