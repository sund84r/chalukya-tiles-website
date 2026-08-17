"""
Schema migrations for Chalukya Tiles (idempotent, data-safe).

Run from init_db() — never drops tables; adds columns/tables/indexes only.
Deduplicates customers/tiles before applying unique constraints.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from database.db import utc_now_iso


def normalize_phone(phone: str | None) -> str:
    """Digits-only phone (strip spaces, +, -, parentheses). Keep last 10–15 digits when long."""
    if not phone:
        return ""
    digits = re.sub(r"\D+", "", str(phone))
    if len(digits) > 15:
        digits = digits[-15:]
    return digits


def normalize_name(name: str | None) -> str:
    return " ".join((name or "").strip().lower().split())


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_col(conn: sqlite3.Connection, table: str, col: str, decl: str) -> None:
    if col not in _cols(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def migrate(conn: sqlite3.Connection) -> dict[str, Any]:
    """Apply all incremental migrations. Returns a short report."""
    report: dict[str, Any] = {"steps": []}

    # --- tiles: pattern for uniqueness (name + colour + pattern) ---
    if _table_exists(conn, "tiles"):
        _add_col(conn, "tiles", "pattern", "VARCHAR(120) NOT NULL DEFAULT ''")
        report["steps"].append("tiles.pattern")

    # --- inventory dimensions (tiles L×W + unit) ---
    if _table_exists(conn, "inventory_items"):
        _add_col(conn, "inventory_items", "dim_length", "REAL NULL")
        _add_col(conn, "inventory_items", "dim_width", "REAL NULL")
        _add_col(conn, "inventory_items", "dim_unit", "VARCHAR(20) NULL")
        report["steps"].append("inventory.dimensions")

    # --- customers: normalized keys ---
    if _table_exists(conn, "customers"):
        _add_col(conn, "customers", "phone_normalized", "VARCHAR(40) NOT NULL DEFAULT ''")
        _add_col(conn, "customers", "name_normalized", "VARCHAR(160) NOT NULL DEFAULT ''")
        rows = conn.execute("SELECT id, name, phone FROM customers").fetchall()
        for r in rows:
            conn.execute(
                "UPDATE customers SET phone_normalized = ?, name_normalized = ? WHERE id = ?",
                (normalize_phone(r["phone"]), normalize_name(r["name"]), r["id"]),
            )
        report["steps"].append("customers.normalized")

    # --- leads / queries: reminder fields ---
    for table in ("leads", "contact_messages", "enquiries"):
        if _table_exists(conn, table):
            _add_col(conn, table, "reminder_at", "TEXT NULL")
            _add_col(conn, table, "reminder_note", "TEXT NULL")
            _add_col(conn, table, "last_contact_channel", "VARCHAR(40) NULL")
            report["steps"].append(f"{table}.reminder_fields")

    # --- New tables ---
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS inventory_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            VARCHAR(200) NOT NULL,
            category        VARCHAR(80)  NOT NULL,
            brand           VARCHAR(120) NULL,
            sku             VARCHAR(100) NULL,
            description     TEXT         NULL,
            unit            VARCHAR(40)  NOT NULL DEFAULT 'pcs',
            quantity        REAL         NOT NULL DEFAULT 0,
            reorder_level   REAL         NOT NULL DEFAULT 0,
            purchase_price  REAL         NOT NULL DEFAULT 0,
            selling_price   REAL         NOT NULL DEFAULT 0,
            supplier        VARCHAR(160) NULL,
            tax_gst         REAL         NOT NULL DEFAULT 0,
            status          VARCHAR(40)  NOT NULL DEFAULT 'active',
            item_date       TEXT         NULL,
            notes           TEXT         NULL,
            image_path      VARCHAR(500) NULL,
            colour          VARCHAR(100) NULL,
            pattern         VARCHAR(120) NULL,
            show_on_website INTEGER      NOT NULL DEFAULT 0,
            material_category VARCHAR(100) NULL,
            size_label      VARCHAR(80)  NULL,
            finish          VARCHAR(80)  NULL,
            created_at      TEXT         NOT NULL,
            updated_at      TEXT         NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stock_movements (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id     INTEGER NOT NULL,
            movement    VARCHAR(20) NOT NULL,
            quantity    REAL NOT NULL,
            note        TEXT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (item_id) REFERENCES inventory_items(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS sales_returns (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            return_no       VARCHAR(80)  NOT NULL,
            original_invoice VARCHAR(80) NULL,
            customer_name   VARCHAR(160) NOT NULL,
            customer_phone  VARCHAR(40)  NULL,
            product_name    VARCHAR(200) NOT NULL,
            quantity        REAL         NOT NULL DEFAULT 1,
            amount          REAL         NOT NULL DEFAULT 0,
            return_date     TEXT         NOT NULL,
            reason          TEXT         NULL,
            status          VARCHAR(40)  NOT NULL DEFAULT 'completed',
            notes           TEXT         NULL,
            created_at      TEXT         NOT NULL
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_no     VARCHAR(80)  NOT NULL,
            supplier_name   VARCHAR(160) NOT NULL,
            supplier_phone  VARCHAR(40)  NULL,
            product_name    VARCHAR(200) NOT NULL,
            category        VARCHAR(80)  NULL,
            quantity        REAL         NOT NULL DEFAULT 1,
            amount          REAL         NOT NULL DEFAULT 0,
            purchase_date   TEXT         NOT NULL,
            status          VARCHAR(40)  NOT NULL DEFAULT 'received',
            notes           TEXT         NULL,
            inventory_id    INTEGER      NULL,
            created_at      TEXT         NOT NULL
        );

        CREATE TABLE IF NOT EXISTS communication_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type VARCHAR(40) NOT NULL,
            entity_id   INTEGER NOT NULL,
            channel     VARCHAR(40) NOT NULL,
            detail      TEXT NULL,
            created_at  TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory_items (category);
        CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory_items (sku);
        CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory_items (status);
        CREATE INDEX IF NOT EXISTS idx_stock_item ON stock_movements (item_id);
        CREATE INDEX IF NOT EXISTS idx_sales_returns_date ON sales_returns (return_date);
        CREATE INDEX IF NOT EXISTS idx_purchases_date ON purchases (purchase_date);
        CREATE INDEX IF NOT EXISTS idx_comm_entity ON communication_logs (entity_type, entity_id);

        CREATE TABLE IF NOT EXISTS app_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            level       VARCHAR(20)  NOT NULL DEFAULT 'INFO',
            source      VARCHAR(80)  NOT NULL DEFAULT 'app',
            message     TEXT         NOT NULL,
            detail      TEXT         NULL,
            created_at  TEXT         NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    VARCHAR(80)  NOT NULL,
            action      VARCHAR(120) NOT NULL,
            entity_type VARCHAR(80)  NULL,
            entity_id   INTEGER      NULL,
            detail      TEXT         NULL,
            ip          VARCHAR(60)  NULL,
            created_at  TEXT         NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_app_logs_created ON app_logs (created_at);
        CREATE INDEX IF NOT EXISTS idx_user_logs_created ON user_logs (created_at);

        CREATE TABLE IF NOT EXISTS concept_gallery (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        VARCHAR(200) NOT NULL,
            category     VARCHAR(40)  NOT NULL,
            image_path   VARCHAR(500) NOT NULL,
            description  TEXT         NULL,
            is_active    INTEGER      NOT NULL DEFAULT 1,
            sort_order   INTEGER      NOT NULL DEFAULT 0,
            created_at   TEXT         NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_concept_gallery_cat ON concept_gallery (category);
        CREATE INDEX IF NOT EXISTS idx_concept_gallery_active ON concept_gallery (is_active);

        CREATE TABLE IF NOT EXISTS reviews (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        VARCHAR(120) NOT NULL,
            email       VARCHAR(180) NULL,
            phone       VARCHAR(40)  NULL,
            rating      INTEGER      NOT NULL DEFAULT 5,
            title       VARCHAR(200) NULL,
            message     TEXT         NOT NULL,
            status      VARCHAR(40)  NOT NULL DEFAULT 'pending',
            is_featured INTEGER      NOT NULL DEFAULT 0,
            created_at  TEXT         NOT NULL,
            reviewed_at TEXT         NULL
        );

        CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews (status);
        CREATE INDEX IF NOT EXISTS idx_reviews_created ON reviews (created_at);
        """
    )
    report["steps"].append("new_tables")

    # --- Deduplicate customers (keep lowest id) ---
    if _table_exists(conn, "customers"):
        dups = conn.execute(
            """
            SELECT name_normalized, phone_normalized, MIN(id) AS keep_id, COUNT(*) AS c
            FROM customers
            WHERE phone_normalized != '' AND name_normalized != ''
            GROUP BY name_normalized, phone_normalized
            HAVING c > 1
            """
        ).fetchall()
        removed = 0
        for d in dups:
            conn.execute(
                """
                DELETE FROM customers
                WHERE name_normalized = ? AND phone_normalized = ? AND id != ?
                """,
                (d["name_normalized"], d["phone_normalized"], d["keep_id"]),
            )
            removed += d["c"] - 1
        report["customer_dups_removed"] = removed
        try:
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_name_phone
                ON customers (name_normalized, phone_normalized)
                """
            )
            report["steps"].append("uq_customers_name_phone")
        except sqlite3.IntegrityError:
            report["steps"].append("uq_customers_name_phone_SKIPPED")

    # --- Deduplicate tiles (name + colour + pattern) ---
    if _table_exists(conn, "tiles"):
        # Normalize empty pattern
        conn.execute("UPDATE tiles SET pattern = '' WHERE pattern IS NULL")
        dups = conn.execute(
            """
            SELECT lower(trim(name)) AS n, lower(trim(colour)) AS c,
                   lower(trim(pattern)) AS p, MIN(id) AS keep_id, COUNT(*) AS cnt
            FROM tiles
            GROUP BY n, c, p
            HAVING cnt > 1
            """
        ).fetchall()
        removed = 0
        for d in dups:
            conn.execute(
                """
                DELETE FROM tiles
                WHERE lower(trim(name)) = ? AND lower(trim(colour)) = ?
                  AND lower(trim(COALESCE(pattern,''))) = ? AND id != ?
                """,
                (d["n"], d["c"], d["p"], d["keep_id"]),
            )
            removed += d["cnt"] - 1
        report["tile_dups_removed"] = removed
        try:
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_tiles_name_colour_pattern
                ON tiles (name, colour, pattern)
                """
            )
            report["steps"].append("uq_tiles_name_colour_pattern")
        except sqlite3.IntegrityError:
            report["steps"].append("uq_tiles_name_colour_pattern_SKIPPED")

    report["migrated_at"] = utc_now_iso()
    return report
