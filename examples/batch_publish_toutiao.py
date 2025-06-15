#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
今日头条批量文章发布脚本
支持指定目录，批量发布该目录下所有的md文件
"""

import asyncio
import os
import sys
import glob
import time
from datetime import datetime
from playwright.async_api import async_playwright

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uploader.toutiao_uploader.main import TouTiaoArticle, toutiao_setup

def parse_markdown_file(file_path):
    """解析markdown文件，提取标题、内容和标签"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.strip().split('\n')
        
        # 提取标题（第一行如果是#开头，或者使用文件名）
        title = ""
        content_start_idx = 0
        
        if lines and lines[0].startswith('#'):
            title = lines[0].lstrip('#').strip()
            content_start_idx = 1
        else:
            # 使用文件名作为标题（去掉.md后缀）
            title = os.path.splitext(os.path.basename(file_path))[0]
            title = title.replace('-', ' ').replace('_', ' ').title()
        
        # 提取内容（去掉标题行）
        article_content = '\n'.join(lines[content_start_idx:]).strip()
        
        # 简单的标签提取（基于文件名和内容关键词）
        tags = extract_tags_from_content(title, article_content, file_path)
        
        return title, article_content, tags
        
    except Exception as e:
        print(f"❌ 解析文件失败 {file_path}: {e}")
        return None, None, None

def extract_tags_from_content(title, content, file_path):
    """从标题、内容和文件名中提取标签"""
    tags = []
    
    # 基于文件名的标签映射
    filename = os.path.basename(file_path).lower()
    
    tag_mapping = {
        'ai': ['人工智能', 'AI技术', '机器学习'],
        'medical': ['医疗健康', '医疗科技', '健康管理'],
        'blockchain': ['区块链', '数字货币', '去中心化'],
        'supply': ['供应链', '物流管理', '商业模式'],
        '5g': ['5G技术', '通信技术', '网络技术'],
        'technology': ['科技发展', '技术创新', '数字化'],
        'microservice': ['微服务', '架构设计', '软件开发'],
        'redis': ['Redis', '数据库', '缓存技术'],
        'thread': ['多线程', '并发编程', '性能优化'],
        'model': ['技术模型', '系统架构', '设计模式']
    }
    
    # 根据文件名匹配标签
    for keyword, related_tags in tag_mapping.items():
        if keyword in filename:
            tags.extend(related_tags[:2])  # 每个关键词最多取2个标签
    
    # 内容关键词标签
    content_lower = content.lower()
    content_keywords = {
        '人工智能': ['artificial intelligence', 'ai', '机器学习', 'machine learning'],
        '区块链': ['blockchain', '比特币', 'bitcoin', '加密货币'],
        '5G': ['5g', '第五代', '通信技术'],
        '医疗': ['medical', '健康', 'health', '医院', '诊断'],
        '技术': ['technology', '科技', '创新', 'innovation'],
        '开发': ['development', '编程', 'programming', '代码'],
        '数据': ['data', '数据库', 'database', '大数据']
    }
    
    for tag, keywords in content_keywords.items():
        if any(keyword in content_lower for keyword in keywords):
            if tag not in tags:
                tags.append(tag)
    
    # 确保至少有一些通用标签
    if not tags:
        tags = ['技术分享', '科技发展', '创新思维']
    
    # 限制标签数量（今日头条建议3-6个标签）
    return tags[:6]

def get_markdown_files(directory):
    """获取指定目录下的所有markdown文件"""
    if not os.path.exists(directory):
        print(f"❌ 目录不存在: {directory}")
        return []
    
    # 支持多种markdown文件扩展名
    patterns = [
        os.path.join(directory, "*.md"),
        os.path.join(directory, "*.markdown"),
        os.path.join(directory, "*.mdown")
    ]
    
    md_files = []
    for pattern in patterns:
        md_files.extend(glob.glob(pattern))
    
    # 排序确保发布顺序一致
    md_files.sort()
    
    return md_files

async def publish_single_article(file_path, account_file, delay_seconds=0):
    """发布单个文章"""
    print(f"\n{'='*60}")
    print(f"📄 正在处理文件: {os.path.basename(file_path)}")
    print(f"{'='*60}")
    
    # 解析markdown文件
    title, content, tags = parse_markdown_file(file_path)
    
    if not title or not content:
        print(f"❌ 文件解析失败，跳过: {file_path}")
        return False
    
    print(f"📝 标题: {title}")
    print(f"🏷️  标签: {tags}")
    print(f"📊 内容长度: {len(content)} 字符")
    print(f"⏰ 延迟: {delay_seconds} 秒")
    
    # 如果有延迟，先等待
    if delay_seconds > 0:
        print(f"⏳ 等待 {delay_seconds} 秒后开始发布...")
        await asyncio.sleep(delay_seconds)
    
    try:
        # 创建文章发布对象
        article = TouTiaoArticle(
            title=title,
            content=content,
            tags=tags,
            publish_date=0,  # 立即发布
            account_file=account_file,
            cover_path=None  # 自动生成封面
        )
        
        print("🎯 开始发布文章...")
        
        # 发布文章
        async with async_playwright() as playwright:
            await article.upload(playwright)
        
        print(f"✅ 文章发布完成: {title}")
        return True
        
    except Exception as e:
        print(f"❌ 文章发布失败: {e}")
        return False

async def batch_publish_articles(directory, account_file, delay_between_posts=60):
    """批量发布文章"""
    print("🚀 今日头条批量文章发布工具")
    print("=" * 60)
    
    # 检查登录状态
    print("🔐 检查登录状态...")
    if not await toutiao_setup(account_file):
        print("❌ 登录状态检查失败，请先登录")
        print("运行以下命令重新登录:")
        print("python examples/login_toutiao.py")
        return
    
    print("✅ 登录状态正常")
    
    # 获取所有markdown文件
    md_files = get_markdown_files(directory)
    
    if not md_files:
        print(f"❌ 在目录 {directory} 中未找到任何markdown文件")
        return
    
    print(f"\n📁 找到 {len(md_files)} 个markdown文件:")
    for i, file_path in enumerate(md_files, 1):
        print(f"  {i}. {os.path.basename(file_path)}")
    
    # 确认发布
    print(f"\n⚠️  即将批量发布 {len(md_files)} 篇文章")
    print(f"📅 发布间隔: {delay_between_posts} 秒")
    print(f"⏱️  预计总时间: {len(md_files) * delay_between_posts // 60} 分钟")
    
    confirm = input("\n确认开始批量发布吗？(y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("❌ 用户取消发布")
        return
    
    # 开始批量发布
    print(f"\n🎯 开始批量发布 {len(md_files)} 篇文章...")
    
    success_count = 0
    failed_count = 0
    
    for i, file_path in enumerate(md_files):
        print(f"\n📊 进度: {i+1}/{len(md_files)}")
        
        # 第一篇文章不延迟，后续文章有延迟
        delay = 0 if i == 0 else delay_between_posts
        
        success = await publish_single_article(file_path, account_file, delay)
        
        if success:
            success_count += 1
        else:
            failed_count += 1
        
        # 显示当前统计
        print(f"📈 当前统计: 成功 {success_count}, 失败 {failed_count}")
    
    # 最终统计
    print(f"\n{'='*60}")
    print("📊 批量发布完成统计:")
    print(f"✅ 成功发布: {success_count} 篇")
    print(f"❌ 发布失败: {failed_count} 篇")
    print(f"📁 总文件数: {len(md_files)} 篇")
    print(f"📈 成功率: {success_count/len(md_files)*100:.1f}%")
    print(f"{'='*60}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='今日头条批量文章发布工具')
    parser.add_argument('directory', help='包含markdown文件的目录路径')
    parser.add_argument('--delay', type=int, default=60, help='文章发布间隔时间（秒），默认60秒')
    parser.add_argument('--account', default='cookies/toutiao_uploader/account.json', help='账号cookie文件路径')
    
    args = parser.parse_args()
    
    # 检查目录
    if not os.path.exists(args.directory):
        print(f"❌ 目录不存在: {args.directory}")
        return
    
    # 检查账号文件
    if not os.path.exists(args.account):
        print(f"❌ 账号文件不存在: {args.account}")
        print("请先运行登录脚本: python examples/login_toutiao.py")
        return
    
    print(f"📁 目标目录: {os.path.abspath(args.directory)}")
    print(f"⏰ 发布间隔: {args.delay} 秒")
    print(f"🔑 账号文件: {args.account}")
    
    # 运行批量发布
    asyncio.run(batch_publish_articles(args.directory, args.account, args.delay))

if __name__ == "__main__":
    main() 