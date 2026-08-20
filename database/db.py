"""
SQLite database layer for Chalukya Tiles showroom.

Design notes for MySQL migration:
- Standard column types and explicit PRIMARY KEYs
- TIMESTAMP-style strings (ISO 8601) stored as TEXT for SQLite;
  use DATETIME on MySQL without changing application field names
- Connection helpers are isolated; swap get_connection() for MySQL later
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATABASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = DATABASE_DIR / "showroom.db"
BASE_DIR = DATABASE_DIR.parent
UPLOAD_TILES_DIR = BASE_DIR / "static" / "uploads" / "tiles"
UPLOAD_VIDEOS_DIR = BASE_DIR / "static" / "uploads" / "videos"
UPLOAD_POSTERS_DIR = BASE_DIR / "static" / "uploads" / "posters"
UPLOAD_INVENTORY_DIR = BASE_DIR / "static" / "uploads" / "inventory"
UPLOAD_GALLERY_DIR = BASE_DIR / "static" / "uploads" / "gallery"

CONCEPT_GALLERY_CATEGORIES = (
    ("living", "Living Room"),
    ("bathroom", "Bathroom"),
    ("parking", "Parking"),
    ("elevation", "Elevation"),
    ("outdoor", "Outdoor"),
)

INVENTORY_CATEGORIES = (
    "Tiles",
    "Paste",
    "Adhesive",
    "Sanitary Wares",
    "Beading",
    "Others",
)

INVENTORY_UNITS = ("pieces", "kg", "litre", "grams", "box", "bag", "set")
TILE_DIM_UNITS = ("mm", "cm", "inches", "ft")

# Suggested under-categories for each main inventory category (admin + products filters)
INVENTORY_SUBCATEGORIES: dict[str, tuple[str, ...]] = {
    "Tiles": (
        "Vitrified Tiles",
        "Ceramic Tiles",
        "Parking Tiles",
        "Outdoor Tiles",
        "Wooden Finish",
        "Marble Finish",
        "Bathroom Tiles",
        "Kitchen Tiles",
        "Elevation Tiles",
    ),
    "Paste": (
        "Wall Paste",
        "Floor Paste",
        "Waterproofing Paste",
        "Joint Filler",
    ),
    "Adhesive": (
        "Tile Adhesive",
        "Epoxy Adhesive",
        "Cement Adhesive",
        "Stone Adhesive",
    ),
    "Sanitary Wares": (
        "Pipes",
        "Showers",
        "Sinks",
        "Closets",
        "Faucets",
        "Accessories",
    ),
    "Beading": (
        "Corner Beading",
        "Edge Beading",
        "Transition Profiles",
        "Skirting",
    ),
    "Others": (
        "General",
        "Tools",
        "Accessories",
    ),
}

# Default admin (override with env ADMIN_USERNAME / ADMIN_PASSWORD)
DEFAULT_ADMIN_USER = os.environ.get("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "chalukya@2026")

# Admin panel permission keys (checkbox modules). Superadmin bypasses these.
ADMIN_PERMISSION_MODULES: list[tuple[str, str]] = [
    ("dashboard", "Overview & stats"),
    ("inv-overview", "Inventory overview"),
    ("sales", "Sales"),
    ("sales-returns", "Sales Return"),
    ("purchases", "Purchase"),
    ("leads", "Leads"),
    ("queries", "Queries"),
    ("customers", "Customer Details"),
    ("reviews", "Reviews & Ratings"),
    ("inventory", "Inventory / Stock"),
    ("inventory-add", "Add Inventory"),
    ("tiles", "New Arrivals"),
    ("videos", "Collection Videos"),
    ("concept-gallery", "Concept Gallery"),
    ("data-tools", "Backup / Export / Import"),
    ("app-logs", "Application Logs"),
    ("user-logs", "User Logs"),
]

ADMIN_PERMISSION_KEYS = [k for k, _ in ADMIN_PERMISSION_MODULES]


def utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string (MySQL-friendly)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """PBKDF2-SHA256 password hash as salt$hash hex."""
    if salt is None:
        salt = secrets.token_hex(16)
    dig = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    )
    return f"{salt}${dig.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify password against stored salt$hash."""
    try:
        salt, _hex = stored.split("$", 1)
    except ValueError:
        return False
    candidate = hash_password(password, salt=salt)
    return hmac.compare_digest(candidate, stored)


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """
    Open a SQLite connection with sensible defaults.

    For MySQL later: replace this function to return a MySQL connection
    that still supports .execute() / .commit() / context managers, or
    introduce a thin adapter around the same interface.
    """
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager that commits on success and closes the connection."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
-- Contact form submissions (general inquiries / queries)
CREATE TABLE IF NOT EXISTS contact_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(120)  NOT NULL,
    phone       VARCHAR(40)   NOT NULL,
    email       VARCHAR(180)  NOT NULL,
    message     TEXT          NOT NULL,
    created_at  TEXT          NOT NULL,
    status      VARCHAR(40)   NOT NULL DEFAULT 'new'
);

-- Product / showroom enquiry submissions (queries)
CREATE TABLE IF NOT EXISTS enquiries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            VARCHAR(120)  NOT NULL,
    phone           VARCHAR(40)   NOT NULL,
    email           VARCHAR(180)  NOT NULL,
    message         TEXT          NOT NULL,
    product_name    VARCHAR(200)  NULL,
    product_category VARCHAR(100) NULL,
    created_at      TEXT          NOT NULL,
    status          VARCHAR(40)   NOT NULL DEFAULT 'new'
);

-- Admin users (role + permissions JSON added via migrate)
CREATE TABLE IF NOT EXISTS admin_users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      VARCHAR(80)  NOT NULL UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    role          VARCHAR(40)  NOT NULL DEFAULT 'user',
    is_active     INTEGER      NOT NULL DEFAULT 1,
    permissions   TEXT         NOT NULL DEFAULT '{}',
    created_at    TEXT         NOT NULL,
    updated_at    TEXT         NULL
);

-- Tile media catalogue (admin uploads)
CREATE TABLE IF NOT EXISTS tiles (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               VARCHAR(200) NOT NULL,
    model_number       VARCHAR(100) NOT NULL,
    colour             VARCHAR(100) NOT NULL,
    material_category  VARCHAR(100) NOT NULL,
    image_path         VARCHAR(500) NOT NULL,
    description        TEXT         NULL,
    size_label         VARCHAR(80)  NULL,
    finish             VARCHAR(80)  NULL,
    is_active          INTEGER      NOT NULL DEFAULT 1,
    created_at         TEXT         NOT NULL,
    updated_at         TEXT         NOT NULL
);

-- Collection / hero-mid videos
CREATE TABLE IF NOT EXISTS collection_videos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        VARCHAR(200) NOT NULL,
    description  TEXT         NULL,
    video_path   VARCHAR(500) NOT NULL,
    poster_path  VARCHAR(500) NULL,
    is_active    INTEGER      NOT NULL DEFAULT 1,
    sort_order   INTEGER      NOT NULL DEFAULT 0,
    created_at   TEXT         NOT NULL
);

-- Sales records
CREATE TABLE IF NOT EXISTS sales (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no      VARCHAR(80)  NOT NULL,
    customer_name   VARCHAR(160) NOT NULL,
    customer_phone  VARCHAR(40)  NULL,
    product_name    VARCHAR(200) NOT NULL,
    quantity        REAL         NOT NULL DEFAULT 1,
    amount          REAL         NOT NULL DEFAULT 0,
    sale_date       TEXT         NOT NULL,
    status          VARCHAR(40)  NOT NULL DEFAULT 'completed',
    notes           TEXT         NULL,
    created_at      TEXT         NOT NULL
);

-- Sales leads
CREATE TABLE IF NOT EXISTS leads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(160) NOT NULL,
    phone       VARCHAR(40)  NOT NULL,
    email       VARCHAR(180) NULL,
    source      VARCHAR(100) NULL,
    interest    VARCHAR(200) NULL,
    status      VARCHAR(40)  NOT NULL DEFAULT 'new',
    notes       TEXT         NULL,
    created_at  TEXT         NOT NULL
);

-- Customer master data
CREATE TABLE IF NOT EXISTS customers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(160) NOT NULL,
    phone       VARCHAR(40)  NOT NULL,
    email       VARCHAR(180) NULL,
    address     TEXT         NULL,
    city        VARCHAR(100) NULL,
    notes       TEXT         NULL,
    created_at  TEXT         NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contact_messages_created_at
    ON contact_messages (created_at);
CREATE INDEX IF NOT EXISTS idx_enquiries_created_at
    ON enquiries (created_at);
CREATE INDEX IF NOT EXISTS idx_tiles_category
    ON tiles (material_category);
CREATE INDEX IF NOT EXISTS idx_tiles_model
    ON tiles (model_number);
CREATE INDEX IF NOT EXISTS idx_sales_date
    ON sales (sale_date);
CREATE INDEX IF NOT EXISTS idx_leads_status
    ON leads (status);
CREATE INDEX IF NOT EXISTS idx_customers_phone
    ON customers (phone);
CREATE INDEX IF NOT EXISTS idx_collection_videos_sort
    ON collection_videos (sort_order);
"""


def ensure_upload_dirs() -> None:
    """Create upload directories used by the admin media panel."""
    for path in (
        UPLOAD_TILES_DIR,
        UPLOAD_VIDEOS_DIR,
        UPLOAD_POSTERS_DIR,
        UPLOAD_INVENTORY_DIR,
        UPLOAD_GALLERY_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _seed_admin(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT id FROM admin_users WHERE username = ?", (DEFAULT_ADMIN_USER,)).fetchone()
    if row:
        conn.execute(
            """
            UPDATE admin_users
            SET role = 'superadmin', is_active = 1
            WHERE id = ?
            """,
            (row["id"],),
        )
        return
    now = utc_now_iso()
    conn.execute(
        """
        INSERT INTO admin_users (
            username, password_hash, role, is_active, permissions, created_at, updated_at
        ) VALUES (?, ?, 'superadmin', 1, '{}', ?, ?)
        """,
        (DEFAULT_ADMIN_USER, hash_password(DEFAULT_ADMIN_PASS), now, now),
    )


def _seed_demo_analytics(conn: sqlite3.Connection) -> None:
    """Seed sample sales/leads/customers once so the dashboard is not empty."""
    sales_count = conn.execute("SELECT COUNT(*) AS c FROM sales").fetchone()["c"]
    if sales_count == 0:
        now = utc_now_iso()
        samples = [
            ("INV-1001", "Ravi Kumar", "9876543210", "Carrara Luxe", 120, 54000, "2026-07-01", "completed"),
            ("INV-1002", "Anitha S", "9876501234", "Oak Heritage", 80, 36000, "2026-07-12", "completed"),
            ("INV-1003", "Green Homes Pvt", "9842011122", "Noir Graphite", 200, 88000, "2026-07-28", "completed"),
            ("INV-1004", "Priya M", "9003112233", "Spa Mist Bath", 60, 21000, "2026-08-02", "pending"),
            ("INV-1005", "Suresh Builders", "9940718307", "Facade Luxe", 150, 67500, "2026-08-05", "completed"),
        ]
        for inv, name, phone, product, qty, amount, date, status in samples:
            conn.execute(
                """
                INSERT INTO sales (
                    invoice_no, customer_name, customer_phone, product_name,
                    quantity, amount, sale_date, status, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (inv, name, phone, product, qty, amount, date, status, None, now),
            )

    leads_count = conn.execute("SELECT COUNT(*) AS c FROM leads").fetchone()["c"]
    if leads_count == 0:
        now = utc_now_iso()
        leads = [
            ("Karthik R", "9811122233", "karthik@email.com", "Website", "Marble Finish", "new"),
            ("Meena L", "9822233344", "meena@email.com", "WhatsApp", "Bathroom Tiles", "contacted"),
            ("Hotel Peak", "9833344455", "purchase@hotelpeak.in", "Walk-in", "Vitrified Tiles", "qualified"),
            ("Deepak N", "9844455566", None, "Phone", "Outdoor Tiles", "new"),
        ]
        for name, phone, email, source, interest, status in leads:
            conn.execute(
                """
                INSERT INTO leads (
                    name, phone, email, source, interest, status, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, phone, email, source, interest, status, None, now),
            )

    cust_count = conn.execute("SELECT COUNT(*) AS c FROM customers").fetchone()["c"]
    if cust_count == 0:
        from database.migrate import normalize_name, normalize_phone

        now = utc_now_iso()
        customers = [
            ("Ravi Kumar", "9876543210", "ravi@email.com", "RS Puram", "Coimbatore"),
            ("Anitha S", "9876501234", "anitha@email.com", "Peelamedu", "Coimbatore"),
            ("Green Homes Pvt", "9842011122", "ops@greenhomes.in", "Sathy Road", "Coimbatore"),
            ("Suresh Builders", "9940718307", "suresh@builders.in", "Kurumbapalayam", "Coimbatore"),
        ]
        for name, phone, email, address, city in customers:
            try:
                conn.execute(
                    """
                    INSERT INTO customers (
                        name, phone, phone_normalized, name_normalized,
                        email, address, city, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        phone,
                        normalize_phone(phone),
                        normalize_name(name),
                        email,
                        address,
                        city,
                        None,
                        now,
                    ),
                )
            except sqlite3.IntegrityError:
                # Unique index already has this demo row — skip safely
                continue


def init_db() -> None:
    """Create tables, indexes, upload dirs, migrate, and seed defaults."""
    ensure_upload_dirs()
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
        from database.migrate import migrate

        migrate(conn)
        _seed_admin(conn)
        # Never inject demo CRM rows on a live host
        env = os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "development")).strip().lower()
        if env not in {"production", "prod", "live"}:
            _seed_demo_analytics(conn)


# ---------------------------------------------------------------------------
# Admin auth + user management
# ---------------------------------------------------------------------------

def _parse_permissions(raw: Any) -> dict[str, int]:
    import json

    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(raw or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            data = {}
    out: dict[str, int] = {}
    for key in ADMIN_PERMISSION_KEYS:
        out[key] = 1 if int(data.get(key) or 0) == 1 else 0
    return out


def _serialize_permissions(perms: Optional[dict[str, Any]]) -> str:
    import json

    clean = _parse_permissions(perms or {})
    return json.dumps(clean)


def _admin_row_to_dict(row: Any, *, include_hash: bool = False) -> dict[str, Any]:
    role = (row["role"] if "role" in row.keys() else "user") or "user"
    is_super = role == "superadmin"
    perms = _parse_permissions(row["permissions"] if "permissions" in row.keys() else "{}")
    if is_super:
        perms = {k: 1 for k in ADMIN_PERMISSION_KEYS}
    data = {
        "id": int(row["id"]),
        "username": row["username"],
        "role": role,
        "is_superadmin": is_super,
        "is_active": int(row["is_active"] if "is_active" in row.keys() else 1),
        "permissions": perms,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"] if "updated_at" in row.keys() else None,
    }
    if include_hash:
        data["password_hash"] = row["password_hash"]
    return data


def get_admin_user(user_id: int) -> Optional[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM admin_users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        return None
    return _admin_row_to_dict(row)


def get_admin_user_by_username(username: str) -> Optional[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM admin_users WHERE lower(username) = lower(?)",
            (username.strip(),),
        ).fetchone()
    if not row:
        return None
    return _admin_row_to_dict(row)


def authenticate_admin(username: str, password: str) -> Optional[dict[str, Any]]:
    """Return admin user dict if credentials match, else None."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM admin_users WHERE lower(username) = lower(?)",
            (username.strip(),),
        ).fetchone()
    if not row:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    user = _admin_row_to_dict(row)
    if not user.get("is_active"):
        return None
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "is_superadmin": user["is_superadmin"],
        "permissions": user["permissions"],
    }


def list_admin_users() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM admin_users ORDER BY role DESC, username ASC"
        ).fetchall()
    return [_admin_row_to_dict(r) for r in rows]


def create_admin_user(
    *,
    username: str,
    password: str,
    permissions: Optional[dict[str, Any]] = None,
    role: str = "user",
) -> int:
    uname = username.strip()
    if not uname:
        raise ValueError("Username required")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    role = "superadmin" if role == "superadmin" else "user"
    now = utc_now_iso()
    with get_db() as conn:
        exists = conn.execute(
            "SELECT id FROM admin_users WHERE lower(username) = lower(?)",
            (uname,),
        ).fetchone()
        if exists:
            raise ValueError("Username already exists")
        cur = conn.execute(
            """
            INSERT INTO admin_users (
                username, password_hash, role, is_active, permissions, created_at, updated_at
            ) VALUES (?, ?, ?, 1, ?, ?, ?)
            """,
            (
                uname,
                hash_password(password),
                role,
                "{}" if role == "superadmin" else _serialize_permissions(permissions),
                now,
                now,
            ),
        )
        return int(cur.lastrowid)


def update_admin_user(user_id: int, **fields: Any) -> bool:
    allowed = {"password", "permissions", "is_active", "role"}
    updates: dict[str, Any] = {}
    for key, val in fields.items():
        if key not in allowed or val is None:
            continue
        if key == "password":
            if len(str(val)) < 6:
                raise ValueError("Password must be at least 6 characters")
            updates["password_hash"] = hash_password(str(val))
        elif key == "permissions":
            updates["permissions"] = _serialize_permissions(val)
        elif key == "is_active":
            updates["is_active"] = 1 if int(val) == 1 else 0
        elif key == "role":
            updates["role"] = "superadmin" if val == "superadmin" else "user"
            if updates["role"] == "superadmin":
                updates["permissions"] = "{}"
    if not updates:
        return False
    updates["updated_at"] = utc_now_iso()
    cols = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]
    with get_db() as conn:
        cur = conn.execute(f"UPDATE admin_users SET {cols} WHERE id = ?", values)
        return cur.rowcount > 0


def delete_admin_user(user_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, role FROM admin_users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row:
            return False
        if row["role"] == "superadmin":
            count = conn.execute(
                "SELECT COUNT(*) AS c FROM admin_users WHERE role = 'superadmin'"
            ).fetchone()["c"]
            if int(count) <= 1:
                raise ValueError("Cannot delete the last superadmin")
        cur = conn.execute("DELETE FROM admin_users WHERE id = ?", (user_id,))
        return cur.rowcount > 0


def user_has_permission(user: dict[str, Any], *modules: str) -> bool:
    if user.get("is_superadmin") or user.get("role") == "superadmin":
        return True
    perms = user.get("permissions") or {}
    return any(int(perms.get(m) or 0) == 1 for m in modules)


# ---------------------------------------------------------------------------
# Contact messages
# ---------------------------------------------------------------------------

def insert_contact_message(
    *,
    name: str,
    phone: str,
    email: str,
    message: str,
) -> int:
    created_at = utc_now_iso()
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO contact_messages (name, phone, email, message, created_at, status)
            VALUES (?, ?, ?, ?, ?, 'new')
            """,
            (name, phone, email, message, created_at),
        )
        return int(cursor.lastrowid)


def list_contact_messages(limit: int = 200) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, name, phone, email, message, created_at, status,
                   reminder_at, reminder_note, last_contact_channel
            FROM contact_messages
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_contact_status(row_id: int, status: str) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE contact_messages SET status = ? WHERE id = ?",
            (status, row_id),
        )
        return cur.rowcount > 0


def delete_contact_message(row_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM contact_messages WHERE id = ?", (row_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Enquiries
# ---------------------------------------------------------------------------

def insert_enquiry(
    *,
    name: str,
    phone: str,
    email: str,
    message: str,
    product_name: Optional[str] = None,
    product_category: Optional[str] = None,
) -> int:
    created_at = utc_now_iso()
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO enquiries (
                name, phone, email, message,
                product_name, product_category, created_at, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'new')
            """,
            (
                name,
                phone,
                email,
                message,
                product_name,
                product_category,
                created_at,
            ),
        )
        return int(cursor.lastrowid)


def list_enquiries(limit: int = 200) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                id, name, phone, email, message,
                product_name, product_category, created_at, status,
                reminder_at, reminder_note, last_contact_channel
            FROM enquiries
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_enquiry_status(row_id: int, status: str) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE enquiries SET status = ? WHERE id = ?",
            (status, row_id),
        )
        return cur.rowcount > 0


def delete_enquiry(row_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM enquiries WHERE id = ?", (row_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Tiles (media catalogue)
# ---------------------------------------------------------------------------

class DuplicateError(Exception):
    """Raised when a unique business key already exists."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def find_tile_duplicate(
    name: str,
    colour: str,
    pattern: str = "",
    exclude_id: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    name = (name or "").strip()
    colour = (colour or "").strip()
    pattern = (pattern or "").strip()
    sql = """
        SELECT id, name, colour, pattern FROM tiles
        WHERE lower(trim(name)) = lower(trim(?))
          AND lower(trim(colour)) = lower(trim(?))
          AND lower(trim(COALESCE(pattern,''))) = lower(trim(?))
    """
    params: list[Any] = [name, colour, pattern]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    with get_db() as conn:
        row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def insert_tile(
    *,
    name: str,
    model_number: str,
    colour: str,
    material_category: str,
    image_path: str,
    description: Optional[str] = None,
    size_label: Optional[str] = None,
    finish: Optional[str] = None,
    pattern: str = "",
) -> int:
    name = name.strip()
    colour = colour.strip()
    pattern = (pattern or "").strip()
    if find_tile_duplicate(name, colour, pattern):
        raise DuplicateError(
            f"Tile already exists: '{name}' / colour '{colour}' / pattern '{pattern or '—'}'"
        )
    now = utc_now_iso()
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO tiles (
                name, model_number, colour, pattern, material_category, image_path,
                description, size_label, finish, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                name,
                model_number,
                colour,
                pattern,
                material_category,
                image_path,
                description,
                size_label,
                finish,
                now,
                now,
            ),
        )
        return int(cur.lastrowid)


def list_tiles(active_only: bool = False, limit: int = 500) -> list[dict[str, Any]]:
    sql = """
        SELECT id, name, model_number, colour, pattern, material_category, image_path,
               description, size_label, finish, is_active, created_at, updated_at
        FROM tiles
    """
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY id DESC LIMIT ?"
    with get_db() as conn:
        rows = conn.execute(sql, (limit,)).fetchall()
    return [dict(row) for row in rows]


def get_tile(tile_id: int) -> Optional[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, name, model_number, colour, pattern, material_category, image_path,
                   description, size_label, finish, is_active, created_at, updated_at
            FROM tiles WHERE id = ?
            """,
            (tile_id,),
        ).fetchone()
    return dict(row) if row else None


def update_tile(tile_id: int, **fields: Any) -> bool:
    allowed = {
        "name",
        "model_number",
        "colour",
        "pattern",
        "material_category",
        "image_path",
        "description",
        "size_label",
        "finish",
        "is_active",
    }
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    # Duplicate check when key fields change
    current = get_tile(tile_id)
    if not current:
        return False
    n = updates.get("name", current["name"])
    c = updates.get("colour", current["colour"])
    p = updates.get("pattern", current.get("pattern") or "")
    if find_tile_duplicate(str(n), str(c), str(p), exclude_id=tile_id):
        raise DuplicateError(
            f"Tile already exists: '{n}' / colour '{c}' / pattern '{p or '—'}'"
        )
    updates["updated_at"] = utc_now_iso()
    cols = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [tile_id]
    with get_db() as conn:
        cur = conn.execute(f"UPDATE tiles SET {cols} WHERE id = ?", values)
        return cur.rowcount > 0


def delete_tile(tile_id: int) -> Optional[str]:
    """Delete tile; return image_path so caller can remove file."""
    with get_db() as conn:
        row = conn.execute("SELECT image_path FROM tiles WHERE id = ?", (tile_id,)).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM tiles WHERE id = ?", (tile_id,))
        return row["image_path"]


# ---------------------------------------------------------------------------
# Collection videos
# ---------------------------------------------------------------------------

def insert_collection_video(
    *,
    title: str,
    video_path: str,
    description: Optional[str] = None,
    poster_path: Optional[str] = None,
    sort_order: int = 0,
    is_active: int = 1,
) -> int:
    now = utc_now_iso()
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO collection_videos (
                title, description, video_path, poster_path, is_active, sort_order, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, description, video_path, poster_path, is_active, sort_order, now),
        )
        return int(cur.lastrowid)


# ---------------------------------------------------------------------------
# Concept Gallery images (public /gallery)
# ---------------------------------------------------------------------------

def insert_concept_gallery(
    *,
    title: str,
    category: str,
    image_path: str,
    description: Optional[str] = None,
    sort_order: int = 0,
    is_active: int = 1,
) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO concept_gallery (
                title, category, image_path, description, is_active, sort_order, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title.strip(),
                category.strip().lower(),
                image_path,
                description,
                is_active,
                sort_order,
                utc_now_iso(),
            ),
        )
        return int(cur.lastrowid)


def list_concept_gallery(
    active_only: bool = False,
    category: Optional[str] = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    sql = """
        SELECT id, title, category, image_path, description, is_active, sort_order, created_at
        FROM concept_gallery
        WHERE 1=1
    """
    params: list[Any] = []
    if active_only:
        sql += " AND is_active = 1"
    if category and category != "all":
        sql += " AND category = ?"
        params.append(category.strip().lower())
    sql += " ORDER BY sort_order ASC, id DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_concept_gallery(item_id: int) -> Optional[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM concept_gallery WHERE id = ?", (item_id,)
        ).fetchone()
    return dict(row) if row else None


def update_concept_gallery(item_id: int, **fields: Any) -> bool:
    allowed = {
        "title",
        "category",
        "image_path",
        "description",
        "is_active",
        "sort_order",
    }
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    cols = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [item_id]
    with get_db() as conn:
        cur = conn.execute(
            f"UPDATE concept_gallery SET {cols} WHERE id = ?", values
        )
        return cur.rowcount > 0


def delete_concept_gallery(item_id: int) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT image_path FROM concept_gallery WHERE id = ?", (item_id,)
        ).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM concept_gallery WHERE id = ?", (item_id,))
        return row["image_path"]


def list_collection_videos(active_only: bool = False, limit: int = 50) -> list[dict[str, Any]]:
    sql = """
        SELECT id, title, description, video_path, poster_path, is_active, sort_order, created_at
        FROM collection_videos
    """
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY sort_order ASC, id DESC LIMIT ?"
    with get_db() as conn:
        rows = conn.execute(sql, (limit,)).fetchall()
    return [dict(row) for row in rows]


def get_collection_video(video_id: int) -> Optional[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, title, description, video_path, poster_path, is_active, sort_order, created_at
            FROM collection_videos WHERE id = ?
            """,
            (video_id,),
        ).fetchone()
    return dict(row) if row else None


def update_collection_video(video_id: int, **fields: Any) -> bool:
    allowed = {
        "title",
        "description",
        "video_path",
        "poster_path",
        "is_active",
        "sort_order",
    }
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    cols = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [video_id]
    with get_db() as conn:
        cur = conn.execute(
            f"UPDATE collection_videos SET {cols} WHERE id = ?",
            values,
        )
        return cur.rowcount > 0


def delete_collection_video(video_id: int) -> Optional[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT video_path, poster_path FROM collection_videos WHERE id = ?",
            (video_id,),
        ).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM collection_videos WHERE id = ?", (video_id,))
        return dict(row)


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------

def insert_sale(
    *,
    invoice_no: str,
    customer_name: str,
    product_name: str,
    quantity: float,
    amount: float,
    sale_date: str,
    customer_phone: Optional[str] = None,
    status: str = "completed",
    notes: Optional[str] = None,
) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO sales (
                invoice_no, customer_name, customer_phone, product_name,
                quantity, amount, sale_date, status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_no,
                customer_name,
                customer_phone,
                product_name,
                quantity,
                amount,
                sale_date,
                status,
                notes,
                utc_now_iso(),
            ),
        )
        return int(cur.lastrowid)


def list_sales(limit: int = 200) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, invoice_no, customer_name, customer_phone, product_name,
                   quantity, amount, sale_date, status, notes, created_at
            FROM sales
            ORDER BY sale_date DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_sale(row_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM sales WHERE id = ?", (row_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------

def insert_lead(
    *,
    name: str,
    phone: str,
    email: Optional[str] = None,
    source: Optional[str] = None,
    interest: Optional[str] = None,
    status: str = "new",
    notes: Optional[str] = None,
) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO leads (
                name, phone, email, source, interest, status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, phone, email, source, interest, status, notes, utc_now_iso()),
        )
        return int(cur.lastrowid)


def list_leads(limit: int = 200) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, name, phone, email, source, interest, status, notes,
                   reminder_at, reminder_note, last_contact_channel, created_at
            FROM leads
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_lead(row_id: int, **fields: Any) -> bool:
    allowed = {
        "name",
        "phone",
        "email",
        "source",
        "interest",
        "status",
        "notes",
        "reminder_at",
        "reminder_note",
        "last_contact_channel",
    }
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    cols = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [row_id]
    with get_db() as conn:
        cur = conn.execute(f"UPDATE leads SET {cols} WHERE id = ?", values)
        return cur.rowcount > 0


def delete_lead(row_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM leads WHERE id = ?", (row_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

def find_customer_duplicate(
    name: str,
    phone: str,
    exclude_id: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    from database.migrate import normalize_name, normalize_phone

    nn = normalize_name(name)
    np = normalize_phone(phone)
    if not nn or not np:
        return None
    sql = """
        SELECT id, name, phone FROM customers
        WHERE name_normalized = ? AND phone_normalized = ?
    """
    params: list[Any] = [nn, np]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    with get_db() as conn:
        row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def insert_customer(
    *,
    name: str,
    phone: str,
    email: Optional[str] = None,
    address: Optional[str] = None,
    city: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    from database.migrate import normalize_name, normalize_phone

    name = name.strip()
    phone = phone.strip()
    if find_customer_duplicate(name, phone):
        raise DuplicateError(
            f"Customer already exists: '{name}' with phone '{phone}'"
        )
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO customers (
                name, phone, phone_normalized, name_normalized,
                email, address, city, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                phone,
                normalize_phone(phone),
                normalize_name(name),
                email,
                address,
                city,
                notes,
                utc_now_iso(),
            ),
        )
        return int(cur.lastrowid)


def list_customers(limit: int = 200) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, name, phone, phone_normalized, name_normalized,
                   email, address, city, notes, created_at
            FROM customers
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_customer(row_id: int, **fields: Any) -> bool:
    from database.migrate import normalize_name, normalize_phone

    allowed = {"name", "phone", "email", "address", "city", "notes"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    current = None
    with get_db() as conn:
        current = conn.execute(
            "SELECT id, name, phone FROM customers WHERE id = ?", (row_id,)
        ).fetchone()
    if not current:
        return False
    n = updates.get("name", current["name"])
    p = updates.get("phone", current["phone"])
    if find_customer_duplicate(str(n), str(p), exclude_id=row_id):
        raise DuplicateError(f"Customer already exists: '{n}' with phone '{p}'")
    if "name" in updates:
        updates["name_normalized"] = normalize_name(str(updates["name"]))
    if "phone" in updates:
        updates["phone_normalized"] = normalize_phone(str(updates["phone"]))
    cols = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [row_id]
    with get_db() as conn:
        cur = conn.execute(f"UPDATE customers SET {cols} WHERE id = ?", values)
        return cur.rowcount > 0


def delete_customer(row_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM customers WHERE id = ?", (row_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Dashboard analytics
# ---------------------------------------------------------------------------

def get_dashboard_stats() -> dict[str, Any]:
    with get_db() as conn:
        def count(table: str, where: str = "") -> int:
            sql = f"SELECT COUNT(*) AS c FROM {table}"
            if where:
                sql += f" WHERE {where}"
            return int(conn.execute(sql).fetchone()["c"])

        sales_sum = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM sales WHERE status != 'cancelled'"
        ).fetchone()["total"]
        sales_month = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total FROM sales
            WHERE status != 'cancelled'
              AND sale_date >= date('now', 'start of month')
            """
        ).fetchone()["total"]
        recent_sales = conn.execute(
            """
            SELECT sale_date AS d, COALESCE(SUM(amount), 0) AS total
            FROM sales
            WHERE status != 'cancelled'
            GROUP BY sale_date
            ORDER BY sale_date DESC
            LIMIT 7
            """
        ).fetchall()

        contact_count = count("contact_messages")
        contact_new = count("contact_messages", "status = 'new'")
        enquiry_count = count("enquiries")
        enquiry_new = count("enquiries", "status = 'new'")

        inv_count = 0
        low_stock = 0
        purchase_sum = 0.0
        returns_sum = 0.0
        try:
            inv_count = count("inventory_items")
            low_stock = int(
                conn.execute(
                    """
                    SELECT COUNT(*) AS c FROM inventory_items
                    WHERE status = 'active' AND quantity <= reorder_level
                    """
                ).fetchone()["c"]
            )
            purchase_sum = float(
                conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) AS t FROM purchases"
                ).fetchone()["t"]
                or 0
            )
            returns_sum = float(
                conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) AS t FROM sales_returns"
                ).fetchone()["t"]
                or 0
            )
        except Exception:
            pass

        reminders_pending = 0
        reminders_overdue = 0
        try:
            now = utc_now_iso()
            for table in ("leads", "contact_messages", "enquiries"):
                reminders_pending += int(
                    conn.execute(
                        f"SELECT COUNT(*) AS c FROM {table} WHERE reminder_at IS NOT NULL AND reminder_at >= ?",
                        (now,),
                    ).fetchone()["c"]
                )
                reminders_overdue += int(
                    conn.execute(
                        f"SELECT COUNT(*) AS c FROM {table} WHERE reminder_at IS NOT NULL AND reminder_at < ?",
                        (now,),
                    ).fetchone()["c"]
                )
        except Exception:
            pass

        return {
            "tiles": count("tiles"),
            "tiles_active": count("tiles", "is_active = 1"),
            "videos": count("collection_videos"),
            "videos_active": count("collection_videos", "is_active = 1"),
            "sales_count": count("sales"),
            "sales_total": float(sales_sum or 0),
            "sales_month": float(sales_month or 0),
            "leads": count("leads"),
            "leads_new": count("leads", "status = 'new'"),
            "customers": count("customers"),
            "contact_messages": contact_count,
            "contact_new": contact_new,
            "enquiries": enquiry_count,
            "enquiries_new": enquiry_new,
            "queries_total": contact_count + enquiry_count,
            "queries_new": contact_new + enquiry_new,
            "inventory_count": inv_count,
            "low_stock": low_stock,
            "purchases_total": purchase_sum,
            "returns_total": returns_sum,
            "reminders_pending": reminders_pending,
            "reminders_overdue": reminders_overdue,
            "sales_by_day": [
                {"date": r["d"], "total": float(r["total"])} for r in recent_sales
            ],
        }


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

def insert_inventory_item(**fields: Any) -> int:
    now = utc_now_iso()
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO inventory_items (
                name, category, brand, sku, description, unit, quantity, reorder_level,
                purchase_price, selling_price, supplier, tax_gst, status, item_date, notes,
                image_path, colour, pattern, show_on_website, material_category, size_label,
                finish, dim_length, dim_width, dim_unit, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                fields.get("name"),
                fields.get("category"),
                fields.get("brand"),
                fields.get("sku"),
                fields.get("description"),
                fields.get("unit") or "pieces",
                float(fields.get("quantity") or 0),
                float(fields.get("reorder_level") or 0),
                float(fields.get("purchase_price") or 0),
                float(fields.get("selling_price") or 0),
                fields.get("supplier"),
                float(fields.get("tax_gst") or 0),
                fields.get("status") or "active",
                fields.get("item_date"),
                fields.get("notes"),
                fields.get("image_path"),
                fields.get("colour"),
                fields.get("pattern") or "",
                int(fields.get("show_on_website") or 0),
                fields.get("material_category"),
                fields.get("size_label"),
                fields.get("finish"),
                fields.get("dim_length"),
                fields.get("dim_width"),
                fields.get("dim_unit"),
                now,
                now,
            ),
        )
        item_id = int(cur.lastrowid)
        qty = float(fields.get("quantity") or 0)
        if qty:
            conn.execute(
                """
                INSERT INTO stock_movements (item_id, movement, quantity, note, created_at)
                VALUES (?, 'in', ?, 'Opening stock', ?)
                """,
                (item_id, qty, now),
            )
        return item_id


def list_inventory(
    category: Optional[str] = None,
    q: Optional[str] = None,
    low_stock_only: bool = False,
    limit: int = 500,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM inventory_items WHERE 1=1"
    params: list[Any] = []
    if category and category != "all":
        sql += " AND category = ?"
        params.append(category)
    if q:
        sql += " AND (name LIKE ? OR sku LIKE ? OR brand LIKE ? OR supplier LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like, like])
    if low_stock_only:
        sql += " AND status = 'active' AND quantity <= reorder_level"
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    items = [dict(r) for r in rows]
    for it in items:
        it["is_low_stock"] = float(it.get("quantity") or 0) <= float(
            it.get("reorder_level") or 0
        )
    return items


def get_inventory_item(item_id: int) -> Optional[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM inventory_items WHERE id = ?", (item_id,)
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["is_low_stock"] = float(item.get("quantity") or 0) <= float(
        item.get("reorder_level") or 0
    )
    return item


def update_inventory_item(item_id: int, **fields: Any) -> bool:
    allowed = {
        "name",
        "category",
        "brand",
        "sku",
        "description",
        "unit",
        "quantity",
        "reorder_level",
        "purchase_price",
        "selling_price",
        "supplier",
        "tax_gst",
        "status",
        "item_date",
        "notes",
        "image_path",
        "colour",
        "pattern",
        "show_on_website",
        "material_category",
        "size_label",
        "finish",
        "dim_length",
        "dim_width",
        "dim_unit",
    }
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    updates["updated_at"] = utc_now_iso()
    cols = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [item_id]
    with get_db() as conn:
        cur = conn.execute(f"UPDATE inventory_items SET {cols} WHERE id = ?", values)
        return cur.rowcount > 0


def delete_inventory_item(item_id: int) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT image_path FROM inventory_items WHERE id = ?", (item_id,)
        ).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM stock_movements WHERE item_id = ?", (item_id,))
        conn.execute("DELETE FROM inventory_items WHERE id = ?", (item_id,))
        return row["image_path"]


def stock_adjust(
    item_id: int,
    *,
    movement: str,
    quantity: float,
    note: Optional[str] = None,
) -> dict[str, Any]:
    """movement: 'in' | 'out' | 'adjust' (set absolute via note; quantity is delta for in/out)."""
    movement = movement.lower().strip()
    if movement not in ("in", "out", "adjust"):
        raise ValueError("movement must be in, out, or adjust")
    qty = abs(float(quantity))
    with get_db() as conn:
        row = conn.execute(
            "SELECT quantity FROM inventory_items WHERE id = ?", (item_id,)
        ).fetchone()
        if not row:
            raise ValueError("Inventory item not found")
        current = float(row["quantity"] or 0)
        if movement == "in":
            new_q = current + qty
            signed = qty
        elif movement == "out":
            new_q = max(0.0, current - qty)
            signed = -qty
        else:
            new_q = qty
            signed = new_q - current
        now = utc_now_iso()
        conn.execute(
            "UPDATE inventory_items SET quantity = ?, updated_at = ? WHERE id = ?",
            (new_q, now, item_id),
        )
        conn.execute(
            """
            INSERT INTO stock_movements (item_id, movement, quantity, note, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (item_id, movement, signed, note, now),
        )
    item = get_inventory_item(item_id)
    assert item is not None
    return item


def list_stock_movements(item_id: int, limit: int = 100) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM stock_movements WHERE item_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (item_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def list_public_inventory_products(limit: int = 200) -> list[dict[str, Any]]:
    """Inventory items flagged for website Products page (no admin-only fields)."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, name, category, description, unit, selling_price, image_path,
                   colour, pattern, material_category, size_label, finish, brand,
                   dim_length, dim_width, dim_unit
            FROM inventory_items
            WHERE show_on_website = 1 AND status = 'active'
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def log_app(
    message: str,
    *,
    level: str = "INFO",
    source: str = "app",
    detail: Optional[str] = None,
) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO app_logs (level, source, message, detail, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (level.upper()[:20], source[:80], message, detail, utc_now_iso()),
        )
        return int(cur.lastrowid)


def log_user(
    username: str,
    action: str,
    *,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    detail: Optional[str] = None,
    ip: Optional[str] = None,
) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO user_logs (
                username, action, entity_type, entity_id, detail, ip, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username or "unknown",
                action[:120],
                entity_type,
                entity_id,
                detail,
                ip,
                utc_now_iso(),
            ),
        )
        return int(cur.lastrowid)


def list_app_logs(limit: int = 200, level: Optional[str] = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM app_logs"
    params: list[Any] = []
    if level:
        sql += " WHERE upper(level) = ?"
        params.append(level.upper())
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def list_user_logs(limit: int = 200, username: Optional[str] = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM user_logs"
    params: list[Any] = []
    if username:
        sql += " WHERE username = ?"
        params.append(username)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


# ---------------------------------------------------------------------------
# Reviews / feedback / ratings
# ---------------------------------------------------------------------------

def insert_review(
    *,
    name: str,
    message: str,
    rating: int = 5,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    title: Optional[str] = None,
) -> int:
    rating = max(1, min(5, int(rating or 5)))
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO reviews (
                name, email, phone, rating, title, message, status, is_featured, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', 0, ?)
            """,
            (
                name.strip(),
                (email or "").strip() or None,
                (phone or "").strip() or None,
                rating,
                (title or "").strip() or None,
                message.strip(),
                utc_now_iso(),
            ),
        )
        return int(cur.lastrowid)


def list_reviews(
    status: Optional[str] = None,
    limit: int = 200,
    featured_only: bool = False,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM reviews WHERE 1=1"
    params: list[Any] = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if featured_only:
        sql += " AND is_featured = 1 AND status = 'approved'"
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def list_public_reviews(limit: int = 12) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, name, rating, title, message, created_at, is_featured
            FROM reviews
            WHERE status = 'approved'
            ORDER BY is_featured DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_review(review_id: int, **fields: Any) -> bool:
    allowed = {"status", "is_featured", "title", "message", "rating", "reviewed_at"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    if "status" in updates and "reviewed_at" not in updates:
        updates["reviewed_at"] = utc_now_iso()
    cols = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [review_id]
    with get_db() as conn:
        cur = conn.execute(f"UPDATE reviews SET {cols} WHERE id = ?", values)
        return cur.rowcount > 0


def delete_review(review_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        return cur.rowcount > 0


def get_analytics_payload() -> dict[str, Any]:
    """Data for dashboard / inventory charts."""
    with get_db() as conn:
        sales_by_day = conn.execute(
            """
            SELECT sale_date AS label, COALESCE(SUM(amount), 0) AS value
            FROM sales WHERE status != 'cancelled'
            GROUP BY sale_date ORDER BY sale_date DESC LIMIT 14
            """
        ).fetchall()
        inv_by_cat = conn.execute(
            """
            SELECT category AS label, COUNT(*) AS value, COALESCE(SUM(quantity), 0) AS qty
            FROM inventory_items GROUP BY category ORDER BY value DESC
            """
        ).fetchall()
        low = conn.execute(
            """
            SELECT name AS label, quantity AS value, reorder_level
            FROM inventory_items
            WHERE status = 'active' AND quantity <= reorder_level
            ORDER BY quantity ASC LIMIT 12
            """
        ).fetchall()
        posted = conn.execute(
            "SELECT COUNT(*) AS c FROM inventory_items WHERE show_on_website = 1"
        ).fetchone()["c"]
        total_inv = conn.execute("SELECT COUNT(*) AS c FROM inventory_items").fetchone()["c"]
    return {
        "sales_by_day": [
            {"label": r["label"], "value": float(r["value"])}
            for r in reversed(list(sales_by_day))
        ],
        "inventory_by_category": [
            {"label": r["label"], "value": int(r["value"]), "qty": float(r["qty"])}
            for r in inv_by_cat
        ],
        "low_stock_items": [
            {
                "label": r["label"],
                "value": float(r["value"]),
                "reorder_level": float(r["reorder_level"] or 0),
            }
            for r in low
        ],
        "posted_on_website": int(posted or 0),
        "inventory_total": int(total_inv or 0),
    }


# ---------------------------------------------------------------------------
# Sales returns & purchases
# ---------------------------------------------------------------------------

def insert_sales_return(**fields: Any) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO sales_returns (
                return_no, original_invoice, customer_name, customer_phone,
                product_name, quantity, amount, return_date, reason, status, notes, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                fields.get("return_no"),
                fields.get("original_invoice"),
                fields.get("customer_name"),
                fields.get("customer_phone"),
                fields.get("product_name"),
                float(fields.get("quantity") or 1),
                float(fields.get("amount") or 0),
                fields.get("return_date"),
                fields.get("reason"),
                fields.get("status") or "completed",
                fields.get("notes"),
                utc_now_iso(),
            ),
        )
        return int(cur.lastrowid)


def list_sales_returns(limit: int = 300) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM sales_returns ORDER BY return_date DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_sales_return(row_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM sales_returns WHERE id = ?", (row_id,))
        return cur.rowcount > 0


def insert_purchase(**fields: Any) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO purchases (
                purchase_no, supplier_name, supplier_phone, product_name, category,
                quantity, amount, purchase_date, status, notes, inventory_id, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                fields.get("purchase_no"),
                fields.get("supplier_name"),
                fields.get("supplier_phone"),
                fields.get("product_name"),
                fields.get("category"),
                float(fields.get("quantity") or 1),
                float(fields.get("amount") or 0),
                fields.get("purchase_date"),
                fields.get("status") or "received",
                fields.get("notes"),
                fields.get("inventory_id"),
                utc_now_iso(),
            ),
        )
        return int(cur.lastrowid)


def list_purchases(limit: int = 300) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM purchases ORDER BY purchase_date DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_purchase(row_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM purchases WHERE id = ?", (row_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Reminders & communication
# ---------------------------------------------------------------------------

def set_entity_reminder(
    entity_type: str,
    entity_id: int,
    reminder_at: Optional[str],
    reminder_note: Optional[str] = None,
) -> bool:
    table_map = {
        "lead": "leads",
        "contact": "contact_messages",
        "enquiry": "enquiries",
    }
    table = table_map.get(entity_type)
    if not table:
        return False
    with get_db() as conn:
        cur = conn.execute(
            f"UPDATE {table} SET reminder_at = ?, reminder_note = ? WHERE id = ?",
            (reminder_at, reminder_note, entity_id),
        )
        return cur.rowcount > 0


def log_communication(
    entity_type: str,
    entity_id: int,
    channel: str,
    detail: Optional[str] = None,
) -> int:
    table_map = {
        "lead": "leads",
        "contact": "contact_messages",
        "enquiry": "enquiries",
    }
    table = table_map.get(entity_type)
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO communication_logs (entity_type, entity_id, channel, detail, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (entity_type, entity_id, channel, detail, utc_now_iso()),
        )
        if table:
            conn.execute(
                f"UPDATE {table} SET last_contact_channel = ? WHERE id = ?",
                (channel, entity_id),
            )
        return int(cur.lastrowid)


def list_reminders() -> dict[str, list[dict[str, Any]]]:
    now = utc_now_iso()
    pending: list[dict[str, Any]] = []
    overdue: list[dict[str, Any]] = []
    with get_db() as conn:
        for etype, table, name_col in (
            ("lead", "leads", "name"),
            ("contact", "contact_messages", "name"),
            ("enquiry", "enquiries", "name"),
        ):
            rows = conn.execute(
                f"""
                SELECT id, {name_col} AS name, phone, email, reminder_at, reminder_note, status
                FROM {table}
                WHERE reminder_at IS NOT NULL AND trim(reminder_at) != ''
                ORDER BY reminder_at ASC
                """
            ).fetchall()
            for r in rows:
                item = dict(r)
                item["entity_type"] = etype
                if item["reminder_at"] < now:
                    overdue.append(item)
                else:
                    pending.append(item)
    return {"pending": pending, "overdue": overdue}


def category_slug(category: str) -> str:
    """Map free-text material / sub category to products filter slug."""
    raw = (category or "").strip().lower().replace("_", " ").replace("-", " ")
    mapping = {
        "vitrified": "vitrified-tiles",
        "vitrified tiles": "vitrified-tiles",
        "ceramic": "ceramic-tiles",
        "ceramic tiles": "ceramic-tiles",
        "parking": "parking-tiles",
        "parking tiles": "parking-tiles",
        "outdoor": "outdoor-tiles",
        "outdoor tiles": "outdoor-tiles",
        "wooden": "wooden-finish",
        "wooden finish": "wooden-finish",
        "wood": "wooden-finish",
        "marble": "marble-finish",
        "marble finish": "marble-finish",
        "bathroom": "bathroom-tiles",
        "bathroom tiles": "bathroom-tiles",
        "kitchen": "kitchen-tiles",
        "kitchen tiles": "kitchen-tiles",
        "elevation": "elevation-tiles",
        "elevation tiles": "elevation-tiles",
        "general": "general",
    }
    if raw in mapping:
        return mapping[raw]
    slug = "-".join(raw.split())
    return slug or "general"


def main_category_slug(category: str) -> str:
    """Inventory main category slug (Tiles, Paste, Adhesive, …)."""
    raw = (category or "").strip().lower().replace("_", " ")
    raw = "-".join(raw.split())
    # normalize known inventory labels
    aliases = {
        "tile": "tiles",
        "sanitary-ware": "sanitary-wares",
        "sanitarywares": "sanitary-wares",
        "sanitary": "sanitary-wares",
        "adhesives": "adhesive",
        "pastes": "paste",
        "beadings": "beading",
        "other": "others",
    }
    return aliases.get(raw, raw or "others")


def sub_category_label(item: dict) -> str:
    """
    Under-category for Products page filters.
    Primary source: inventory material_category field (stored as subcategory in admin UI).
    """
    return (
        (item.get("material_category") or "").strip()
        or (item.get("pattern") or "").strip()
        or "General"
    )


# ---------------------------------------------------------------------------
# Homepage trust-strip stats (site_settings)
# ---------------------------------------------------------------------------

TRUST_STAT_KEYS = (
    "trust_years_experience",
    "trust_projects_completed",
    "trust_tile_designs",
    "trust_happy_clients",
)

TRUST_STAT_DEFAULTS = {
    "trust_years_experience": 25,
    "trust_projects_completed": 2500,
    "trust_tile_designs": 800,
    "trust_happy_clients": 15000,
}


def get_site_stats() -> dict[str, int]:
    """Return homepage trust counters (ints). Missing keys fall back to defaults."""
    out = dict(TRUST_STAT_DEFAULTS)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT key, value FROM site_settings WHERE key LIKE 'trust_%'"
        ).fetchall()
    for row in rows:
        key = row["key"]
        if key in out:
            try:
                out[key] = max(0, int(str(row["value"]).strip()))
            except (TypeError, ValueError):
                pass
    return {
        "years_experience": out["trust_years_experience"],
        "projects_completed": out["trust_projects_completed"],
        "tile_designs": out["trust_tile_designs"],
        "happy_clients": out["trust_happy_clients"],
    }


def update_site_stats(
    *,
    years_experience: int,
    projects_completed: int,
    tile_designs: int,
    happy_clients: int,
) -> dict[str, int]:
    """Upsert trust-strip numbers. Returns normalized stats."""
    mapping = {
        "trust_years_experience": max(0, int(years_experience)),
        "trust_projects_completed": max(0, int(projects_completed)),
        "trust_tile_designs": max(0, int(tile_designs)),
        "trust_happy_clients": max(0, int(happy_clients)),
    }
    now = utc_now_iso()
    with get_db() as conn:
        for key, val in mapping.items():
            conn.execute(
                """
                INSERT INTO site_settings (key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, str(val), now),
            )
    return get_site_stats()
