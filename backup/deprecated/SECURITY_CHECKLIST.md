# Fund Daily 安全部署检查清单

## 🚨 生产环境部署前必须完成

### 1. 环境变量配置
- [ ] 创建 `.env` 文件（不要提交到版本控制）
- [ ] 设置强密码和密钥（使用 `scripts/check_security.py` 生成）
- [ ] 验证环境变量文件权限：`chmod 600 .env`

### 2. 密钥和密码要求
- [ ] **JWT 密钥**: 至少32字符，包含大小写字母、数字、特殊字符
- [ ] **Flask 密钥**: 至少32字符，使用 `secrets.token_hex(32)` 生成
- [ ] **数据库密码**: 至少16字符，避免使用常见密码
- [ ] **API 网关令牌**: 每个角色使用不同的强令牌

### 3. 文件权限检查
- [ ] `.env` 文件权限: 600（仅所有者可读写）
- [ ] 配置文件权限: 644（所有者可读写，其他只读）
- [ ] 日志目录权限: 755（所有者可读写执行，其他只读执行）

### 4. 网络和安全配置
- [ ] 启用 HTTPS（使用 Nginx 或负载均衡器）
- [ ] 配置防火墙规则（仅开放必要端口）
- [ ] 设置数据库仅允许应用服务器访问
- [ ] 配置 Redis 密码认证

### 5. 应用安全配置
- [ ] 设置 `FUND_DAILY_ENV=production`
- [ ] 启用安全 Cookie: `FUND_DAILY_SECURE_COOKIES=true`
- [ ] 禁用调试模式: `FLASK_DEBUG=false`
- [ ] 配置 CORS 允许的域名

## 🔧 安全加固步骤

### 步骤 1: 生成安全密钥
```bash
cd /home/kid/fund-daily
python3 scripts/check_security.py --generate-secrets
```

### 步骤 2: 创建生产环境配置文件
```bash
# 创建 .env 文件
cp .env.example .env
# 编辑 .env 文件，替换所有 CHANGE_ME 为强密码
vim .env
# 设置文件权限
chmod 600 .env
```

### 步骤 3: 更新 Docker 配置
```bash
# 确保 docker-compose.yml 使用环境变量文件
# 不要创建 docker-compose.override.yml（仅用于开发）
```

### 步骤 4: 启动服务
```bash
# 使用生产环境配置启动
docker-compose up -d
```

### 步骤 5: 验证安全配置
```bash
# 运行安全检查
python3 scripts/check_security.py

# 测试安全头
curl -I https://your-domain.com/api/health
# 应包含以下安全头:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# Strict-Transport-Security: max-age=31536000
```

## 📊 监控和告警

### 必须监控的指标
- [ ] 认证失败次数
- [ ] API 请求速率异常
- [ ] 数据库连接异常
- [ ] Redis 缓存命中率下降
- [ ] 应用错误率上升

### 安全日志
- [ ] 启用应用访问日志
- [ ] 记录所有认证事件
- [ ] 记录敏感操作（用户创建、权限变更等）
- [ ] 配置日志轮转和归档

## 🚑 应急响应

### 安全事件处理流程
1. **识别**: 发现安全事件（异常登录、数据泄露等）
2. **隔离**: 立即隔离受影响系统
3. **调查**: 收集日志，分析攻击路径
4. **修复**: 修补漏洞，重置受影响凭证
5. **恢复**: 验证修复后恢复服务
6. **复盘**: 分析根本原因，改进防护

### 联系人清单
- 系统管理员: [姓名/联系方式]
- 安全负责人: [姓名/联系方式]
- 开发团队: [团队联系方式]

## 📚 参考文档

### 安全最佳实践
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Flask 安全指南](https://flask.palletsprojects.com/en/stable/security/)

### 工具和资源
- 漏洞扫描: [Trivy](https://github.com/aquasecurity/trivy)
- 密钥管理: [HashiCorp Vault](https://www.vaultproject.io/)
- 安全头检查: [SecurityHeaders.com](https://securityheaders.com/)

---

**最后更新**: 2026-03-19  
**版本**: 1.0  
**责任人**: 系统管理员