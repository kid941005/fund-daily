#!/usr/bin/env python3
"""
Migration 0025: 创建默认管理员用户
用户名: admin
密码: admin123
"""

import hashlib
import os
import sys
import uuid

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_migration():
    """运行迁移"""
    try:
        # 导入数据库模块
        from db import get_db
        from src.auth import hash_password

        with get_db() as conn:
            from db.pool import get_cursor

            with get_cursor(conn) as cursor:
                # 检查是否已存在 admin 用户
                cursor.execute("SELECT * FROM users WHERE username = %s", ("admin",))
                existing_user = cursor.fetchone()

                if existing_user:
                    print("✅ 管理员用户 'admin' 已存在")
                    return True

                # 创建用户 ID
                user_id = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:16]

                # 哈希密码
                password_hash = hash_password("admin123")

                # 插入用户
                cursor.execute(
                    """
                    INSERT INTO users (user_id, username, password, created_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                """,
                    (user_id, "admin", password_hash),
                )

                conn.commit()
                print("✅ 迁移 0025 完成: 管理员用户 'admin' 创建成功")
                print(f"   用户名: admin")
                print(f"   密码: admin123")
                print(f"   用户ID: {user_id}")
                return True

    except Exception as e:
        print(f"❌ 迁移 0025 失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("运行迁移 0025: 创建默认管理员用户...")
    success = run_migration()
    sys.exit(0 if success else 1)
