#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库操作工具类
用于处理URL幂等性检查
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from utils.log import logger


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_file: str = './database.db'):
        self.db_file = db_file
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """确保表存在"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 创建幂等性表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tb_unique (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    type TEXT NOT NULL,
                    task_id TEXT,
                    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(url, type)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ 数据库表检查完成")
            
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            raise
    
    def is_url_processed(self, url: str, type: str) -> bool:
        """
        检查URL是否已经处理过
        
        Args:
            url: 要检查的URL
            type: 处理类型 (youtube/juejin)
            
        Returns:
            bool: 是否已处理过
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id FROM tb_unique WHERE url = ? AND type = ?",
                (url, type)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                logger.info(f"🔍 URL已处理过: {url} (type: {type})")
                return True
            else:
                logger.info(f"🆕 URL未处理过: {url} (type: {type})")
                return False
                
        except Exception as e:
            logger.error(f"❌ 检查URL状态失败: {e}")
            return False
    
    def mark_url_processed(self, url: str, type: str, task_id: str = None) -> bool:
        """
        标记URL为已处理
        
        Args:
            url: 要标记的URL
            type: 处理类型 (youtube/juejin)
            task_id: 任务ID
            
        Returns:
            bool: 是否成功标记
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 使用INSERT OR REPLACE来处理唯一性约束
            cursor.execute('''
                INSERT OR REPLACE INTO tb_unique (url, type, task_id, update_time)
                VALUES (?, ?, ?, ?)
            ''', (url, type, task_id, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ URL已标记为已处理: {url} (type: {type}, task_id: {task_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 标记URL失败: {e}")
            return False
    
    def get_processed_urls(self, type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取已处理的URL列表
        
        Args:
            type: 可选的类型过滤
            
        Returns:
            List[Dict]: URL记录列表
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            if type:
                cursor.execute(
                    "SELECT * FROM tb_unique WHERE type = ? ORDER BY create_time DESC",
                    (type,)
                )
            else:
                cursor.execute("SELECT * FROM tb_unique ORDER BY create_time DESC")
            
            results = cursor.fetchall()
            conn.close()
            
            # 转换为字典列表
            records = []
            for row in results:
                records.append({
                    "id": row[0],
                    "url": row[1],
                    "type": row[2],
                    "task_id": row[3],
                    "create_time": row[4],
                    "update_time": row[5]
                })
            
            return records
            
        except Exception as e:
            logger.error(f"❌ 获取已处理URL列表失败: {e}")
            return []
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        获取处理统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 总记录数
            cursor.execute("SELECT COUNT(*) FROM tb_unique")
            total_count = cursor.fetchone()[0]
            
            # 按类型统计
            cursor.execute("SELECT type, COUNT(*) FROM tb_unique GROUP BY type")
            type_stats = dict(cursor.fetchall())
            
            # 今日新增
            cursor.execute('''
                SELECT COUNT(*) FROM tb_unique 
                WHERE DATE(create_time) = DATE('now')
            ''')
            today_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total_count": total_count,
                "type_stats": type_stats,
                "today_count": today_count
            }
            
        except Exception as e:
            logger.error(f"❌ 获取统计信息失败: {e}")
            return {}


# 全局数据库管理器实例
db_manager = DatabaseManager() 