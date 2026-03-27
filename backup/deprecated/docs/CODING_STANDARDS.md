# Fund Daily 命名规范

## 参数命名规范

### 核心参数
| 概念 | 标准名称 | 说明 | 示例 |
|------|----------|------|------|
| 基金代码 | `fund_code` | 6位数字加可选后缀 | `"000001"`, `"510300"` |
| 用户ID | `user_id` | 用户唯一标识 | `123`, `"user_abc"` |
| 持仓金额 | `amount` | 持仓数量或金额 | `1000.00` |
| 成本价 | `cost_basis` | 购买成本 | `1.2345` |
| 时间戳 | `timestamp` | Unix时间戳 | `1640995200` |
| 日期 | `date` | YYYY-MM-DD格式 | `"2024-01-01"` |

### 布尔参数
| 模式 | 示例 | 说明 |
|------|------|------|
| `is_` 前缀 | `is_active`, `is_valid` | 状态标志 |
| `has_` 前缀 | `has_permission`, `has_data` | 拥有关系 |
| `should_` 前缀 | `should_update`, `should_cache` | 行为标志 |

### 集合参数
| 类型 | 命名模式 | 示例 |
|------|----------|------|
| 列表 | 复数形式 | `funds`, `users`, `items` |
| 字典 | 单数形式 + 后缀 | `fund_data`, `user_info` |
| 查询结果 | `result` 或具体名称 | `search_result`, `fund_list` |

## 函数命名规范

### 验证函数
- 前缀: `validate_`
- 示例: `validate_fund_code()`, `validate_user_input()`

### 获取函数
- 前缀: `get_`, `fetch_`, `load_`
- 示例: `get_user_by_id()`, `fetch_fund_data()`

### 创建函数
- 前缀: `create_`, `add_`, `insert_`
- 示例: `create_user()`, `add_holding()`

### 更新函数
- 前缀: `update_`, `modify_`, `set_`
- 示例: `update_user_profile()`, `set_user_preferences()`

### 删除函数
- 前缀: `delete_`, `remove_`, `clear_`
- 示例: `delete_holding()`, `clear_cache()`

## 变量命名规范

### 局部变量
- 小写字母，下划线分隔
- 描述性名称
- 示例: `fund_data`, `user_count`, `is_valid`

### 常量
- 大写字母，下划线分隔
- 放在文件顶部
- 示例: `MAX_RETRY_COUNT`, `DEFAULT_CACHE_TTL`

### 类属性
- 小写字母，下划线分隔
- 私有属性以 `_` 开头
- 示例: `self.user_id`, `self._cache`

## 数据库字段命名

### 表名
- 小写字母，下划线分隔
- 复数形式
- 示例: `users`, `fund_holdings`

### 字段名
- 小写字母，下划线分隔
- 与参数命名一致
- 示例: `fund_code`, `user_id`, `created_at`

## 代码示例

### 好的示例
```python
def calculate_fund_score(fund_code: str, date: str = None) -> float:
    """计算基金评分"""
    fund_data = fetch_fund_data(fund_code, date)
    return calculate_score(fund_data)

def update_user_holdings(user_id: int, holdings_data: List[Dict]) -> bool:
    """更新用户持仓"""
    for holding in holdings_data:
        validate_holding_data(holding)
    return db.update_holdings(user_id, holdings_data)
```

### 避免的示例
```python
def calcScore(code: str, d: str = None) -> float:  # 不清晰
def updateHoldings(uid: int, data: List) -> bool:  # 缩写不一致
```

## 实施指南

1. **新代码**: 必须遵循此规范
2. **现有代码**: 逐步重构，优先修改频繁使用的代码
3. **代码审查**: 检查命名规范遵守情况
4. **自动化检查**: 使用工具检查命名一致性

## 例外情况

1. **第三方API**: 遵循第三方命名约定
2. **已有标准**: 遵循行业或技术标准
3. **性能关键代码**: 在必要时使用缩写

## 当前统一工作

### 已完成
1. ✅ 合并验证系统: `src/validation.py` → `web/api/validation.py`
2. ✅ 统一基金代码参数: `code` → `fund_code` (关键API端点)
3. ✅ 创建命名规范文档

### 进行中
1. 🔄 统一用户ID参数: `uid`, `userId` → `user_id`
2. 🔄 更新数据库字段引用
3. 🔄 更新测试用例

### 待完成
1. ⏳ 统一错误处理中间件
2. ⏳ 清理缓存冗余接口
3. ⏳ 自动化命名检查

---
*最后更新: 2026-03-19*
*版本: 1.0*