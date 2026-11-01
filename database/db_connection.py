"""
db_connection.py
================
MySQL database connection helper for RentEase Rental Portal.

Provides:
  - A reusable connection factory with sensible defaults.
  - A context-manager-based connection helper.
  - Safe parameterized query helpers:
      execute_query(sql, params)   -> INSERT / UPDATE / DELETE (returns lastrowid)
      fetch_all(sql, params)       -> SELECT multiple rows
      fetch_one(sql, params)       -> SELECT single row
  - Graceful error handling — no uncaught exceptions reach Streamlit.

All credentials can be overridden via environment variables:
  DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT
"""

import os
import contextlib
from typing import Any, Dict, List, Optional, Tuple

import mysql.connector
from mysql.connector import Error as MySQLError

# ------------------------------------------------------------------
# Default connection configuration (override via environment vars)
# ------------------------------------------------------------------
DB_CONFIG: Dict[str, Any] = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "user":     os.environ.get("DB_USER",     "root"),
    "password": os.environ.get("DB_PASSWORD", "Yash2005#"),
    "database": os.environ.get("DB_NAME",     "rental_db"),
    "port":     int(os.environ.get("DB_PORT", 3306)),
    "charset":  "utf8mb4",
    "use_unicode": True,
    "autocommit": False,
    "connection_timeout": 10,
    "raise_on_warnings": True,
}


# ------------------------------------------------------------------
# Low-level connection factory
# ------------------------------------------------------------------
def _get_connection() -> Optional[mysql.connector.MySQLConnection]:
    """
    Open and return a raw MySQL connection using DB_CONFIG.
    Returns None and prints the error if the connection fails.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except MySQLError as exc:
        print(f"[DB ERROR] Could not connect to MySQL: {exc}")
        return None


# ------------------------------------------------------------------
# Context manager – preferred for transactional work
# ------------------------------------------------------------------
@contextlib.contextmanager
def get_db_connection():
    """
    Context manager that yields a MySQL connection and handles
    commit/rollback automatically.

    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(...)
    """
    conn = _get_connection()
    if conn is None:
        raise RuntimeError("Database connection could not be established.")
    try:
        yield conn
        conn.commit()
    except MySQLError as exc:
        conn.rollback()
        raise exc
    finally:
        if conn.is_connected():
            conn.close()


# ------------------------------------------------------------------
# High-level helpers
# ------------------------------------------------------------------

def execute_query(sql: str, params: Optional[Tuple] = None) -> Optional[int]:
    """
    Execute a data-modification query (INSERT, UPDATE, DELETE).

    Parameters
    ----------
    sql    : Parameterized SQL string (use %s placeholders).
    params : Tuple of values corresponding to %s placeholders.

    Returns
    -------
    int   : lastrowid for INSERT statements; 0 otherwise.
    None  : on error (error is printed to stdout for debugging).
    """
    conn = _get_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        conn.commit()
        last_id = cursor.lastrowid
        cursor.close()
        return last_id
    except MySQLError as exc:
        conn.rollback()
        print(f"[DB ERROR] execute_query failed: {exc}\nSQL: {sql}\nParams: {params}")
        return None
    finally:
        if conn.is_connected():
            conn.close()


def fetch_all(sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return all matching rows as a list of dicts.

    Parameters
    ----------
    sql    : Parameterized SQL string (use %s placeholders).
    params : Tuple of values corresponding to %s placeholders.

    Returns
    -------
    list[dict] : Rows as dictionaries (column_name -> value).
                 Returns an empty list on error.
    """
    conn = _get_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        rows = cursor.fetchall()
        cursor.close()
        return rows
    except MySQLError as exc:
        print(f"[DB ERROR] fetch_all failed: {exc}\nSQL: {sql}\nParams: {params}")
        return []
    finally:
        if conn.is_connected():
            conn.close()


def fetch_one(sql: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
    """
    Execute a SELECT query and return a single row as a dict (or None).

    Parameters
    ----------
    sql    : Parameterized SQL string (use %s placeholders).
    params : Tuple of values corresponding to %s placeholders.

    Returns
    -------
    dict  : The first matching row as a dictionary.
    None  : If no rows match, or on error.
    """
    conn = _get_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        row = cursor.fetchone()
        cursor.close()
        return row
    except MySQLError as exc:
        print(f"[DB ERROR] fetch_one failed: {exc}\nSQL: {sql}\nParams: {params}")
        return None
    finally:
        if conn.is_connected():
            conn.close()


def test_connection() -> bool:
    """
    Ping the database and return True if the connection is healthy.
    Used by the Streamlit app to show a DB-status indicator.
    """
    conn = _get_connection()
    if conn is None:
        return False
    try:
        conn.ping(reconnect=False, attempts=1, delay=0)
        return True
    except MySQLError:
        return False
    finally:
        if conn.is_connected():
            conn.close()
