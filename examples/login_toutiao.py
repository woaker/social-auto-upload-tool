#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
今日头条账号登录脚本
用于获取和保存登录状态
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uploader.toutiao_uploader.main import toutiao_cookie_gen, cookie_auth

async def main():
    """主函数"""
    print("🔑 今日头条账号登录")
    print("=" * 40)
    
    # 账号文件路径 - 使用正确的路径
    account_file = "cookies/toutiao_uploader/account.json"
    
    # 确保目录存在
    os.makedirs(os.path.dirname(account_file), exist_ok=True)
    
    print(f"Cookie将保存到: {os.path.abspath(account_file)}")
    print()
    
    # 检查是否已有有效登录
    if os.path.exists(account_file):
        print("🔍 检查现有登录状态...")
        if await cookie_auth(account_file):
            print("✅ 当前登录状态有效！")
            print("如需重新登录，请删除cookie文件后重新运行此脚本")
            return
        else:
            print("❌ 当前登录状态已失效，需要重新登录")
    else:
        print("📝 首次登录，需要获取登录状态")
    
    print()
    print("请按照以下步骤操作:")
    print("1. 浏览器将自动打开今日头条登录页面")
    print("2. 请使用手机扫码或账号密码登录")
    print("3. 登录成功后，在调试器中点击 '继续' 按钮")
    print("4. Cookie将自动保存")
    print()
    
    input("按回车键开始...")
    
    # 执行登录
    success = await toutiao_cookie_gen(account_file)
    
    if success:
        print()
        print("✅ 登录成功！Cookie已保存")
        print("🔍 验证Cookie...")
        
        if await cookie_auth(account_file):
            print("✅ Cookie验证成功！")
            print()
            print("现在可以使用以下命令测试发布功能:")
            print("python examples/upload_article_to_toutiao_final.py")
        else:
            print("❌ Cookie验证失败，请重试")
    else:
        print("❌ 登录失败，请重试")

if __name__ == "__main__":
    asyncio.run(main()) 