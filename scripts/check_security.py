#!/usr/bin/env python3
"""
安全配置检查脚本
检查项目中的安全配置问题
"""

import os
import re
import secrets
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_hardcoded_passwords():
    """检查硬编码密码"""
    issues = []

    # 检查的文件和模式
    patterns = [
        (r'password\s*[:=]\s*["\']\d+["\']', "硬编码数字密码"),
        (r'password\s*[:=]\s*["\'][^"\']{1,10}["\']', "过短的硬编码密码"),
        (r'secret\s*[:=]\s*["\']change-in-production["\']', "未更改的生产环境密钥"),
        (r"941005", "硬编码数据库密码"),
    ]

    files_to_check = [
        "docker-compose.yml",
        "src/config.py",
        "src/jwt_auth.py",
        "src/api_gateway/core.py",
    ]

    for file_path in files_to_check:
        full_path = project_root / file_path
        if not full_path.exists():
            continue

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                for pattern, description in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append({"file": file_path, "line": i, "issue": description, "content": line.strip()})

    return issues


def check_environment_variables():
    """检查必要的环境变量是否设置"""
    issues = []

    # 必要的环境变量（生产环境）
    required_vars = [
        "FUND_DAILY_JWT_SECRET",
        "FUND_DAILY_SECRET_KEY",
        "FUND_DAILY_DB_PASSWORD",
    ]

    env = os.getenv("FUND_DAILY_ENV", "development")

    if env == "production":
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                issues.append(f"生产环境必须设置环境变量: {var}")
            elif "change-in-production" in value.lower():
                issues.append(f"环境变量 {var} 包含默认值，必须更改为强密钥")
            elif var.endswith("_SECRET") and len(value) < 32:
                issues.append(f"环境变量 {var} 长度不足32字符: {len(value)}")

    return issues


def check_file_permissions():
    """检查文件权限"""
    issues = []

    sensitive_files = [
        ".env",
        "docker-compose.override.yml",
    ]

    for file_name in sensitive_files:
        file_path = project_root / file_name
        if file_path.exists():
            mode = file_path.stat().st_mode
            # 检查是否对组或其他用户可写
            if mode & 0o022:
                issues.append(f"文件 {file_name} 权限过宽: {oct(mode)}")

    return issues


def check_security_headers():
    """检查安全头配置"""
    issues = []

    # 检查安全中间件是否存在
    security_file = project_root / "web" / "security.py"
    if not security_file.exists():
        issues.append("缺少安全HTTP头中间件: web/security.py")

    # 检查Flask应用是否使用了安全中间件
    app_file = project_root / "web" / "app.py"
    if app_file.exists():
        with open(app_file, "r", encoding="utf-8") as f:
            content = f.read()
            if "security_headers" not in content:
                issues.append("Flask应用未配置安全HTTP头中间件")

    return issues


def generate_secure_secrets():
    """生成安全的随机密钥"""
    secrets_dict = {
        "JWT_SECRET": secrets.token_urlsafe(48),
        "FLASK_SECRET": secrets.token_hex(32),
        "DB_PASSWORD": secrets.token_urlsafe(24),
    }

    return secrets_dict


def main():
    """主函数"""
    print("🔒 Fund Daily 安全配置检查")
    print("=" * 50)

    # 检查环境
    env = os.getenv("FUND_DAILY_ENV", "development")
    print(f"环境: {env}")

    all_issues = []

    # 执行检查
    print("\n1. 检查硬编码密码...")
    password_issues = check_hardcoded_passwords()
    if password_issues:
        all_issues.extend(password_issues)
        for issue in password_issues:
            print(f"   ❌ {issue['file']}:{issue['line']} - {issue['issue']}")
            print(f"      内容: {issue['content']}")
    else:
        print("   ✅ 未发现硬编码密码")

    print("\n2. 检查环境变量...")
    env_issues = check_environment_variables()
    if env_issues:
        all_issues.extend(env_issues)
        for issue in env_issues:
            print(f"   ❌ {issue}")
    else:
        print("   ✅ 环境变量检查通过")

    print("\n3. 检查文件权限...")
    perm_issues = check_file_permissions()
    if perm_issues:
        all_issues.extend(perm_issues)
        for issue in perm_issues:
            print(f"   ❌ {issue}")
    else:
        print("   ✅ 文件权限检查通过")

    print("\n4. 检查安全头...")
    header_issues = check_security_headers()
    if header_issues:
        all_issues.extend(header_issues)
        for issue in header_issues:
            print(f"   ❌ {issue}")
    else:
        print("   ✅ 安全头检查通过")

    # 总结
    print("\n" + "=" * 50)
    if all_issues:
        print(f"❌ 发现 {len(all_issues)} 个安全问题")

        # 生成安全密钥建议
        if env == "production":
            print("\n🔑 建议生成的安全密钥:")
            secrets_dict = generate_secure_secrets()
            for key, value in secrets_dict.items():
                print(f"   {key}: {value}")

            print("\n📋 修复建议:")
            print("   1. 创建 .env 文件并设置强密码")
            print("   2. 更新 docker-compose.yml 使用环境变量文件")
            print("   3. 设置文件权限: chmod 600 .env")
            print("   4. 重启服务使配置生效")

        return 1
    else:
        print("✅ 所有安全检查通过！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
