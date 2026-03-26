-- 修复持仓名称缺失问题
-- 将 funds 表的 fund_name 回填到 holdings 表的 name 字段
UPDATE holdings h
SET name = f.fund_name
FROM funds f
WHERE h.code = f.fund_code
  AND h.name IS DISTINCT FROM f.fund_name
  AND f.fund_name IS NOT NULL
  AND f.fund_name != '';
