"""持仓、监控列表、配置管理模块"""
from .pool import get_db, get_cursor

def get_holdings(user_id):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute(
                "SELECT code, name, amount, buy_nav, buy_date FROM holdings WHERE user_id = %s",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

def save_holding(user_id, code, amount, name="", buy_nav=None, buy_date=None):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("""
                INSERT INTO holdings (user_id, code, name, amount, buy_nav, buy_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, code) DO UPDATE SET
                    name = EXCLUDED.name,
                    amount = EXCLUDED.amount,
                    buy_nav = EXCLUDED.buy_nav,
                    buy_date = EXCLUDED.buy_date,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, code, name, amount, buy_nav, buy_date))
            conn.commit()

def delete_holding(user_id, code):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("DELETE FROM holdings WHERE user_id = %s AND code = %s", (user_id, code))
            conn.commit()

def clear_holdings(user_id):
    """清空用户的所有持仓"""
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("DELETE FROM holdings WHERE user_id = %s", (user_id,))
            conn.commit()

# 其他操作...
def get_watchlist(user_id):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT code FROM watchlist WHERE user_id = %s", (user_id,))
            return [row['code'] for row in cursor.fetchall()]

def add_to_watchlist(user_id, code):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("INSERT INTO watchlist (user_id, code) VALUES (%s, %s) ON CONFLICT DO NOTHING", 
                         (user_id, code))
            conn.commit()

def remove_from_watchlist(user_id, code):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("DELETE FROM watchlist WHERE user_id = %s AND code = %s", (user_id, code))
            conn.commit()

def get_config(user_id):
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT config FROM config WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
            return row['config'] if row else None

def save_config(user_id, config):
    import json
    with get_db() as conn:
        with get_cursor(conn) as cursor:
            cursor.execute("""
                INSERT INTO config (user_id, config) VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET config = EXCLUDED.config, updated_at = CURRENT_TIMESTAMP
            """, (user_id, json.dumps(config)))
            conn.commit()

# 基金数据操作函数