import asyncio
import sys
from pathlib import Path
import uuid

# 添加父目录到模块搜索路径
sys.path.append(str(Path(__file__).parent.parent))

from conf import BASE_DIR
from uploader.baijiahao_uploader.main import baijiahao_setup

if __name__ == '__main__':
    # 生成随机的文件名
    account_filename = f"{uuid.uuid4()}.json"
    account_file = Path(BASE_DIR / "cookiesFile" / account_filename)
    
    # 确保目录存在
    account_file.parent.mkdir(exist_ok=True)
    
    print(f"正在为百家号生成cookie文件: {account_filename}")
    cookie_setup = asyncio.run(baijiahao_setup(str(account_file), handle=True))
    
    if cookie_setup:
        print(f"✅ 百家号cookie文件生成成功: {account_filename}")
        print(f"文件路径: {account_file}")
        print("现在可以使用百家号平台进行上传了")
    else:
        print("❌ 百家号cookie文件生成失败")
