import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到系统路径
current_dir = Path(__file__).parent.parent.resolve()
sys.path.append(str(current_dir))

from conf import BASE_DIR
from uploader.ks_uploader.main import ks_setup

if __name__ == '__main__':
    account_file = Path(BASE_DIR / "cookiesFile" / "ks_cookie.json")
    account_file.parent.mkdir(exist_ok=True)
    cookie_setup = asyncio.run(ks_setup(str(account_file), handle=True))
