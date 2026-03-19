#!/bin/sh
# 数据库备份脚本

set -e

# 备份目录
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/fund_daily_${TIMESTAMP}.sql"

# 创建备份
echo "开始备份数据库..."
pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  --clean --if-exists --no-owner --no-privileges \
  -f "$BACKUP_FILE"

# 压缩备份
gzip "$BACKUP_FILE"
BACKUP_FILE_GZ="${BACKUP_FILE}.gz"

echo "备份完成: ${BACKUP_FILE_GZ}"
echo "文件大小: $(du -h "${BACKUP_FILE_GZ}" | cut -f1)"

# 保留最近7天的备份
find "$BACKUP_DIR" -name "fund_daily_*.sql.gz" -mtime +7 -delete

# 列出当前备份
echo "当前备份文件:"
ls -lh "$BACKUP_DIR"/fund_daily_*.sql.gz 2>/dev/null || echo "无备份文件"