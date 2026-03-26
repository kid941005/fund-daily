#!/usr/bin/env python3
"""
测试管理员用户登录
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import verify_password

def test_admin_login():
    """测试管理员用户登录"""
    try:
        from db import get_db
        
        with get_db() as conn:
            from db.pool import get_cursor
            with get_cursor(conn) as cursor:
                # 获取 admin 用户
                cursor.execute("SELECT * FROM users WHERE username = %s", ("admin",))
                user = cursor.fetchone()
                
                if not user:
                    print("❌ 管理员用户 'admin' 不存在")
                    return False
                
                print(f"✅ 找到管理员用户: {user['username']} (ID: {user['user_id']})")
                
                # 验证密码
                password_correct = verify_password("admin123", user["password"])
                
                if password_correct:
                    print("✅ 密码验证成功: admin123")
                    return True
                else:
                    print("❌ 密码验证失败")
                    return False
                    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("测试管理员用户登录...")
    success = test_admin_login()
    sys.exit(0 if success else 1)