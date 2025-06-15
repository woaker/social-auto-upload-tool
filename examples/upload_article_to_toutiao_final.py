#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
今日头条文章发布示例 - 最终版本
展示如何使用TouTiaoArticle类发布文章到今日头条
"""

import asyncio
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uploader.toutiao_uploader.main import TouTiaoArticle, toutiao_setup

async def main():
    """主函数"""
    print("🚀 今日头条文章发布示例 - 最终版本")
    print("=" * 50)
    
    # 账号文件路径 - 使用正确的路径
    account_file = "cookies/toutiao_uploader/account.json"
    
    # 检查登录状态
    if not await toutiao_setup(account_file):
        print("❌ 登录状态检查失败，请先登录")
        print("运行以下命令重新登录:")
        print("python examples/login_toutiao.py")
        return
    
    # 文章信息
    title = "人工智能技术的未来发展趋势与应用前景"
    
    content = """
人工智能技术正在快速发展，为我们的生活带来了许多便利和创新。从智能手机到自动驾驶汽车，AI技术无处不在，正在改变着我们的工作和生活方式。

## 人工智能的主要应用领域

### 1. 医疗健康
AI在医疗诊断、药物研发、个性化治疗等方面展现出巨大潜力。通过深度学习算法，AI可以帮助医生更准确地诊断疾病，提高治疗效果。

### 2. 教育领域
智能教育系统可以根据学生的学习特点提供个性化的学习方案，提高学习效率。AI助教可以24小时为学生答疑解惑。

### 3. 智能制造
工业4.0时代，AI技术在智能制造中发挥重要作用，提高生产效率，降低成本，实现精准制造。

### 4. 金融服务
AI在风险控制、智能投顾、反欺诈等金融服务领域应用广泛，为用户提供更安全、便捷的金融服务。

## 未来发展趋势

随着技术的不断进步，人工智能将在更多领域发挥作用：

- **多模态AI**: 结合视觉、听觉、语言等多种感知能力
- **边缘计算**: 将AI能力部署到边缘设备，实现实时响应
- **可解释AI**: 让AI决策过程更加透明和可理解
- **AI伦理**: 确保AI技术的安全、公平和负责任使用

## 结语

人工智能技术的发展为人类社会带来了前所未有的机遇。我们应该积极拥抱这一技术革命，同时也要关注其带来的挑战，确保AI技术能够更好地服务于人类的发展和进步。

让我们一起期待AI技术为人类带来更美好的未来！
    """.strip()
    
    # 文章标签
    tags = ["人工智能", "科技发展", "未来趋势", "技术创新", "数字化转型", "智能制造"]
    
    # 发布时间 (0表示立即发布)
    publish_date = 0
    
    # 封面图片路径 (可选，如果不指定会自动生成)
    cover_path = None
    
    print(f"📝 标题: {title}")
    print(f"🏷️  标签: {tags}")
    print(f"📊 内容长度: {len(content)} 字符")
    print(f"🕐 发布时间: {'立即发布' if publish_date == 0 else publish_date}")
    print(f"🖼️  封面: {'自动生成' if not cover_path else cover_path}")
    print()
    
    # 创建文章发布对象
    article = TouTiaoArticle(
        title=title,
        content=content,
        tags=tags,
        publish_date=publish_date,
        account_file=account_file,
        cover_path=cover_path
    )
    
    print("🎯 开始发布文章...")
    print("=" * 50)
    
    # 发布文章
    async with async_playwright() as playwright:
        await article.upload(playwright)
    
    print()
    print("=" * 50)
    print("📋 发布完成！请检查以下内容:")
    print("1. 查看浏览器中的发布状态")
    print("2. 登录今日头条创作者中心确认文章是否发布成功")
    print("3. 检查生成的截图文件了解详细情况")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main()) 