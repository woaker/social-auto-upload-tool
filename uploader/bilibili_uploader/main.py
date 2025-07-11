import json
import pathlib
import random
from biliup.plugins.bili_webup import BiliBili, Data

from utils.log import bilibili_logger


def extract_keys_from_json(data):
    """Extract specified keys from the provided JSON data."""
    keys_to_extract = ["SESSDATA", "bili_jct", "DedeUserID__ckMd5", "DedeUserID", "access_token"]
    extracted_data = {}

    # 处理不同格式的cookie文件
    if 'cookie_info' in data and 'cookies' in data['cookie_info']:
        # 标准biliup格式
        for cookie in data['cookie_info']['cookies']:
            if cookie['name'] in keys_to_extract:
                extracted_data[cookie['name']] = cookie['value']
    elif 'cookies' in data:
        # 简化格式
        for cookie in data['cookies']:
            if cookie['name'] in keys_to_extract:
                extracted_data[cookie['name']] = cookie['value']
    elif 'cookie_dict' in data:
        # 字典格式
        for key, value in data['cookie_dict'].items():
            if key in keys_to_extract:
                extracted_data[key] = value

    # 提取access_token
    if "token_info" in data and "access_token" in data['token_info']:
        extracted_data['access_token'] = data['token_info']['access_token']
    else:
        # 设置空的access_token，某些情况下B站可以仅用cookie工作
        extracted_data['access_token'] = None
        
    # 检查是否有必要的cookie
    if 'SESSDATA' not in extracted_data or 'bili_jct' not in extracted_data:
        bilibili_logger.warning("警告: Cookie中缺少必要的SESSDATA或bili_jct字段")
        
    return extracted_data


def read_cookie_json_file(filepath: pathlib.Path):
    with open(filepath, 'r', encoding='utf-8') as file:
        content = json.load(file)
        return content


def random_emoji():
    emoji_list = ["🍏", "🍎", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🍈", "🍒", "🍑", "🍍", "🥭", "🥥", "🥝",
                  "🍅", "🍆", "🥑", "🥦", "🥒", "🥬", "🌶", "🌽", "🥕", "🥔", "🍠", "🥐", "🍞", "🥖", "🥨", "🥯", "🧀", "🥚", "🍳", "🥞",
                  "🥓", "🥩", "🍗", "🍖", "🌭", "🍔", "🍟", "🍕", "🥪", "🥙", "🌮", "🌯", "🥗", "🥘", "🥫", "🍝", "🍜", "🍲", "🍛", "🍣",
                  "🍱", "🥟", "🍤", "🍙", "🍚", "🍘", "🍥", "🥮", "🥠", "🍢", "🍡", "🍧", "🍨", "🍦", "🥧", "🍰", "🎂", "🍮", "🍭", "🍬",
                  "🍫", "🍿", "🧂", "🍩", "🍪", "🌰", "🥜", "🍯", "🥛", "🍼", "☕️", "🍵", "🥤", "🍶", "🍻", "🥂", "🍷", "🥃", "🍸", "🍹",
                  "🍾", "🥄", "🍴", "🍽", "🥣", "🥡", "🥢"]
    return random.choice(emoji_list)


class BilibiliUploader(object):
    def __init__(self, cookie_data, file: pathlib.Path, title, desc, tid, tags, dtime):
        self.upload_thread_num = 3
        self.copyright = 1
        self.lines = 'AUTO'
        self.cookie_data = cookie_data
        self.file = file
        self.title = title
        self.desc = desc
        self.tid = tid
        self.tags = tags
        self.dtime = dtime
        self._init_data()

    def _init_data(self):
        self.data = Data()
        self.data.copyright = self.copyright
        self.data.title = self.title
        self.data.desc = self.desc
        self.data.tid = self.tid
        self.data.set_tag(self.tags)
        self.data.dtime = self.dtime

    def upload(self):
        with BiliBili(self.data) as bili:
            # 先检查是否有必要的cookie信息
            if 'SESSDATA' not in self.cookie_data or 'bili_jct' not in self.cookie_data:
                bilibili_logger.error(f"[-] {self.file.name}上传失败: 缺少必要的cookie信息(SESSDATA或bili_jct)")
                return False
                
            # 使用cookies登录
            bili.login_by_cookies(self.cookie_data)
            
            # 设置access_token (如果有)
            access_token = self.cookie_data.get('access_token')
            if access_token:
                bili.access_token = access_token
                
            # 上传视频
            try:
                video_part = bili.upload_file(str(self.file), lines=self.lines,
                                            tasks=self.upload_thread_num)  # 上传视频，默认线路AUTO自动选择，线程数量3。
                video_part['title'] = self.title
                self.data.append(video_part)
                ret = bili.submit()  # 提交视频
                if ret.get('code') == 0:
                    bilibili_logger.success(f'[+] {self.file.name}上传 成功')
                    return True
                else:
                    bilibili_logger.error(f'[-] {self.file.name}上传 失败, error messge: {ret.get("message")}')
                    return False
            except Exception as e:
                bilibili_logger.error(f'[-] {self.file.name}上传 异常: {str(e)}')
                return False
