import sqlite3
import pytest
from database import get_connection


def test_get_connection_returns_connection():
    conn = get_connection()
    assert isinstance(conn, sqlite3.Connection)
    conn.close()


def test_tables_exist_after_seed():
    conn = get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {row[0] for row in tables}
    assert {"customers", "products", "orders", "order_items"}.issubset(table_names)
    conn.close()


def test_row_counts_meet_minimum():
    conn = get_connection()
    customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    order_items = conn.execute("SELECT COUNT(*) FROM order_items").fetchone()[0]
    assert customers >= 200
    assert products >= 50
    assert orders >= 300
    assert order_items >= 500
    conn.close()
