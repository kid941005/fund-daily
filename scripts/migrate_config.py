#!/usr/bin/env python3
"""
配置统一迁移脚本
将分散的环境变量读取统一到配置管理器
"""

import os
import re
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置映射：环境变量名 -> 配置管理器路径
CONFIG_MAPPING = {
    # Redis 配置
    "REDIS_HOST": "config.redis.host",
    "REDIS_PORT": "config.redis.port", 
    "REDIS_DB": "config.redis.db",
    "REDIS_PASSWORD": "config.redis.password",
    "REDIS_TTL": "config.redis.ttl",
    
    # 缓存配置
    "FUND_DAILY_CACHE_DURATION": "config.cache.duration",
    "FUND_DAILY_REQUEST_INTERVAL": "config.cache.request_interval",
    
    # SSL 配置
    "FUND_DAILY_SSL_VERIFY": "config.security.ssl_verify",
    
    # 数据库配置（已在 config.py 中）
    # "FUND_DAILY_DB_TYPE": "config.database.type",  # 已移除，仅支持PostgreSQL
    "FUND_DAILY_DB_HOST": "config.database.host",
    "FUND_DAILY_DB_PORT": "config.database.port",
    "FUND_DAILY_DB_NAME": "config.database.name",
    "FUND_DAILY_DB_USER": "config.database.user",
    "FUND_DAILY_DB_PASSWORD": "config.database.password",
    
    # JWT 配置
    "FUND_DAILY_JWT_SECRET": "config.security.jwt.secret",
    "FUND_DAILY_JWT_EXPIRE_MINUTES": "config.security.jwt.access_token_expire_minutes",
    "FUND_DAILY_JWT_REFRESH_DAYS": "config.security.jwt.refresh_token_expire_days",
    
    # 应用配置
    "FUND_DAILY_ENV": "config.app.env",
    "FUND_DAILY_VERSION": "config.app.version",
    "FUND_DAILY_DEFAULT_FUNDS": "config.app.default_funds",
    
    # 服务器配置
    "PORT": "config.server.port",
    "FLASK_DEBUG": "config.server.debug",
    "FLASK_HOST": "config.server.host",
}

def find_direct_env_usage(file_path):
    """查找文件中直接使用环境变量的地方"""
    patterns = [
        r'os\.environ\.get\(["\']([^"\']+)["\']',
        r'os\.getenv\(["\']([^"\']+)["\']',
        r'os\.environ\[["\']([^"\']+)["\']\]',
    ]
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    matches = []
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            env_var = match.group(1)
            if env_var in CONFIG_MAPPING:
                matches.append({
                    'env_var': env_var,
                    'line': content[:match.start()].count('\n') + 1,
                    'match': match.group(0),
                    'config_path': CONFIG_MAPPING[env_var]
                })
    
    return matches

def generate_migration_patch(file_path, matches):
    """生成迁移补丁"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    patches = []
    for match in matches:
        line_num = match['line'] - 1  # 转换为0-based索引
        old_line = lines[line_num]
        
        # 构建新的导入语句（如果需要）
        if 'from src.config import get_config' not in ''.join(lines[:line_num]):
            patches.append({
                'type': 'import',
                'line': 0,
                'content': 'from src.config import get_config\n'
            })
        
        # 构建配置管理器调用
        config_call = f'get_config().{match["config_path"]}'
        
        # 替换环境变量调用
        # 处理 os.environ.get("VAR", default) 的情况
        if 'os.environ.get' in old_line or 'os.getenv' in old_line:
            # 提取默认值
            default_match = re.search(r'["\']([^"\']+)["\']\s*,\s*([^)]+)', old_line[match['match'].find('('):])
            if default_match:
                # 有默认值的情况，配置管理器应该已经处理了默认值
                new_line = old_line.replace(match['match'], config_call)
            else:
                # 没有默认值的情况
                new_line = old_line.replace(match['match'], config_call)
        else:
            # 其他情况
            new_line = old_line.replace(f'os.environ["{match["env_var"]}"]', config_call)
        
        patches.append({
            'type': 'replace',
            'line': line_num,
            'old': old_line,
            'new': new_line.rstrip()
        })
    
    return patches

def apply_patches(file_path, patches):
    """应用补丁到文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 按行号排序（从后往前，避免索引变化）
    patches.sort(key=lambda x: x['line'], reverse=True)
    
    for patch in patches:
        if patch['type'] == 'import':
            # 在文件开头添加导入
            lines.insert(patch['line'], patch['content'])
        elif patch['type'] == 'replace':
            # 替换行
            lines[patch['line']] = patch['new'] + '\n'
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def main():
    """主函数"""
    print("🔧 配置统一迁移工具")
    print("=" * 50)
    
    # 查找需要迁移的文件
    python_files = list(project_root.rglob("*.py"))
    
    all_matches = []
    for file_path in python_files:
        # 跳过测试文件和缓存目录
        if 'test_' in str(file_path) or '__pycache__' in str(file_path):
            continue
        
        matches = find_direct_env_usage(file_path)
        if matches:
            all_matches.append({
                'file': file_path,
                'matches': matches
            })
    
    if not all_matches:
        print("✅ 未发现需要迁移的配置")
        return 0
    
    print(f"📁 发现 {len(all_matches)} 个文件需要迁移:")
    
    for file_info in all_matches:
        print(f"\n{file_info['file'].relative_to(project_root)}:")
        for match in file_info['matches']:
            print(f"  - 第{match['line']}行: {match['env_var']} → {match['config_path']}")
    
    # 询问是否应用迁移
    response = input("\n是否应用这些迁移？(y/N): ").strip().lower()
    if response != 'y':
        print("❌ 取消迁移")
        return 0
    
    # 应用迁移
    print("\n🔨 应用迁移...")
    for file_info in all_matches:
        patches = generate_migration_patch(file_info['file'], file_info['matches'])
        if patches:
            apply_patches(file_info['file'], patches)
            print(f"  ✅ {file_info['file'].relative_to(project_root)}")
    
    print("\n🎉 迁移完成！")
    print("\n📋 后续步骤:")
    print("  1. 运行测试确保配置迁移正确")
    print("  2. 更新相关文档")
    print("  3. 验证应用功能正常")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())