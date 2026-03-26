#!/usr/bin/env python3
"""
创建默认管理员用户脚本
用户名: admin
密码: admin123
"""

import sys
import os
import hashlib
import secrets

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import hash_password

def create_admin_user():
    """创建默认管理员用户"""
    try:
        # 导入数据库模块
        from db import get_db, create_user, get_user_by_username
        
        # 检查是否已存在 admin 用户
        with get_db() as conn:
            from db.pool import get_cursor
            with get_cursor(conn) as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", ("admin",))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    print("✅ 管理员用户 'admin' 已存在")
                    return True
                
                # 创建用户 ID
                import uuid
                user_id = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:16]
                
                # 哈希密码
                password_hash = hash_password("admin123")
                
                # 插入用户
                cursor.execute("""
                    INSERT INTO users (user_id, username, password, created_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                """, (user_id, "admin", password_hash))
                
                conn.commit()
                print("✅ 管理员用户 'admin' 创建成功")
                print(f"   用户名: admin")
                print(f"   密码: admin123")
                print(f"   用户ID: {user_id}")
                return True
                
    except Exception as e:
        print(f"❌ 创建管理员用户失败: {e}")
        print("请确保:")
        print("1. PostgreSQL 服务正在运行")
        print("2. 数据库已初始化 (运行过 init_db)")
        print("3. 环境变量 FUND_DAILY_DB_PASSWORD 已设置")
        return False

if __name__ == "__main__":
    print("正在创建默认管理员用户...")
    success = create_admin_user()
    sys.exit(0 if success else 1)