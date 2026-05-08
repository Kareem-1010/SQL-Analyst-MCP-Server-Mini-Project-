#!/usr/bin/env python3
"""
Seed a user database with synthetic demo tables and data.

Creates a small but realistic retail/operations schema so the full product
can be exercised end-to-end with joins, aggregates, and destructive queries.

Usage:
    python scripts/seed_demo_data.py --db-name db_testuser2
    python scripts/seed_demo_data.py --db-name db_testuser2 --reset
"""

from __future__ import annotations

import argparse
import logging
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


TABLE_ORDER = [
    "departments",
    "employees",
    "customers",
    "suppliers",
    "categories",
    "products",
    "warehouses",
    "inventory",
    "orders",
    "order_items",
    "payments",
    "shipments",
    "support_tickets",
]


def parse_db_url(db_url: str) -> dict[str, str | int]:
    parsed = urlparse(db_url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": unquote(parsed.username) if parsed.username else "postgres",
        "password": unquote(parsed.password) if parsed.password else "",
        "dbname": parsed.path.lstrip("/") or "sqlanalyst",
    }


def connect(host: str, port: int, user: str, password: str, dbname: str):
    return psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        connect_timeout=10,
    )


def drop_existing(conn):
    with conn.cursor() as cur:
        for table in reversed(TABLE_ORDER):
            cur.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
    conn.commit()


def create_schema(conn):
    statements = [
        """
        CREATE TABLE IF NOT EXISTS departments (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            budget NUMERIC(12, 2) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            department_id INTEGER NOT NULL REFERENCES departments(id),
            first_name VARCHAR(80) NOT NULL,
            last_name VARCHAR(80) NOT NULL,
            title VARCHAR(120) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            salary NUMERIC(12, 2) NOT NULL,
            hire_date DATE NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(80) NOT NULL,
            last_name VARCHAR(80) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            phone VARCHAR(30),
            city VARCHAR(80) NOT NULL,
            country VARCHAR(80) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS suppliers (
            id SERIAL PRIMARY KEY,
            company_name VARCHAR(150) NOT NULL UNIQUE,
            contact_name VARCHAR(150) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(30),
            city VARCHAR(80) NOT NULL,
            country VARCHAR(80) NOT NULL,
            rating INTEGER NOT NULL DEFAULT 5
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
            sku VARCHAR(40) NOT NULL UNIQUE,
            name VARCHAR(150) NOT NULL,
            unit_price NUMERIC(12, 2) NOT NULL,
            cost_price NUMERIC(12, 2) NOT NULL,
            is_discontinued BOOLEAN NOT NULL DEFAULT FALSE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS warehouses (
            id SERIAL PRIMARY KEY,
            warehouse_code VARCHAR(20) NOT NULL UNIQUE,
            city VARCHAR(80) NOT NULL,
            country VARCHAR(80) NOT NULL,
            capacity INTEGER NOT NULL,
            manager_name VARCHAR(150) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY,
            product_id INTEGER NOT NULL REFERENCES products(id),
            warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
            quantity_on_hand INTEGER NOT NULL,
            reorder_level INTEGER NOT NULL,
            last_restocked_at TIMESTAMPTZ NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            order_number VARCHAR(30) NOT NULL UNIQUE,
            order_status VARCHAR(30) NOT NULL,
            order_date TIMESTAMPTZ NOT NULL,
            shipping_city VARCHAR(80) NOT NULL,
            total_amount NUMERIC(12, 2) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity INTEGER NOT NULL,
            unit_price NUMERIC(12, 2) NOT NULL,
            discount_percent NUMERIC(5, 2) NOT NULL DEFAULT 0,
            line_total NUMERIC(12, 2) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            payment_method VARCHAR(30) NOT NULL,
            payment_status VARCHAR(30) NOT NULL,
            amount NUMERIC(12, 2) NOT NULL,
            paid_at TIMESTAMPTZ NOT NULL,
            transaction_reference VARCHAR(60) NOT NULL UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS shipments (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
            tracking_number VARCHAR(60) NOT NULL UNIQUE,
            carrier VARCHAR(60) NOT NULL,
            shipment_status VARCHAR(30) NOT NULL,
            shipped_at TIMESTAMPTZ NOT NULL,
            delivered_at TIMESTAMPTZ
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS support_tickets (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,
            assigned_employee_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
            ticket_number VARCHAR(30) NOT NULL UNIQUE,
            subject VARCHAR(200) NOT NULL,
            priority VARCHAR(20) NOT NULL,
            ticket_status VARCHAR(30) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            resolved_at TIMESTAMPTZ
        )
        """,
    ]

    with conn.cursor() as cur:
        for statement in statements:
            cur.execute(statement)
    conn.commit()


def seed_data(conn):
    random.seed(42)
    now = datetime.now(timezone.utc)

    departments = [
        ("Executive", 250000.00),
        ("Sales", 180000.00),
        ("Marketing", 150000.00),
        ("Engineering", 320000.00),
        ("Operations", 210000.00),
    ]

    categories = [
        ("Electronics", "Devices and accessories"),
        ("Office Supplies", "Stationery and workspace essentials"),
        ("Home & Kitchen", "Household products"),
        ("Sports", "Fitness and outdoor gear"),
        ("Books", "Printed and digital books"),
    ]

    suppliers = [
        ("Northwind Supply Co.", "Ava Brooks", "ava@northwind.example", "555-0101", "Seattle", "USA", 5),
        ("Metro Wholesale Ltd.", "Liam Chen", "liam@metro.example", "555-0102", "Austin", "USA", 4),
        ("Global Importers", "Noah Patel", "noah@global.example", "555-0103", "Toronto", "Canada", 5),
        ("Prime Trade Group", "Emma Wilson", "emma@prime.example", "555-0104", "London", "UK", 4),
    ]

    warehouses = [
        ("WH-NY-01", "New York", "USA", 5000, "Morgan Reed"),
        ("WH-TX-01", "Dallas", "USA", 4200, "Jordan Kim"),
        ("WH-CA-01", "Los Angeles", "USA", 6100, "Casey Nguyen"),
    ]

    customers = []
    for i in range(1, 31):
        customers.append(
            (
                f"Customer{i}",
                f"{random.choice(['Smith', 'Johnson', 'Brown', 'Taylor', 'Davis', 'Moore'])}",
                f"customer{i}@example.com",
                f"+1-555-{1000 + i:04d}",
                random.choice(["New York", "Dallas", "Chicago", "Seattle", "Miami", "Boston"]),
                "USA",
                now - timedelta(days=random.randint(1, 365)),
            )
        )

    employees = []
    employee_titles = ["CEO", "Sales Manager", "Marketing Specialist", "Senior Engineer", "Operations Analyst", "Support Lead"]
    for i in range(1, 16):
        dept_id = (i % len(departments)) + 1
        employees.append(
            (
                dept_id,
                f"Emp{i}",
                random.choice(["Walker", "Harris", "Clark", "Lewis", "Young", "Allen"]),
                employee_titles[i % len(employee_titles)],
                f"employee{i}@example.com",
                round(random.uniform(65000, 180000), 2),
                (now - timedelta(days=random.randint(365, 2500))).date(),
                True,
            )
        )

    products = []
    for i in range(1, 41):
        category_id = ((i - 1) % len(categories)) + 1
        supplier_id = ((i - 1) % len(suppliers)) + 1
        unit_price = round(random.uniform(15, 900), 2)
        cost_price = round(unit_price * random.uniform(0.45, 0.75), 2)
        products.append(
            (
                category_id,
                supplier_id,
                f"SKU-{i:04d}",
                f"Product {i}",
                unit_price,
                cost_price,
                i % 17 == 0,
            )
        )

    inventory = []
    for product_id in range(1, len(products) + 1):
        for warehouse_id in range(1, len(warehouses) + 1):
            inventory.append(
                (
                    product_id,
                    warehouse_id,
                    random.randint(20, 650),
                    random.randint(10, 50),
                    now - timedelta(days=random.randint(1, 60)),
                )
            )

    orders = []
    for i in range(1, 61):
        customer_id = ((i - 1) % len(customers)) + 1
        order_date = now - timedelta(days=random.randint(1, 120))
        orders.append(
            (
                customer_id,
                f"ORD-{2026000 + i}",
                random.choice(["processing", "shipped", "delivered", "cancelled"]),
                order_date,
                random.choice(["New York", "Dallas", "Chicago", "Seattle", "Miami"]),
                0.0,
            )
        )

    support_tickets = []
    priorities = ["low", "medium", "high", "urgent"]
    statuses = ["open", "in_progress", "resolved", "closed"]
    subjects = [
        "Order delay",
        "Wrong item received",
        "Payment failed",
        "Return request",
        "Product damaged",
        "Invoice needed",
    ]
    for i in range(1, 26):
        support_tickets.append(
            (
                ((i - 1) % len(customers)) + 1,
                ((i - 1) % len(orders)) + 1 if i % 3 != 0 else None,
                ((i - 1) % len(employees)) + 1,
                f"TCK-{2026000 + i}",
                random.choice(subjects),
                random.choice(priorities),
                random.choice(statuses),
                now - timedelta(days=random.randint(1, 90)),
                None if i % 4 else now - timedelta(days=random.randint(0, 20)),
            )
        )

    with conn.cursor() as cur:
        execute_values(cur, "INSERT INTO departments (name, budget) VALUES %s", departments)
        execute_values(
            cur,
            "INSERT INTO categories (name, description) VALUES %s",
            categories,
        )
        execute_values(
            cur,
            "INSERT INTO suppliers (company_name, contact_name, email, phone, city, country, rating) VALUES %s",
            suppliers,
        )
        execute_values(
            cur,
            "INSERT INTO warehouses (warehouse_code, city, country, capacity, manager_name) VALUES %s",
            warehouses,
        )
        execute_values(
            cur,
            "INSERT INTO customers (first_name, last_name, email, phone, city, country, created_at) VALUES %s",
            customers,
        )
        execute_values(
            cur,
            "INSERT INTO employees (department_id, first_name, last_name, title, email, salary, hire_date, is_active) VALUES %s",
            employees,
        )
        execute_values(
            cur,
            "INSERT INTO products (category_id, supplier_id, sku, name, unit_price, cost_price, is_discontinued) VALUES %s",
            products,
        )
        execute_values(
            cur,
            "INSERT INTO inventory (product_id, warehouse_id, quantity_on_hand, reorder_level, last_restocked_at) VALUES %s",
            inventory,
        )
        execute_values(
            cur,
            "INSERT INTO orders (customer_id, order_number, order_status, order_date, shipping_city, total_amount) VALUES %s",
            orders,
        )

        order_items = []
        payments = []
        shipments = []
        order_totals: dict[int, float] = {}
        for order_id in range(1, len(orders) + 1):
            product_count = random.randint(1, 4)
            picked_products = random.sample(range(1, len(products) + 1), product_count)
            order_total = 0

            for product_id in picked_products:
                quantity = random.randint(1, 6)
                unit_price = round(random.uniform(20, 750), 2)
                discount = random.choice([0, 0, 5, 10, 15])
                line_total = round(quantity * unit_price * (1 - discount / 100), 2)
                order_total += line_total
                order_items.append((order_id, product_id, quantity, unit_price, discount, line_total))

            order_totals[order_id] = round(order_total, 2)

            paid_at = now - timedelta(days=random.randint(0, 90))
            payments.append(
                (
                    order_id,
                    random.choice(["card", "bank_transfer", "paypal", "cash"]),
                    random.choice(["paid", "paid", "pending", "refunded"]),
                    round(order_total, 2),
                    paid_at,
                    f"TXN-{2026000 + order_id}",
                )
            )

            shipped_at = now - timedelta(days=random.randint(0, 60))
            delivered_at = shipped_at + timedelta(days=random.randint(1, 10)) if order_id % 5 else None
            shipments.append(
                (
                    order_id,
                    random.randint(1, len(warehouses)),
                    f"TRK-{2026000 + order_id}",
                    random.choice(["DHL", "FedEx", "UPS", "USPS"]),
                    random.choice(["label_created", "in_transit", "delivered"]),
                    shipped_at,
                    delivered_at,
                )
            )

        execute_values(
            cur,
            "UPDATE orders AS o SET total_amount = data.total_amount FROM (VALUES %s) AS data(id, total_amount) WHERE o.id = data.id",
            [(order_id, total_amount) for order_id, total_amount in order_totals.items()],
            template=None,
            page_size=100,
        )

        execute_values(
            cur,
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_percent, line_total) VALUES %s",
            order_items,
        )
        execute_values(
            cur,
            "INSERT INTO payments (order_id, payment_method, payment_status, amount, paid_at, transaction_reference) VALUES %s",
            payments,
        )
        execute_values(
            cur,
            "INSERT INTO shipments (order_id, warehouse_id, tracking_number, carrier, shipment_status, shipped_at, delivered_at) VALUES %s",
            shipments,
        )
        execute_values(
            cur,
            "INSERT INTO support_tickets (customer_id, order_id, assigned_employee_id, ticket_number, subject, priority, ticket_status, created_at, resolved_at) VALUES %s",
            support_tickets,
        )

    conn.commit()


def count_rows(conn, table_name: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return int(cur.fetchone()[0])


def main():
    parser = argparse.ArgumentParser(description="Seed a user database with synthetic demo data")
    parser.add_argument("--db-name", required=True, help="Target PostgreSQL database name (for example db_testuser2)")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all demo tables before seeding")
    args = parser.parse_args()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL not set. Load backend/.env or pass environment variables first.")

    config = parse_db_url(db_url)
    conn = connect(config["host"], int(config["port"]), str(config["user"]), str(config["password"]), args.db_name)

    try:
        if args.reset:
            logger.info("Dropping existing demo tables...")
            drop_existing(conn)

        logger.info("Creating demo schema...")
        create_schema(conn)

        logger.info("Seeding synthetic rows...")
        seed_data(conn)

        logger.info("Seed complete")
        for table_name in TABLE_ORDER:
            logger.info("  %s: %s rows", table_name, count_rows(conn, table_name))
    finally:
        conn.close()


if __name__ == "__main__":
    main()