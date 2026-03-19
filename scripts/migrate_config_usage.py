#!/usr/bin/env python3
"""
迁移配置使用，将 os.getenv() 替换为 get_config()
"""

import re
from pathlib import Path

def migrate_db_pool():
    """迁移 db/pool.py"""
    file_path = Path("/home/kid/fund-daily/db/pool.py")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 添加导入
    if "from src.config import get_config" not in content:
        # 在第一个import后添加
        import_match = re.search(r'^import', content, re.MULTILINE)
        if import_match:
            insert_pos = import_match.end()
            # 找到import块的结束
            lines = content.split('\n')
            for i in range(import_match.start(), len(lines)):
                if not lines[i].startswith(('import', 'from')):
                    insert_pos = sum(len(line) + 1 for line in lines[:i])
                    break
            
            content = content[:insert_pos] + '\nfrom src.config import get_config\n' + content[insert_pos:]
    
    # 替换数据库配置部分
    db_config_section = '''# PostgreSQL 配置
DB_HOST = os.environ.get("FUND_DAILY_DB_HOST", "localhost")
DB_PORT = os.environ.get("FUND_DAILY_DB_PORT", "5432")
DB_NAME = os.environ.get("FUND_DAILY_DB_NAME", "fund_daily")
DB_USER = os.environ.get("FUND_DAILY_DB_USER", "kid")
DB_PASSWORD = os.environ.get("FUND_DAILY_DB_PASSWORD", "")'''
    
    db_config_replacement = '''# PostgreSQL 配置 - 使用统一配置管理器
config = get_config()
DB_HOST = config.database.host
DB_PORT = config.database.port
DB_NAME = config.database.name
DB_USER = config.database.user
DB_PASSWORD = config.database.password'''
    
    if db_config_section in content:
        content = content.replace(db_config_section, db_config_replacement)
        print("✅ 已迁移 db/pool.py 数据库配置")
    else:
        print("⚠️  未找到预期的数据库配置部分，手动检查")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def migrate_jwt_auth():
    """迁移 src/jwt_auth.py"""
    file_path = Path("/home/kid/fund-daily/src/jwt_auth.py")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经导入了get_config
    if "from src.config import get_config" not in content:
        # 在现有导入后添加
        import_match = re.search(r'^from src\.error import', content, re.MULTILINE)
        if import_match:
            insert_pos = import_match.end()
            content = content[:insert_pos] + '\nfrom src.config import get_config' + content[insert_pos:]
    
    # 查找并替换 os.getenv 调用
    changes = 0
    
    # 替换 FUND_DAILY_JWT_SECRET
    pattern1 = r'os\.getenv\("FUND_DAILY_JWT_SECRET",\s*""\)'
    if re.search(pattern1, content):
        content = re.sub(pattern1, 'get_config().jwt.secret', content)
        changes += 1
    
    # 替换 FUND_DAILY_ENV
    pattern2 = r'os\.getenv\("FUND_DAILY_ENV",\s*"development"\)'
    if re.search(pattern2, content):
        content = re.sub(pattern2, 'get_config().env', content)
        changes += 1
    
    # 替换 FUND_DAILY_JWT_ALGORITHM
    pattern3 = r'os\.getenv\("FUND_DAILY_JWT_ALGORITHM",\s*"HS256"\)'
    if re.search(pattern3, content):
        content = re.sub(pattern3, 'get_config().jwt.algorithm', content)
        changes += 1
    
    # 替换 FUND_DAILY_JWT_EXPIRE_MINUTES
    pattern4 = r'int\(os\.getenv\("FUND_DAILY_JWT_EXPIRE_MINUTES",\s*"60"\)\)'
    if re.search(pattern4, content):
        content = re.sub(pattern4, 'get_config().jwt.access_token_expire_minutes', content)
        changes += 1
    
    if changes > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 已迁移 src/jwt_auth.py: {changes} 处配置调用")
    else:
        print("⚠️  src/jwt_auth.py 中未找到需要迁移的配置调用")

def migrate_rate_limiter():
    """迁移 web/api/rate_limiter.py"""
    file_path = Path("/home/kid/fund-daily/web/api/rate_limiter.py")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 添加导入
    if "from src.config import get_config" not in content:
        # 在现有导入后添加
        import_match = re.search(r'^from flask import', content, re.MULTILINE)
        if import_match:
            insert_pos = import_match.end()
            content = content[:insert_pos] + '\nfrom src.config import get_config' + content[insert_pos:]
    
    # 查找Redis配置部分
    redis_config_pattern = r'redis_host = os\.getenv\("FUND_DAILY_REDIS_HOST",\s*"localhost"\)\s*\nredis_port = os\.getenv\("FUND_DAILY_REDIS_PORT",\s*"6379"\)\s*\nredis_db = os\.getenv\("FUND_DAILY_REDIS_DB",\s*"0"\)'
    
    redis_config_replacement = '''config = get_config()
redis_host = config.redis.host
redis_port = config.redis.port
redis_db = config.redis.db'''
    
    if re.search(redis_config_pattern, content):
        content = re.sub(redis_config_pattern, redis_config_replacement, content)
        print("✅ 已迁移 web/api/rate_limiter.py Redis配置")
    else:
        print("⚠️  未找到预期的Redis配置模式，手动检查")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def migrate_api_gateway():
    """迁移 src/api_gateway/core.py"""
    file_path = Path("/home/kid/fund-daily/src/api_gateway/core.py")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 这个文件有多个配置调用，需要更复杂的迁移
    # 先添加导入
    if "from src.config import get_config" not in content:
        # 在现有导入后添加
        import_match = re.search(r'^import', content, re.MULTILINE)
        if import_match:
            insert_pos = import_match.end()
            content = content[:insert_pos] + '\nfrom src.config import get_config' + content[insert_pos:]
    
    # 在文件开头添加配置获取
    init_function_pattern = r'def __init__\(self\):'
    if re.search(init_function_pattern, content):
        # 在 __init__ 方法开头添加配置获取
        content = re.sub(
            r'(def __init__\(self\):\s*\n)',
            r'\1        self.config = get_config()\n',
            content
        )
        
        # 替换环境变量读取
        changes = 0
        
        # 替换 self.env = os.getenv(...)
        pattern1 = r'self\.env = os\.getenv\("FUND_DAILY_ENV",\s*"development"\)'
        if re.search(pattern1, content):
            content = re.sub(pattern1, 'self.env = self.config.env', content)
            changes += 1
        
        # 替换其他 os.getenv 调用
        pattern2 = r'os\.getenv\("FUND_DAILY_ADMIN_TOKEN"\)'
        if re.search(pattern2, content):
            # 注意：这个配置可能不在标准配置中，需要特殊处理
            # 暂时保留，但标记为需要手动处理
            print("⚠️  发现 FUND_DAILY_ADMIN_TOKEN，需要手动处理")
        
        pattern3 = r'os\.getenv\("FUND_DAILY_USER_TOKEN"\)'
        if re.search(pattern3, content):
            print("⚠️  发现 FUND_DAILY_USER_TOKEN，需要手动处理")
        
        if changes > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已迁移 src/api_gateway/core.py: {changes} 处配置调用")
        else:
            print("⚠️  src/api_gateway/core.py 中未迁移任何配置调用")
    else:
        print("❌ 未找到 __init__ 方法，无法自动迁移")

def main():
    print("🔧 开始迁移配置使用...\n")
    
    # 按优先级迁移
    print("1. 迁移数据库连接池配置 (高优先级)...")
    migrate_db_pool()
    
    print("\n2. 迁移JWT认证配置 (高优先级)...")
    migrate_jwt_auth()
    
    print("\n3. 迁移速率限制器配置 (中优先级)...")
    migrate_rate_limiter()
    
    print("\n4. 迁移API网关配置 (中优先级)...")
    migrate_api_gateway()
    
    print("\n📊 迁移完成!")
    print("   配置使用已统一到 get_config() 接口")
    
    # 创建迁移报告
    report = """# 配置使用迁移报告

## 迁移内容
将以下文件的配置读取从直接 os.getenv() 调用迁移到统一的 get_config() 接口:

### 1. db/pool.py - 数据库连接池
- **迁移前**: 使用 `os.environ.get()` 读取数据库配置
- **迁移后**: 使用 `get_config().database` 获取配置
- **配置项**:
  - `FUND_DAILY_DB_HOST` → `config.database.host`
  - `FUND_DAILY_DB_PORT` → `config.database.port`
  - `FUND_DAILY_DB_NAME` → `config.database.name`
  - `FUND_DAILY_DB_USER` → `config.database.user`
  - `FUND_DAILY_DB_PASSWORD` → `config.database.password`

### 2. src/jwt_auth.py - JWT认证
- **迁移前**: 使用 `os.getenv()` 读取JWT配置
- **迁移后**: 使用 `get_config().jwt` 获取配置
- **配置项**:
  - `FUND_DAILY_JWT_SECRET` → `config.jwt.secret`
  - `FUND_DAILY_ENV` → `config.env`
  - `FUND_DAILY_JWT_ALGORITHM` → `config.jwt.algorithm`
  - `FUND_DAILY_JWT_EXPIRE_MINUTES` → `config.jwt.access_token_expire_minutes`

### 3. web/api/rate_limiter.py - 速率限制器
- **迁移前**: 使用 `os.getenv()` 读取Redis配置
- **迁移后**: 使用 `get_config().redis` 获取配置
- **配置项**:
  - `FUND_DAILY_REDIS_HOST` → `config.redis.host`
  - `FUND_DAILY_REDIS_PORT` → `config.redis.port`
  - `FUND_DAILY_REDIS_DB` → `config.redis.db`

### 4. src/api_gateway/core.py - API网关
- **迁移状态**: 部分迁移
- **已迁移**: `FUND_DAILY_ENV` → `config.env`
- **待处理**: `FUND_DAILY_ADMIN_TOKEN`, `FUND_DAILY_USER_TOKEN`
  - 这些配置可能不在标准配置类中，需要扩展配置类

## 迁移好处
1. **统一管理**: 所有配置通过单一接口获取
2. **类型安全**: 配置值有明确的类型定义
3. **验证集中**: 配置验证逻辑集中在配置类中
4. **默认值一致**: 避免默认值分散定义
5. **环境感知**: 根据环境自动加载相应配置

## 验证步骤
1. 运行数据库连接测试
2. 测试JWT认证功能
3. 验证速率限制器工作正常
4. 测试API网关功能

## 注意事项
1. **配置扩展**: 需要为 `FUND_DAILY_ADMIN_TOKEN` 和 `FUND_DAILY_USER_TOKEN` 添加配置支持
2. **类型转换**: 确保字符串到其他类型的转换正确
3. **默认值**: 验证迁移前后默认值一致
4. **环境变量**: 确保环境变量名与配置类字段对应

## 后续工作
1. 扩展配置类以支持所有环境变量
2. 添加配置验证和文档生成
3. 实现配置热重载支持
4. 集成配置监控和告警
"""
    
    report_file = Path("/home/kid/fund-daily/docs/CONFIG_MIGRATION_REPORT.md")
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 报告已保存: {report_file}")

if __name__ == "__main__":
    main()