import pytest
from safety import validate_sql


@pytest.mark.parametrize("sql", [
    "DELETE FROM customers WHERE id=1",
    "delete from orders",
    "DROP TABLE products",
    "drop table products",
    "UPDATE customers SET name='x'",
    "INSERT INTO customers VALUES (1,'a','b',null,null,null)",
    "ALTER TABLE customers ADD COLUMN x TEXT",
    "TRUNCATE TABLE orders",
    "CREATE TABLE foo (id INTEGER)",
    "REPLACE INTO customers VALUES (1,'a','b',null,null,null)",
    "SELECT * FROM customers; DROP TABLE orders;",
])
def test_dangerous_sql_is_blocked(sql):
    with pytest.raises(PermissionError, match="blocked"):
        validate_sql(sql)


@pytest.mark.parametrize("sql", [
    "SELECT * FROM customers",
    "SELECT COUNT(*) FROM orders",
    "SELECT p.name, SUM(oi.quantity) FROM products p JOIN order_items oi ON p.id=oi.product_id GROUP BY p.name",
    "SELECT c.name, SUM(o.total_amount) FROM customers c JOIN orders o ON c.id=o.customer_id GROUP BY c.id ORDER BY 2 DESC LIMIT 5",
])
def test_safe_sql_passes(sql):
    validate_sql(sql)  # must not raise
