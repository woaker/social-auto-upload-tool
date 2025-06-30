import asyncio
import sys
from pathlib import Path

# 添加父目录到模块搜索路径
sys.path.append(str(Path(__file__).parent.parent))

from conf import BASE_DIR
from uploader.tk_uploader.main_chrome import tiktok_setup

if __name__ == '__main__':
    account_file = Path(BASE_DIR / "cookiesFile" / "tiktok_account.json")
    account_file.parent.mkdir(exist_ok=True)
    cookie_setup = asyncio.run(tiktok_setup(str(account_file), handle=True))
