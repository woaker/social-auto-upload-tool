from pathlib import Path
from typing import List, Callable, Any, Awaitable
import asyncio
from datetime import datetime
import os
from utils.log import douyin_logger

from conf import BASE_DIR

SOCIAL_MEDIA_DOUYIN = "douyin"
SOCIAL_MEDIA_TENCENT = "tencent"
SOCIAL_MEDIA_TIKTOK = "tiktok"
SOCIAL_MEDIA_BILIBILI = "bilibili"
SOCIAL_MEDIA_KUAISHOU = "kuaishou"


def get_supported_social_media() -> List[str]:
    return [SOCIAL_MEDIA_DOUYIN, SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU]


async def wait_with_timeout(
    check_func: Callable[[], Awaitable[bool]],
    timeout_seconds: int,
    interval_seconds: float = 1.0,
    timeout_message: str = "操作超时",
    success_message: str = "操作成功",
    progress_message: str = "操作进行中...",
    logger=douyin_logger
) -> bool:
    """
    通用的超时等待函数
    
    Args:
        check_func: 检查条件的异步函数，返回True表示条件满足
        timeout_seconds: 超时时间（秒）
        interval_seconds: 检查间隔（秒）
        timeout_message: 超时时显示的消息
        success_message: 成功时显示的消息
        progress_message: 等待过程中显示的消息
        logger: 日志记录器
        
    Returns:
        bool: 是否在超时前满足条件
    """
    start_time = datetime.now()
    
    while (datetime.now() - start_time).total_seconds() < timeout_seconds:
        try:
            if await check_func():
                if success_message:
                    logger.success(success_message)
                return True
        except Exception as e:
            logger.warning(f"检查条件时出错: {e}")
        
        elapsed_seconds = int((datetime.now() - start_time).total_seconds())
        if progress_message:
            logger.info(f"{progress_message} ({elapsed_seconds}/{timeout_seconds}秒)")
        
        await asyncio.sleep(interval_seconds)
    
    if timeout_message:
        logger.error(f"❌ {timeout_message} ({timeout_seconds}秒)")
    
    return False


async def set_init_script(context):
    # 读取stealth.min.js
    stealth_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "utils", "stealth.min.js")
    with open(stealth_path, "r") as f:
        stealth_js = f.read()

    # 添加初始化脚本
    await context.add_init_script(stealth_js)
    return context
