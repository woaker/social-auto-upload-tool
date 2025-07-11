import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conf import BASE_DIR
from uploader.douyin_uploader.main import douyin_setup

if __name__ == '__main__':
    account_file = Path(BASE_DIR / "cookiesFile" / "douyin_cookie.json")
    account_file.parent.mkdir(exist_ok=True)
    cookie_setup = asyncio.run(douyin_setup(str(account_file), handle=True))
