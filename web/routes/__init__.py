"""
Routes package
API路由模块
"""
from .auth import auth_bp
from .holdings import holdings_bp
from .data import data_bp

__all__ = ['auth_bp', 'holdings_bp', 'data_bp']
