import asyncio
import os
import sys
from pathlib import Path

# 获取项目根目录
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 添加项目根目录到Python路径
sys.path.insert(0, str(BASE_DIR))

# 导入抖音上传器
from uploader.douyin_uploader.main import douyin_setup, douyin_logger

async def main():
    try:
        # 设置cookie文件路径
        account_file = BASE_DIR / "cookies" / "douyin_uploader" / "account.json"
        account_file.parent.mkdir(parents=True, exist_ok=True)
        
        douyin_logger.info(f"Cookie文件路径: {account_file}")
        
        # 尝试设置抖音环境
        cookie_setup = await douyin_setup(str(account_file), handle=True)
        
        if cookie_setup:
            douyin_logger.success("✅ Cookie设置成功")
        else:
            douyin_logger.error("❌ Cookie设置失败")
            
    except Exception as e:
        douyin_logger.error(f"❌ 程序出错: {str(e)}")

if __name__ == '__main__':
    asyncio.run(main())
