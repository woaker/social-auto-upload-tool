import asyncio
from pathlib import Path
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conf import BASE_DIR
from uploader.xiaohongshu_uploader.main import xiaohongshu_setup

if __name__ == '__main__':
    account_file = Path(BASE_DIR / "cookiesFile" / "xhs_cookie.json")
    account_file.parent.mkdir(exist_ok=True)
    cookie_setup = asyncio.run(xiaohongshu_setup(str(account_file), handle=True))
