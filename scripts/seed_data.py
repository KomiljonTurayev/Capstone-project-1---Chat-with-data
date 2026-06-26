import sys
import os
import sqlite3
import random
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from faker import Faker
from database import get_connection

fake = Faker()
random.seed(42)
Faker.seed(42)

CATEGORIES = ["Electronics", "Clothing", "Books", "Sports", "Home & Kitchen"]
STATUSES = ["pending", "shipped", "delivered", "cancelled"]

PRODUCT_NAMES = {
    "Electronics": ["Laptop", "Smartphone", "Headphones", "Tablet", "Smartwatch",
                    "Keyboard", "Mouse", "Monitor", "Webcam", "Speaker", "Camera",
                    "USB Hub", "Power Bank"],
    "Clothing":    ["T-Shirt", "Jeans", "Jacket", "Sneakers", "Dress",
                    "Hoodie", "Shorts", "Boots", "Scarf", "Hat", "Socks"],
    "Books":       ["Python Basics", "Data Science 101", "Clean Code", "Deep Learning",
                    "Fiction Novel", "History Book", "Cookbook", "Self-Help Guide",
                    "Business Strategy", "AI for Everyone"],
    "Sports":      ["Yoga Mat", "Dumbbell Set", "Running Shoes", "Water Bottle",
                    "Resistance Bands", "Jump Rope", "Gym Gloves", "Protein Shaker",
                    "Foam Roller", "Sports Bag"],
    "Home & Kitchen": ["Coffee Maker", "Blender", "Air Fryer", "Toaster", "Kettle",
                       "Cutting Board", "Knife Set", "Storage Containers", "Vacuum",
                       "Rice Cooker", "Dish Rack"],
}


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    NOT NULL UNIQUE,
            phone      TEXT,
            city       TEXT,
            created_at DATE    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            category TEXT    NOT NULL,
            price    REAL    NOT NULL,
            stock    INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id  INTEGER NOT NULL REFERENCES customers(id),
            order_date   DATE    NOT NULL,
            status       TEXT    NOT NULL,
            total_amount REAL    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    INTEGER NOT NULL REFERENCES orders(id),
            product_id  INTEGER NOT NULL REFERENCES products(id),
            quantity    INTEGER NOT NULL,
            unit_price  REAL    NOT NULL
        );
    """)
    conn.commit()


def seed_customers(conn: sqlite3.Connection, n: int = 200) -> list:
    rows = []
    seen_emails = set()
    attempts = 0
    while len(rows) < n and attempts < n * 10:
        attempts += 1
        email = fake.email()
        if email in seen_emails:
            continue
        seen_emails.add(email)
        start = date(2021, 1, 1)
        created = start + timedelta(days=random.randint(0, 1095))
        rows.append((fake.name(), email, fake.phone_number()[:20],
                     fake.city(), created.isoformat()))
    conn.executemany(
        "INSERT INTO customers (name, email, phone, city, created_at) VALUES (?,?,?,?,?)",
        rows,
    )
    conn.commit()
    return [r[0] for r in conn.execute("SELECT id FROM customers").fetchall()]


def seed_products(conn: sqlite3.Connection) -> list:
    rows = []
    for category, names in PRODUCT_NAMES.items():
        for name in names:
            price = round(random.uniform(5.0, 999.99), 2)
            stock = random.randint(0, 200)
            rows.append((name, category, price, stock))
    conn.executemany(
        "INSERT INTO products (name, category, price, stock) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit()
    return [r[0] for r in conn.execute("SELECT id FROM products").fetchall()]


def seed_orders(
    conn: sqlite3.Connection,
    customer_ids: list,
    product_ids: list,
    n: int = 300,
) -> None:
    for _ in range(n):
        customer_id = random.choice(customer_ids)
        start = date(2022, 1, 1)
        order_date = start + timedelta(days=random.randint(0, 730))
        status = random.choices(STATUSES, weights=[15, 20, 55, 10])[0]

        item_count = random.randint(1, 5)
        chosen_products = random.sample(product_ids, min(item_count, len(product_ids)))
        items = []
        total = 0.0
        for pid in chosen_products:
            qty = random.randint(1, 4)
            price = conn.execute(
                "SELECT price FROM products WHERE id=?", (pid,)
            ).fetchone()[0]
            total += qty * price
            items.append((pid, qty, price))

        cur = conn.execute(
            "INSERT INTO orders (customer_id, order_date, status, total_amount) VALUES (?,?,?,?)",
            (customer_id, order_date.isoformat(), status, round(total, 2)),
        )
        order_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?,?,?,?)",
            [(order_id, pid, qty, price) for pid, qty, price in items],
        )
    conn.commit()


def already_seeded(conn: sqlite3.Connection) -> bool:
    try:
        count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        return count > 0
    except sqlite3.OperationalError:
        return False


def main() -> None:
    conn = get_connection()
    if already_seeded(conn):
        print("Database already seeded — skipping.")
        conn.close()
        return
    print("Creating tables...")
    create_tables(conn)
    print("Seeding customers...")
    customer_ids = seed_customers(conn, 200)
    print("Seeding products...")
    product_ids = seed_products(conn)
    print("Seeding orders and order_items...")
    seed_orders(conn, customer_ids, product_ids, 300)
    counts = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("customers", "products", "orders", "order_items")
    }
    print("Done!", counts)
    conn.close()


if __name__ == "__main__":
    main()
