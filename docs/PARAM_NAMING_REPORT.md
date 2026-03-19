# 参数命名一致性检查报告

## FUND_CODE 参数
- **标准名称**: `fund_code`
- **发现变体**: `fund_codes`
- **影响文件数**: 4
- **具体位置**:
  - `src/fetcher/alipay.py`:
    - `fetch_fund_detail_alipay()` 使用 `fund_codes`
    - `fetch_fund_detail_alipay()` 使用 `fund_codes`
  - `src/services/score_service.py`:
    - `calculate_score()` 使用 `fund_codes`
  - `src/services/fund_service.py`:
    - `get_fund_score()` 使用 `fund_codes`
    - `get_fund_score()` 使用 `fund_codes`
  - `src/advice/generate.py`:
    - `generate_advice()` 使用 `fund_codes`

## AMOUNT 参数
- **标准名称**: `amount`
- **发现变体**: `amounts`, `amount_num`, `amounts_by_line`
- **影响文件数**: 2
- **具体位置**:
  - `src/ocr.py`:
    - `_extract_all_amounts()` 使用 `amounts`
    - `parse()` 使用 `amounts_by_line`
  - `web/api/validation.py`:
    - `validate_amount()` 使用 `amount_num`

## DATE 参数
- **标准名称**: `date`
- **发现变体**: `nav_date`, `data_date`, `date_str`
- **影响文件数**: 2
- **具体位置**:
  - `src/fetcher/enhanced_fetcher.py`:
    - `fetch_fund_data()` 使用 `nav_date`
    - `fetch_fund_data()` 使用 `data_date`
  - `web/api/validation.py`:
    - `validate_date()` 使用 `date_str`
    - `validate_date()` 使用 `date_str`


## 总结
- **总问题数**: 7 个不一致的参数命名
- **需要统一的概念**: 3 个
