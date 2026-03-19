"""基金数据操作模块"""
from .pool import get_db, get_cursor

def save_fund_info(fund_code, fund_name, fund_type=None, fund_company=None, 
                   establish_date=None, fund_size=None, manager=None, 
                   risk_level=None, rating=None):
    """保存基金基本信息"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("""
                INSERT INTO funds (
                    fund_code, fund_name, fund_type, fund_company,
                    establish_date, fund_size, manager, risk_level, rating
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fund_code) DO UPDATE SET
                    fund_name = EXCLUDED.fund_name,
                    fund_type = EXCLUDED.fund_type,
                    fund_company = EXCLUDED.fund_company,
                    establish_date = EXCLUDED.establish_date,
                    fund_size = EXCLUDED.fund_size,
                    manager = EXCLUDED.manager,
                    risk_level = EXCLUDED.risk_level,
                    rating = EXCLUDED.rating,
                    updated_at = CURRENT_TIMESTAMP
            """, (fund_code, fund_name, fund_type, fund_company, 
                  establish_date, fund_size, manager, risk_level, rating))
            conn.commit()

def save_fund_nav(fund_code, nav_date, net_value=None, accumulated_value=None,
                  daily_return=None, weekly_return=None, monthly_return=None,
                  quarterly_return=None, yearly_return=None):
    """保存基金净值数据"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            # 首先确保基金基本信息存在
            cursor.execute("INSERT INTO funds (fund_code, fund_name) VALUES (%s, %s) ON CONFLICT DO NOTHING", 
                         (fund_code, f"基金{fund_code}"))
            
            cursor.execute("""
                INSERT INTO fund_nav (
                    fund_code, nav_date, net_value, accumulated_value,
                    daily_return, weekly_return, monthly_return,
                    quarterly_return, yearly_return
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fund_code, nav_date) DO UPDATE SET
                    net_value = EXCLUDED.net_value,
                    accumulated_value = EXCLUDED.accumulated_value,
                    daily_return = EXCLUDED.daily_return,
                    weekly_return = EXCLUDED.weekly_return,
                    monthly_return = EXCLUDED.monthly_return,
                    quarterly_return = EXCLUDED.quarterly_return,
                    yearly_return = EXCLUDED.yearly_return,
                    created_at = CURRENT_TIMESTAMP
            """, (fund_code, nav_date, net_value, accumulated_value,
                  daily_return, weekly_return, monthly_return,
                  quarterly_return, yearly_return))
            conn.commit()

def save_fund_score(fund_code, score_date, total_score=None,
                    valuation_score=None, sector_score=None, risk_score=None,
                    valuation_reason=None, sector_reason=None, risk_reason=None):
    """保存基金评分数据"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            # 首先确保基金基本信息存在
            cursor.execute("INSERT INTO funds (fund_code, fund_name) VALUES (%s, %s) ON CONFLICT DO NOTHING", 
                         (fund_code, f"基金{fund_code}"))
            
            cursor.execute("""
                INSERT INTO fund_scores (
                    fund_code, score_date, total_score,
                    valuation_score, sector_score, risk_score,
                    valuation_reason, sector_reason, risk_reason
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fund_code, score_date) DO UPDATE SET
                    total_score = EXCLUDED.total_score,
                    valuation_score = EXCLUDED.valuation_score,
                    sector_score = EXCLUDED.sector_score,
                    risk_score = EXCLUDED.risk_score,
                    valuation_reason = EXCLUDED.valuation_reason,
                    sector_reason = EXCLUDED.sector_reason,
                    risk_reason = EXCLUDED.risk_reason,
                    created_at = CURRENT_TIMESTAMP
            """, (fund_code, score_date, total_score,
                  valuation_score, sector_score, risk_score,
                  valuation_reason, sector_reason, risk_reason))
            conn.commit()

def get_fund_info(fund_code):
    """获取基金基本信息"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT * FROM funds WHERE fund_code = %s", (fund_code,))
            row = cursor.fetchone()
            return dict(row) if row else None

def get_fund_nav(fund_code, nav_date=None):
    """获取基金净值数据"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            if nav_date:
                cursor.execute("SELECT * FROM fund_nav WHERE fund_code = %s AND nav_date = %s", 
                             (fund_code, nav_date))
            else:
                cursor.execute("SELECT * FROM fund_nav WHERE fund_code = %s ORDER BY nav_date DESC LIMIT 1", 
                             (fund_code,))
            row = cursor.fetchone()
            return dict(row) if row else None

def get_fund_score(fund_code, score_date=None):
    """获取基金评分数据"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            if score_date:
                cursor.execute("SELECT * FROM fund_scores WHERE fund_code = %s AND score_date = %s", 
                             (fund_code, score_date))
            else:
                cursor.execute("SELECT * FROM fund_scores WHERE fund_code = %s ORDER BY score_date DESC LIMIT 1", 
                             (fund_code,))
            row = cursor.fetchone()
            return dict(row) if row else None

def get_recent_funds(days=7):
    """获取最近有更新的基金"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("""
                SELECT DISTINCT f.*, 
                       fn.nav_date as last_nav_date,
                       fn.net_value as last_net_value,
                       fs.score_date as last_score_date,
                       fs.total_score as last_total_score
                FROM funds f
                LEFT JOIN fund_nav fn ON f.fund_code = fn.fund_code 
                    AND fn.nav_date = (SELECT MAX(nav_date) FROM fund_nav WHERE fund_code = f.fund_code)
                LEFT JOIN fund_scores fs ON f.fund_code = fs.fund_code 
                    AND fs.score_date = (SELECT MAX(score_date) FROM fund_scores WHERE fund_code = f.fund_code)
                WHERE f.updated_at >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY f.updated_at DESC
            """, (days,))
            return [dict(row) for row in cursor.fetchall()]

def search_funds(query):
    """搜索基金"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("""
                SELECT * FROM funds 
                WHERE fund_code LIKE %s OR fund_name LIKE %s
                ORDER BY fund_code
                LIMIT 20
            """, (f"%{query}%", f"%{query}%"))
            return [dict(row) for row in cursor.fetchall()]

def get_fund_history(fund_code, days=30):
    """获取基金历史数据"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            # 获取净值历史
            cursor.execute("""
                SELECT * FROM fund_nav 
                WHERE fund_code = %s AND nav_date >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY nav_date DESC
            """, (fund_code, days))
            nav_history = [dict(row) for row in cursor.fetchall()]
            
            # 获取评分历史
            cursor.execute("""
                SELECT * FROM fund_scores 
                WHERE fund_code = %s AND score_date >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY score_date DESC
            """, (fund_code, days))
            score_history = [dict(row) for row in cursor.fetchall()]
            
            return {
                'fund_info': get_fund_info(fund_code),
                'nav_history': nav_history,
                'score_history': score_history
            }

def save_fund_data(fund_code, fund_data):
    """保存完整的基金数据（兼容现有API格式）"""
    import json
    from datetime import date
    
    try:
        # 保存基本信息
        save_fund_info(
            fund_code=fund_code,
            fund_name=fund_data.get('fund_name', f'基金{fund_code}'),
            fund_type=fund_data.get('fund_type'),
            fund_company=fund_data.get('fund_company'),
            establish_date=fund_data.get('establish_date'),
            fund_size=fund_data.get('fund_size'),
            manager=fund_data.get('manager'),
            risk_level=fund_data.get('risk_level'),
            rating=fund_data.get('rating')
        )
        
        # 保存净值数据（如果存在）
        if 'net_value' in fund_data:
            save_fund_nav(
                fund_code=fund_code,
                nav_date=date.today(),
                net_value=fund_data.get('net_value'),
                accumulated_value=fund_data.get('accumulated_value'),
                daily_return=fund_data.get('daily_return'),
                weekly_return=fund_data.get('weekly_return'),
                monthly_return=fund_data.get('monthly_return'),
                quarterly_return=fund_data.get('quarterly_return'),
                yearly_return=fund_data.get('yearly_return')
            )
        
        # 保存评分数据（如果存在）
        score_100 = fund_data.get('score_100', {})
        if score_100:
            save_fund_score(
                fund_code=fund_code,
                score_date=date.today(),
                total_score=score_100.get('total_score'),
                valuation_score=score_100.get('valuation', {}).get('score'),
                sector_score=score_100.get('sector', {}).get('score'),
                risk_score=score_100.get('risk_control', {}).get('score'),
                valuation_reason=score_100.get('valuation', {}).get('reason'),
                sector_reason=score_100.get('sector', {}).get('reason'),
                risk_reason=score_100.get('risk_control', {}).get('reason')
            )
        
        return True
    except Exception as e:
        logger.error(f"保存基金数据失败: {fund_code}, {e}")
        return False

# 兼容性别名
def get_all_holdings():
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT * FROM holdings")
            return [dict(row) for row in cursor.fetchall()]

def save_holdings(user_id, holdings):
    for h in holdings:
        save_holding(
            user_id,
            h.get("code", ""),
            h.get("amount", 0),
            h.get("name") or "",
            h.get("buy_nav") or h.get("buyNav"),
            h.get("buy_date") or h.get("buyDate")
        )

if __name__ == "__main__":
    init_db()
    print("Database initialized!")
