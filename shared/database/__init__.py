"""
Unified Database Layer for LMS Backend
Consolidates all database operations into a single, optimized interface
"""

from .connection import get_database, close_connection, init_database
from .operations import DatabaseOperations
from .health import health_check
from .indexes import create_indexes

__all__ = [
    'get_database',
    'close_connection',
    'init_database',
    'DatabaseOperations',
    'health_check',
    'create_indexes'
]