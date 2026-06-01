#!/usr/bin/env python3
"""
数据库初始化脚本
"""

import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()


def init_database():
    """初始化 SQLite 数据库"""
    
    db_path = os.getenv('DATABASE_PATH', './data/samples.db')
    
    # 确保 data 目录存在
    data_dir = os.path.dirname(db_path)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建样本表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS samples (
            sample_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            parent_message TEXT NOT NULL,
            advisor_reply TEXT NOT NULL,
            scene_tag TEXT,
            stage_tag TEXT,
            note TEXT,
            quality_score INTEGER DEFAULT 1,
            source_type TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            
            -- 索引优化字段
            source_trace TEXT,
            author_type TEXT
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON samples(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON samples(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_scene_tag ON samples(scene_tag)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stage_tag ON samples(stage_tag)')
    
    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            openid TEXT UNIQUE,
            nickname TEXT,
            phone TEXT,
            llm_provider TEXT,
            llm_api_key_encrypted TEXT,
            llm_api_base TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP
        )
    ''')
    
    # 创建消息暂存表（用于合并转发解析）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_temp (
            temp_id TEXT PRIMARY KEY,
            user_id TEXT,
            openid TEXT,
            sender TEXT,
            time TEXT,
            content TEXT,
            role_guess TEXT DEFAULT 'unknown',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建使用日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            log_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            sample_id TEXT,
            query TEXT,
            latency_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"✅ 数据库初始化完成: {db_path}")


if __name__ == '__main__':
    init_database()