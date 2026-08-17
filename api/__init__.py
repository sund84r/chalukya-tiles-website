"""
API package for Chalukya Tiles showroom.

Modular FastAPI routers live here (e.g. enquiry / contact endpoints).
Import routers in app.py and register them with include_router().
"""

from api.enquiry import router as enquiry_router

__all__ = ["enquiry_router"]
