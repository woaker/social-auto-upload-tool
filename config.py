from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.absolute()

# Chrome浏览器路径
import platform
import os

if platform.system() == 'Darwin':  # macOS
    LOCAL_CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
elif platform.system() == 'Windows':  # Windows
    LOCAL_CHROME_PATH = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    if not os.path.exists(LOCAL_CHROME_PATH):
        LOCAL_CHROME_PATH = r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
else:  # Linux
    LOCAL_CHROME_PATH = '/usr/bin/google-chrome'

# 如果找不到Chrome，使用系统默认
if not os.path.exists(LOCAL_CHROME_PATH):
    LOCAL_CHROME_PATH = None

XHS_SERVER = "http://127.0.0.1:11901"
