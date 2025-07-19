import sqlite3
import json
import os

# 数据库文件路径（如果不存在会自动创建）
db_file = './database.db'

# 如果数据库已存在，则删除旧的表（可选）
# if os.path.exists(db_file):
#     os.remove(db_file)

# 连接到SQLite数据库（如果文件不存在则会自动创建）
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

cursor.execute('''
DROP TABLE IF EXISTS tb_unquie
''')

# 创建幂等性记录表
cursor.execute('''
CREATE TABLE IF NOT EXISTS tb_unquie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    type TEXT NOT NULL,
    task_id TEXT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(url, type)
)
''')

# 提交更改
conn.commit()
print("✅ 幂等性表创建成功")
# 关闭连接
conn.close()