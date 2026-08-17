"""
Database package for Chalukya Tiles showroom.

SQLite is used initially (database/showroom.db).
Schema and helpers are written to allow a clean switch to MySQL later:
- Standard SQL types where possible
- Explicit primary keys and timestamps
- Connection logic isolated from route handlers

Public helpers are re-exported from database.db for convenient imports.
"""

from database.db import (
    init_db,
    insert_contact_message,
    insert_enquiry,
    list_contact_messages,
    list_enquiries,
)

__all__ = [
    "init_db",
    "insert_contact_message",
    "insert_enquiry",
    "list_contact_messages",
    "list_enquiries",
]
