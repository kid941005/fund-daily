# 缓存键生成统一优化报告

## 优化内容
将分散的缓存键生成逻辑统一到 `src/utils/cache_keys.py` 工具模块。

### 1. 创建的缓存键生成器
**类**: `CacheKeyGenerator`
**实例**: `cache_keys` (单例)

**支持的方法**:
- `fund_data(fund_code)` - 基金数据缓存键
- `fund_detail(fund_code)` - 基金详情缓存键  
- `fund_score(fund_code)` - 基金评分缓存键
- `market_sentiment()` - 市场情绪缓存键
- `market_news(limit)` - 市场新闻缓存键
- `hot_sectors(limit)` - 热点板块缓存键
- `fund_manager(fund_code)` - 基金经理缓存键
- `user_holdings(user_id)` - 用户持仓缓存键
- `user_watchlist(user_id)` - 用户关注列表缓存键
- `custom(prefix_key, *parts)` - 自定义缓存键

### 2. 更新的模块

#### 2.1 src/fetcher/__init__.py
- **添加导入**: `from src.utils.cache_keys import cache_keys`
- **替换的缓存键**:
  - `f"fund:{fund_code}"` → `cache_keys.fund_data(fund_code)`
  - `f"fund_detail:{fund_code}"` → `cache_keys.fund_detail(fund_code)`
  - `f"news:{limit}"` → `cache_keys.market_news(limit)`
  - `f"sectors:{limit}"` → `cache_keys.hot_sectors(limit)`
  - `f"fund_manager:{fund_code}"` → `cache_keys.fund_manager(fund_code)`

#### 2.2 src/services/market_service.py
- **添加导入**: `from src.utils.cache_keys import cache_keys`
- **替换的缓存键**:
  - `f"{self.cache_prefix}sentiment"` → `cache_keys.market_sentiment()`
  - `f"{self.cache_prefix}commodity"` → `cache_keys.custom("market", "commodity")`
  - `f"{self.cache_prefix}hot_sectors"` → `cache_keys.hot_sectors()`
  - `f"{self.cache_prefix}market_news"` → `cache_keys.market_news()`

## 优化好处
1. **一致性**: 所有缓存键使用统一的格式和前缀
2. **可维护性**: 缓存键生成逻辑集中管理
3. **可测试性**: 更容易测试缓存键生成
4. **可扩展性**: 添加新的缓存键类型更容易
5. **减少错误**: 避免手动拼接缓存键时的错误

## 向后兼容性
提供了向后兼容的函数:
- `get_fund_data_key(fund_code)`
- `get_fund_score_key(fund_code)`  
- `get_market_news_key(limit)`

## 验证步骤
1. 运行缓存相关的单元测试
2. 测试数据获取功能正常
3. 验证缓存命中率统计

## 后续优化
1. 更新其他模块使用统一的缓存键生成器
2. 添加缓存键验证和文档
3. 实现缓存键版本管理
