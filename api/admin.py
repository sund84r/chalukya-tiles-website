"""
Admin panel API — auth, dashboard, tiles media, videos, sales, leads, customers, queries.
"""

from __future__ import annotations

import re
import secrets
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from database import db as database

router = APIRouter(prefix="/api/admin", tags=["admin"])

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
ALLOWED_VIDEO_EXT = {".mp4", ".webm", ".mov", ".mkv"}
MAX_IMAGE_BYTES = 12 * 1024 * 1024  # 12 MB
MAX_VIDEO_BYTES = 120 * 1024 * 1024  # 120 MB


# ---------------------------------------------------------------------------
# Auth helpers + permission gates
# ---------------------------------------------------------------------------

def _resolve_api_modules(path: str) -> Optional[tuple[str, ...]]:
    """Map /api/admin/* paths to required permission module keys."""
    if path in ("/api/admin/login", "/api/admin/logout", "/api/admin/me"):
        return None
    if path.startswith("/api/admin/users"):
        return ("__superadmin__",)
    if path.startswith("/api/admin/logs/app") or path.startswith("/api/admin/logs/cli"):
        # CLI dump may be either log type; require either log permission
        if "kind=user" in path:
            return ("user-logs",)
        return ("app-logs", "user-logs")
    if path.startswith("/api/admin/logs/user"):
        return ("user-logs",)
    if path.startswith("/api/admin/backup") or path.startswith("/api/admin/export") or path.startswith("/api/admin/import"):
        return ("data-tools",)
    if path.startswith("/api/admin/reviews"):
        return ("reviews",)
    if path.startswith("/api/admin/concept-gallery"):
        return ("concept-gallery",)
    if path.startswith("/api/admin/tiles"):
        return ("tiles",)
    if path.startswith("/api/admin/videos"):
        return ("videos",)
    if path.startswith("/api/admin/inventory"):
        return ("inventory", "inventory-add", "inv-overview")
    if path.startswith("/api/admin/customers"):
        return ("customers",)
    if path.startswith("/api/admin/leads") or path.startswith("/api/admin/reminders"):
        return ("leads",)
    if (
        path.startswith("/api/admin/queries")
        or path.startswith("/api/admin/contacts")
        or "/enquiry" in path
    ):
        return ("queries",)
    if path.startswith("/api/admin/returns") or "sales-return" in path:
        return ("sales-returns",)
    if path.startswith("/api/admin/purchases"):
        return ("purchases",)
    if path.startswith("/api/admin/sales"):
        return ("sales",)
    if path.startswith("/api/admin/dashboard") or path.startswith("/api/admin/analytics"):
        return ("dashboard", "inv-overview")
    # Default: any logged-in staff
    return None


def require_admin(request: Request) -> dict[str, Any]:
    session_user = request.session.get("admin_user")
    if not session_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin login required",
        )
    fresh = database.get_admin_user(int(session_user["id"]))
    if not fresh or not fresh.get("is_active"):
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin session expired or account disabled",
        )
    user = {
        "id": fresh["id"],
        "username": fresh["username"],
        "role": fresh["role"],
        "is_superadmin": fresh["is_superadmin"],
        "permissions": fresh["permissions"],
    }
    request.session["admin_user"] = user

    path = request.url.path
    needed = _resolve_api_modules(path)
    # /logs/cli?kind=user|app|both — path has no query string
    if path.startswith("/api/admin/logs/cli"):
        kind = (request.query_params.get("kind") or "app").lower()
        if kind == "user":
            needed = ("user-logs",)
        elif kind == "both":
            needed = ("app-logs", "user-logs")
        else:
            needed = ("app-logs",)
    if needed is None:
        return user
    if needed == ("__superadmin__",):
        if not user.get("is_superadmin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the main admin can manage users",
            )
        return user
    if not database.user_has_permission(user, *needed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission for this section",
        )
    return user


def require_superadmin(user: dict = Depends(require_admin)) -> dict[str, Any]:
    if not user.get("is_superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the main admin can manage users",
        )
    return user


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=1, max_length=200)


class StatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=40)


class SaleCreate(BaseModel):
    invoice_no: str = Field(..., min_length=1, max_length=80)
    customer_name: str = Field(..., min_length=1, max_length=160)
    customer_phone: Optional[str] = Field(default=None, max_length=40)
    product_name: str = Field(..., min_length=1, max_length=200)
    quantity: float = Field(default=1, ge=0)
    amount: float = Field(default=0, ge=0)
    sale_date: str = Field(..., min_length=4, max_length=40)
    status: str = Field(default="completed", max_length=40)
    notes: Optional[str] = None


class LeadCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    phone: str = Field(..., min_length=5, max_length=40)
    email: Optional[str] = Field(default=None, max_length=180)
    source: Optional[str] = Field(default=None, max_length=100)
    interest: Optional[str] = Field(default=None, max_length=200)
    status: str = Field(default="new", max_length=40)
    notes: Optional[str] = None


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    phone: str = Field(..., min_length=5, max_length=40)
    email: Optional[str] = Field(default=None, max_length=180)
    address: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _safe_ext(filename: Optional[str], allowed: set[str]) -> str:
    name = (filename or "").strip().lower()
    ext = Path(name).suffix
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed))}",
        )
    return ext


def _public_static_path(abs_path: Path) -> str:
    """Convert absolute path under static/ to /static/... URL."""
    rel = abs_path.relative_to(STATIC_DIR).as_posix()
    return f"/static/{rel}"


def _unlink_public(public_path: Optional[str]) -> None:
    if not public_path or not public_path.startswith("/static/"):
        return
    abs_path = STATIC_DIR / public_path[len("/static/") :]
    try:
        if abs_path.is_file() and "uploads" in abs_path.parts:
            abs_path.unlink()
    except OSError:
        pass


async def _save_upload(
    upload: UploadFile,
    dest_dir: Path,
    allowed: set[str],
    max_bytes: int,
) -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = _safe_ext(upload.filename, allowed)
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = dest_dir / filename

    size = 0
    with dest.open("wb") as out:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File too large (max {max_bytes // (1024 * 1024)} MB)",
                )
            out.write(chunk)

    return _public_static_path(dest)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@router.post("/login")
async def admin_login(request: Request, payload: LoginRequest) -> dict[str, Any]:
    user = database.authenticate_admin(payload.username, payload.password)
    if not user:
        database.log_app(
            f"Failed admin login for '{payload.username}'",
            level="WARN",
            source="auth",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    request.session["admin_user"] = user
    request.session["csrf"] = secrets.token_hex(16)
    client = request.client.host if request.client else None
    database.log_user(user["username"], "login", ip=client)
    database.log_app(
        f"Admin login: {user['username']} ({user.get('role', 'user')})",
        source="auth",
    )
    return {
        "success": True,
        "message": "Logged in",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user.get("role"),
            "is_superadmin": bool(user.get("is_superadmin")),
            "permissions": user.get("permissions") or {},
        },
    }


@router.post("/logout")
async def admin_logout(request: Request) -> dict[str, Any]:
    request.session.clear()
    return {"success": True, "message": "Logged out"}


@router.get("/me")
async def admin_me(user: dict = Depends(require_admin)) -> dict[str, Any]:
    return {
        "success": True,
        "user": user,
        "modules": [
            {"key": k, "label": lab} for k, lab in database.ADMIN_PERMISSION_MODULES
        ],
    }


# ---------------------------------------------------------------------------
# User management (superadmin only)
# ---------------------------------------------------------------------------

class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=80)
    password: str = Field(..., min_length=6, max_length=200)
    permissions: dict[str, int] = Field(default_factory=dict)


class AdminUserUpdate(BaseModel):
    password: Optional[str] = Field(default=None, min_length=6, max_length=200)
    permissions: Optional[dict[str, int]] = None
    is_active: Optional[int] = Field(default=None, ge=0, le=1)


@router.get("/users")
async def admin_list_users(_user: dict = Depends(require_superadmin)) -> dict[str, Any]:
    return {
        "success": True,
        "items": database.list_admin_users(),
        "modules": [
            {"key": k, "label": lab} for k, lab in database.ADMIN_PERMISSION_MODULES
        ],
    }


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    payload: AdminUserCreate,
    request: Request,
    user: dict = Depends(require_superadmin),
) -> dict[str, Any]:
    try:
        row_id = database.create_admin_user(
            username=payload.username,
            password=payload.password,
            permissions=payload.permissions,
            role="user",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    client = request.client.host if request.client else None
    database.log_user(
        user["username"],
        "user.create",
        entity_type="admin_user",
        entity_id=row_id,
        detail=payload.username.strip(),
        ip=client,
    )
    database.log_app(
        f"Admin user created: {payload.username.strip()} by {user['username']}",
        source="users",
    )
    return {
        "success": True,
        "message": "User created",
        "id": row_id,
        "item": database.get_admin_user(row_id),
    }


@router.patch("/users/{user_id}")
async def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    request: Request,
    user: dict = Depends(require_superadmin),
) -> dict[str, Any]:
    target = database.get_admin_user(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.get("is_superadmin") and user_id != user["id"]:
        # Allow editing other superadmin only for is_active? Safer: only self password for superadmin
        if payload.permissions is not None or payload.is_active is not None:
            if payload.is_active == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot deactivate a superadmin account here",
                )
    fields: dict[str, Any] = {}
    if payload.password is not None:
        fields["password"] = payload.password
    if payload.permissions is not None and not target.get("is_superadmin"):
        fields["permissions"] = payload.permissions
    if payload.is_active is not None and not target.get("is_superadmin"):
        fields["is_active"] = payload.is_active
    try:
        ok = database.update_admin_user(user_id, **fields)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=400, detail="Nothing to update")
    client = request.client.host if request.client else None
    database.log_user(
        user["username"],
        "user.update",
        entity_type="admin_user",
        entity_id=user_id,
        detail=str(fields.keys()),
        ip=client,
    )
    database.log_app(
        f"Admin user updated id={user_id} by {user['username']}",
        source="users",
        detail=str(list(fields.keys())),
    )
    return {"success": True, "message": "User updated", "item": database.get_admin_user(user_id)}


@router.delete("/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    request: Request,
    user: dict = Depends(require_superadmin),
) -> dict[str, Any]:
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    target = database.get_admin_user(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        ok = database.delete_admin_user(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    client = request.client.host if request.client else None
    database.log_user(
        user["username"],
        "user.delete",
        entity_type="admin_user",
        entity_id=user_id,
        detail=target.get("username"),
        ip=client,
    )
    database.log_app(
        f"Admin user deleted: {target.get('username')} by {user['username']}",
        source="users",
    )
    return {"success": True, "message": "User deleted"}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def dashboard(_user: dict = Depends(require_admin)) -> dict[str, Any]:
    stats = database.get_dashboard_stats()
    return {
        "success": True,
        "stats": stats,
        "recent": {
            "sales": database.list_sales(limit=8),
            "leads": database.list_leads(limit=8),
            "contacts": database.list_contact_messages(limit=5),
            "enquiries": database.list_enquiries(limit=5),
            "tiles": database.list_tiles(limit=6),
        },
    }


# ---------------------------------------------------------------------------
# Tiles media
# ---------------------------------------------------------------------------

@router.get("/tiles")
async def admin_list_tiles(_user: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"success": True, "items": database.list_tiles(limit=500)}


@router.post("/tiles", status_code=status.HTTP_201_CREATED)
async def admin_create_tile(
    _user: dict = Depends(require_admin),
    name: str = Form(...),
    model_number: str = Form(...),
    colour: str = Form(...),
    material_category: str = Form(...),
    pattern: Optional[str] = Form(default=""),
    description: Optional[str] = Form(default=None),
    size_label: Optional[str] = Form(default=None),
    finish: Optional[str] = Form(default=None),
    image: UploadFile = File(...),
) -> dict[str, Any]:
    name = name.strip()
    model_number = model_number.strip()
    colour = colour.strip()
    material_category = material_category.strip()
    pattern = (pattern or "").strip()
    if not all([name, model_number, colour, material_category]):
        raise HTTPException(status_code=400, detail="Name, model number, colour and category are required")

    image_path = await _save_upload(
        image,
        database.UPLOAD_TILES_DIR,
        ALLOWED_IMAGE_EXT,
        MAX_IMAGE_BYTES,
    )
    try:
        row_id = database.insert_tile(
            name=name,
            model_number=model_number,
            colour=colour,
            pattern=pattern,
            material_category=material_category,
            image_path=image_path,
            description=(description or "").strip() or None,
            size_label=(size_label or "").strip() or None,
            finish=(finish or "").strip() or None,
        )
    except database.DuplicateError as exc:
        _unlink_public(image_path)
        raise HTTPException(status_code=409, detail=exc.message) from exc
    tile = database.get_tile(row_id)
    return {"success": True, "message": "Tile uploaded", "item": tile}


@router.patch("/tiles/{tile_id}")
async def admin_update_tile(
    tile_id: int,
    _user: dict = Depends(require_admin),
    name: Optional[str] = Form(default=None),
    model_number: Optional[str] = Form(default=None),
    colour: Optional[str] = Form(default=None),
    pattern: Optional[str] = Form(default=None),
    material_category: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    size_label: Optional[str] = Form(default=None),
    finish: Optional[str] = Form(default=None),
    is_active: Optional[int] = Form(default=None),
    image: Optional[UploadFile] = File(default=None),
) -> dict[str, Any]:
    existing = database.get_tile(tile_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Tile not found")

    fields: dict[str, Any] = {}
    for key, val in {
        "name": name,
        "model_number": model_number,
        "colour": colour,
        "pattern": pattern,
        "material_category": material_category,
        "description": description,
        "size_label": size_label,
        "finish": finish,
        "is_active": is_active,
    }.items():
        if val is not None and (key == "pattern" or str(val).strip() != ""):
            fields[key] = val if key == "is_active" else str(val).strip()

    if image is not None and image.filename:
        new_path = await _save_upload(
            image,
            database.UPLOAD_TILES_DIR,
            ALLOWED_IMAGE_EXT,
            MAX_IMAGE_BYTES,
        )
        fields["image_path"] = new_path
        _unlink_public(existing.get("image_path"))

    if fields:
        try:
            database.update_tile(tile_id, **fields)
        except database.DuplicateError as exc:
            raise HTTPException(status_code=409, detail=exc.message) from exc
    return {"success": True, "message": "Tile updated", "item": database.get_tile(tile_id)}


@router.delete("/tiles/{tile_id}")
async def admin_delete_tile(
    tile_id: int,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    image_path = database.delete_tile(tile_id)
    if image_path is None:
        raise HTTPException(status_code=404, detail="Tile not found")
    _unlink_public(image_path)
    return {"success": True, "message": "Tile deleted"}


# ---------------------------------------------------------------------------
# Collection videos
# ---------------------------------------------------------------------------

@router.get("/videos")
async def admin_list_videos(_user: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"success": True, "items": database.list_collection_videos(limit=100)}


@router.post("/videos", status_code=status.HTTP_201_CREATED)
async def admin_create_video(
    _user: dict = Depends(require_admin),
    title: str = Form(...),
    description: Optional[str] = Form(default=None),
    sort_order: int = Form(default=0),
    is_active: int = Form(default=1),
    video: UploadFile = File(...),
    poster: Optional[UploadFile] = File(default=None),
) -> dict[str, Any]:
    title = title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")

    video_path = await _save_upload(
        video,
        database.UPLOAD_VIDEOS_DIR,
        ALLOWED_VIDEO_EXT,
        MAX_VIDEO_BYTES,
    )
    poster_path = None
    if poster is not None and poster.filename:
        poster_path = await _save_upload(
            poster,
            database.UPLOAD_POSTERS_DIR,
            ALLOWED_IMAGE_EXT,
            MAX_IMAGE_BYTES,
        )

    row_id = database.insert_collection_video(
        title=title,
        description=(description or "").strip() or None,
        video_path=video_path,
        poster_path=poster_path,
        sort_order=sort_order,
        is_active=is_active,
    )
    return {
        "success": True,
        "message": "Collection video uploaded",
        "item": database.get_collection_video(row_id),
    }


@router.patch("/videos/{video_id}")
async def admin_update_video(
    video_id: int,
    _user: dict = Depends(require_admin),
    title: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    sort_order: Optional[int] = Form(default=None),
    is_active: Optional[int] = Form(default=None),
) -> dict[str, Any]:
    existing = database.get_collection_video(video_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Video not found")
    fields: dict[str, Any] = {}
    if title is not None and title.strip():
        fields["title"] = title.strip()
    if description is not None:
        fields["description"] = description.strip() or None
    if sort_order is not None:
        fields["sort_order"] = sort_order
    if is_active is not None:
        fields["is_active"] = is_active
    if fields:
        database.update_collection_video(video_id, **fields)
    return {
        "success": True,
        "message": "Video updated",
        "item": database.get_collection_video(video_id),
    }


@router.delete("/videos/{video_id}")
async def admin_delete_video(
    video_id: int,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    paths = database.delete_collection_video(video_id)
    if paths is None:
        raise HTTPException(status_code=404, detail="Video not found")
    _unlink_public(paths.get("video_path"))
    _unlink_public(paths.get("poster_path"))
    return {"success": True, "message": "Video deleted"}


# ---------------------------------------------------------------------------
# Concept Gallery pictures (public /gallery)
# ---------------------------------------------------------------------------

_GALLERY_CATS = {slug for slug, _ in database.CONCEPT_GALLERY_CATEGORIES}


@router.get("/concept-gallery")
async def admin_list_concept_gallery(
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    return {
        "success": True,
        "items": database.list_concept_gallery(limit=300),
        "categories": [
            {"slug": s, "label": lab}
            for s, lab in database.CONCEPT_GALLERY_CATEGORIES
        ],
    }


@router.post("/concept-gallery", status_code=status.HTTP_201_CREATED)
async def admin_create_concept_gallery(
    _user: dict = Depends(require_admin),
    title: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(default=None),
    sort_order: int = Form(default=0),
    is_active: int = Form(default=1),
    image: UploadFile = File(...),
) -> dict[str, Any]:
    title = title.strip()
    cat = category.strip().lower()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    if cat not in _GALLERY_CATS:
        raise HTTPException(
            status_code=400,
            detail="Category must be living, bathroom, parking, elevation, or outdoor",
        )
    image_path = await _save_upload(
        image,
        database.UPLOAD_GALLERY_DIR,
        ALLOWED_IMAGE_EXT,
        MAX_IMAGE_BYTES,
    )
    row_id = database.insert_concept_gallery(
        title=title,
        category=cat,
        image_path=image_path,
        description=(description or "").strip() or None,
        sort_order=sort_order,
        is_active=is_active,
    )
    database.log_user(
        _user.get("username", "admin"),
        "concept_gallery.create",
        entity_type="concept_gallery",
        entity_id=row_id,
        detail=title,
    )
    return {
        "success": True,
        "message": "Concept gallery image uploaded",
        "item": database.get_concept_gallery(row_id),
    }


@router.patch("/concept-gallery/{item_id}")
async def admin_update_concept_gallery(
    item_id: int,
    _user: dict = Depends(require_admin),
    title: Optional[str] = Form(default=None),
    category: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    sort_order: Optional[int] = Form(default=None),
    is_active: Optional[int] = Form(default=None),
) -> dict[str, Any]:
    if not database.get_concept_gallery(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    fields: dict[str, Any] = {}
    if title is not None and title.strip():
        fields["title"] = title.strip()
    if category is not None and category.strip():
        cat = category.strip().lower()
        if cat not in _GALLERY_CATS:
            raise HTTPException(status_code=400, detail="Invalid category")
        fields["category"] = cat
    if description is not None:
        fields["description"] = description.strip() or None
    if sort_order is not None:
        fields["sort_order"] = sort_order
    if is_active is not None:
        fields["is_active"] = is_active
    if fields:
        database.update_concept_gallery(item_id, **fields)
    return {
        "success": True,
        "message": "Updated",
        "item": database.get_concept_gallery(item_id),
    }


@router.delete("/concept-gallery/{item_id}")
async def admin_delete_concept_gallery(
    item_id: int,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    path = database.delete_concept_gallery(item_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Item not found")
    _unlink_public(path)
    database.log_user(
        _user.get("username", "admin"),
        "concept_gallery.delete",
        entity_type="concept_gallery",
        entity_id=item_id,
    )
    return {"success": True, "message": "Deleted"}


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------

@router.get("/sales")
async def admin_list_sales(_user: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"success": True, "items": database.list_sales(limit=500)}


@router.post("/sales", status_code=status.HTTP_201_CREATED)
async def admin_create_sale(
    payload: SaleCreate,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    row_id = database.insert_sale(
        invoice_no=payload.invoice_no.strip(),
        customer_name=payload.customer_name.strip(),
        customer_phone=(payload.customer_phone or "").strip() or None,
        product_name=payload.product_name.strip(),
        quantity=payload.quantity,
        amount=payload.amount,
        sale_date=payload.sale_date.strip(),
        status=payload.status.strip() or "completed",
        notes=(payload.notes or "").strip() or None,
    )
    return {"success": True, "message": "Sale recorded", "id": row_id}


@router.delete("/sales/{sale_id}")
async def admin_delete_sale(
    sale_id: int,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not database.delete_sale(sale_id):
        raise HTTPException(status_code=404, detail="Sale not found")
    return {"success": True, "message": "Sale deleted"}


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------

@router.get("/leads")
async def admin_list_leads(_user: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"success": True, "items": database.list_leads(limit=500)}


@router.post("/leads", status_code=status.HTTP_201_CREATED)
async def admin_create_lead(
    payload: LeadCreate,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    row_id = database.insert_lead(
        name=payload.name.strip(),
        phone=payload.phone.strip(),
        email=(payload.email or "").strip() or None,
        source=(payload.source or "").strip() or None,
        interest=(payload.interest or "").strip() or None,
        status=payload.status.strip() or "new",
        notes=(payload.notes or "").strip() or None,
    )
    return {"success": True, "message": "Lead created", "id": row_id}


@router.patch("/leads/{lead_id}")
async def admin_update_lead(
    lead_id: int,
    payload: LeadCreate,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    ok = database.update_lead(
        lead_id,
        name=payload.name.strip(),
        phone=payload.phone.strip(),
        email=(payload.email or "").strip() or None,
        source=(payload.source or "").strip() or None,
        interest=(payload.interest or "").strip() or None,
        status=payload.status.strip() or "new",
        notes=(payload.notes or "").strip() or None,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True, "message": "Lead updated"}


@router.delete("/leads/{lead_id}")
async def admin_delete_lead(
    lead_id: int,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not database.delete_lead(lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True, "message": "Lead deleted"}


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

@router.get("/customers")
async def admin_list_customers(_user: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"success": True, "items": database.list_customers(limit=500)}


@router.post("/customers", status_code=status.HTTP_201_CREATED)
async def admin_create_customer(
    payload: CustomerCreate,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    try:
        row_id = database.insert_customer(
            name=payload.name.strip(),
            phone=payload.phone.strip(),
            email=(payload.email or "").strip() or None,
            address=(payload.address or "").strip() or None,
            city=(payload.city or "").strip() or None,
            notes=(payload.notes or "").strip() or None,
        )
    except database.DuplicateError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    return {"success": True, "message": "Customer created", "id": row_id}


@router.patch("/customers/{customer_id}")
async def admin_update_customer(
    customer_id: int,
    payload: CustomerCreate,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    try:
        ok = database.update_customer(
            customer_id,
            name=payload.name.strip(),
            phone=payload.phone.strip(),
            email=(payload.email or "").strip() or None,
            address=(payload.address or "").strip() or None,
            city=(payload.city or "").strip() or None,
            notes=(payload.notes or "").strip() or None,
        )
    except database.DuplicateError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"success": True, "message": "Customer updated"}


@router.delete("/customers/{customer_id}")
async def admin_delete_customer(
    customer_id: int,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not database.delete_customer(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"success": True, "message": "Customer deleted"}


# ---------------------------------------------------------------------------
# Queries (contact + enquiries)
# ---------------------------------------------------------------------------

@router.get("/queries")
async def admin_list_queries(_user: dict = Depends(require_admin)) -> dict[str, Any]:
    contacts = database.list_contact_messages(limit=300)
    enquiries = database.list_enquiries(limit=300)
    for c in contacts:
        c["query_type"] = "contact"
    for e in enquiries:
        e["query_type"] = "enquiry"
    return {
        "success": True,
        "contacts": contacts,
        "enquiries": enquiries,
    }


@router.patch("/queries/contact/{row_id}")
async def admin_update_contact_status(
    row_id: int,
    payload: StatusUpdate,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not database.update_contact_status(row_id, payload.status.strip()):
        raise HTTPException(status_code=404, detail="Contact message not found")
    return {"success": True, "message": "Status updated"}


@router.patch("/queries/enquiry/{row_id}")
async def admin_update_enquiry_status(
    row_id: int,
    payload: StatusUpdate,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not database.update_enquiry_status(row_id, payload.status.strip()):
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return {"success": True, "message": "Status updated"}


@router.delete("/queries/contact/{row_id}")
async def admin_delete_contact(
    row_id: int,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not database.delete_contact_message(row_id):
        raise HTTPException(status_code=404, detail="Contact message not found")
    return {"success": True, "message": "Deleted"}


@router.delete("/queries/enquiry/{row_id}")
async def admin_delete_enquiry(
    row_id: int,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not database.delete_enquiry(row_id):
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return {"success": True, "message": "Deleted"}


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

class InventoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=80)
    brand: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    unit: str = "pieces"
    quantity: float = 0
    reorder_level: float = 0
    purchase_price: float = 0
    selling_price: float = 0
    supplier: Optional[str] = None
    tax_gst: float = 0
    status: str = "active"
    item_date: Optional[str] = None
    notes: Optional[str] = None
    colour: Optional[str] = None
    pattern: Optional[str] = None
    show_on_website: int = 0
    material_category: Optional[str] = None
    size_label: Optional[str] = None
    finish: Optional[str] = None
    dim_length: Optional[float] = None
    dim_width: Optional[float] = None
    dim_unit: Optional[str] = None


class StockAdjust(BaseModel):
    movement: str = Field(..., pattern="^(in|out|adjust)$")
    quantity: float = Field(..., ge=0)
    note: Optional[str] = None


class SalesReturnCreate(BaseModel):
    return_no: str
    original_invoice: Optional[str] = None
    customer_name: str
    customer_phone: Optional[str] = None
    product_name: str
    quantity: float = 1
    amount: float = 0
    return_date: str
    reason: Optional[str] = None
    status: str = "completed"
    notes: Optional[str] = None


class PurchaseCreate(BaseModel):
    purchase_no: str
    supplier_name: str
    supplier_phone: Optional[str] = None
    product_name: str
    category: Optional[str] = None
    quantity: float = 1
    amount: float = 0
    purchase_date: str
    status: str = "received"
    notes: Optional[str] = None
    inventory_id: Optional[int] = None


class ReminderPayload(BaseModel):
    entity_type: str = Field(..., pattern="^(lead|contact|enquiry)$")
    entity_id: int
    reminder_at: Optional[str] = None
    reminder_note: Optional[str] = None


class CommLogPayload(BaseModel):
    entity_type: str = Field(..., pattern="^(lead|contact|enquiry)$")
    entity_id: int
    channel: str
    detail: Optional[str] = None


@router.get("/inventory")
async def admin_list_inventory(
    _user: dict = Depends(require_admin),
    category: Optional[str] = None,
    q: Optional[str] = None,
    low_stock: int = 0,
) -> dict[str, Any]:
    items = database.list_inventory(
        category=category,
        q=q,
        low_stock_only=bool(low_stock),
        limit=500,
    )
    return {
        "success": True,
        "items": items,
        "categories": list(database.INVENTORY_CATEGORIES),
        "subcategories": {
            k: list(v) for k, v in database.INVENTORY_SUBCATEGORIES.items()
        },
        "units": list(database.INVENTORY_UNITS),
        "dim_units": list(database.TILE_DIM_UNITS),
    }


@router.post("/inventory", status_code=status.HTTP_201_CREATED)
async def admin_create_inventory(
    _user: dict = Depends(require_admin),
    name: str = Form(...),
    category: str = Form(...),
    brand: Optional[str] = Form(default=None),
    sku: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    unit: str = Form(default="pcs"),
    quantity: float = Form(default=0),
    reorder_level: float = Form(default=0),
    purchase_price: float = Form(default=0),
    selling_price: float = Form(default=0),
    supplier: Optional[str] = Form(default=None),
    tax_gst: float = Form(default=0),
    status: str = Form(default="active"),
    item_date: Optional[str] = Form(default=None),
    notes: Optional[str] = Form(default=None),
    colour: Optional[str] = Form(default=None),
    pattern: Optional[str] = Form(default=None),
    show_on_website: int = Form(default=0),
    material_category: Optional[str] = Form(default=None),
    size_label: Optional[str] = Form(default=None),
    finish: Optional[str] = Form(default=None),
    dim_length: Optional[float] = Form(default=None),
    dim_width: Optional[float] = Form(default=None),
    dim_unit: Optional[str] = Form(default=None),
    image: Optional[UploadFile] = File(default=None),
) -> dict[str, Any]:
    if category not in database.INVENTORY_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Use one of: {', '.join(database.INVENTORY_CATEGORIES)}")
    image_path = None
    if image is not None and image.filename:
        image_path = await _save_upload(
            image,
            database.UPLOAD_INVENTORY_DIR,
            ALLOWED_IMAGE_EXT,
            MAX_IMAGE_BYTES,
        )
    size_auto = (size_label or "").strip() or None
    if not size_auto and dim_length and dim_width and dim_unit:
        size_auto = f"{dim_length} × {dim_width} {dim_unit}"
    row_id = database.insert_inventory_item(
        name=name.strip(),
        category=category.strip(),
        brand=(brand or "").strip() or None,
        sku=(sku or "").strip() or None,
        description=(description or "").strip() or None,
        unit=(unit or "pieces").strip(),
        quantity=quantity,
        reorder_level=reorder_level,
        purchase_price=purchase_price,
        selling_price=selling_price,
        supplier=(supplier or "").strip() or None,
        tax_gst=tax_gst,
        status=(status or "active").strip(),
        item_date=(item_date or "").strip() or None,
        notes=(notes or "").strip() or None,
        image_path=image_path,
        colour=(colour or "").strip() or None,
        pattern=(pattern or "").strip() or "",
        show_on_website=int(show_on_website or 0),
        material_category=(material_category or "").strip() or None,
        size_label=size_auto,
        finish=(finish or "").strip() or None,
        dim_length=dim_length,
        dim_width=dim_width,
        dim_unit=(dim_unit or "").strip() or None,
    )
    user = _user
    database.log_user(
        user.get("username", "admin"),
        "inventory.create",
        entity_type="inventory",
        entity_id=row_id,
        detail=name.strip(),
    )
    return {
        "success": True,
        "message": "Inventory item created",
        "item": database.get_inventory_item(row_id),
    }


@router.patch("/inventory/{item_id}")
async def admin_update_inventory(
    item_id: int,
    payload: InventoryCreate,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not database.get_inventory_item(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    size_auto = (payload.size_label or "").strip() or None
    if not size_auto and payload.dim_length and payload.dim_width and payload.dim_unit:
        size_auto = f"{payload.dim_length} × {payload.dim_width} {payload.dim_unit}"
    database.update_inventory_item(
        item_id,
        name=payload.name.strip(),
        category=payload.category.strip(),
        brand=(payload.brand or "").strip() or None,
        sku=(payload.sku or "").strip() or None,
        description=(payload.description or "").strip() or None,
        unit=payload.unit or "pieces",
        quantity=payload.quantity,
        reorder_level=payload.reorder_level,
        purchase_price=payload.purchase_price,
        selling_price=payload.selling_price,
        supplier=(payload.supplier or "").strip() or None,
        tax_gst=payload.tax_gst,
        status=payload.status or "active",
        item_date=payload.item_date,
        notes=(payload.notes or "").strip() or None,
        colour=(payload.colour or "").strip() or None,
        pattern=(payload.pattern or "").strip() or "",
        show_on_website=int(payload.show_on_website or 0),
        material_category=(payload.material_category or "").strip() or None,
        size_label=size_auto,
        finish=(payload.finish or "").strip() or None,
        dim_length=payload.dim_length,
        dim_width=payload.dim_width,
        dim_unit=(payload.dim_unit or "").strip() or None,
    )
    database.log_user(
        _user.get("username", "admin"),
        "inventory.update",
        entity_type="inventory",
        entity_id=item_id,
        detail=payload.name.strip(),
    )
    return {"success": True, "item": database.get_inventory_item(item_id)}


@router.delete("/inventory/{item_id}")
async def admin_delete_inventory(
    item_id: int,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not database.get_inventory_item(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    path = database.delete_inventory_item(item_id)
    _unlink_public(path)
    return {"success": True, "message": "Deleted"}


class VisibilityPayload(BaseModel):
    """Public (1) = show on website Products page; Private (0) = admin only."""

    show_on_website: int = Field(..., ge=0, le=1)


@router.patch("/inventory/{item_id}/visibility")
async def admin_inventory_visibility(
    item_id: int,
    payload: VisibilityPayload,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not database.get_inventory_item(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    database.update_inventory_item(
        item_id,
        show_on_website=int(payload.show_on_website),
    )
    item = database.get_inventory_item(item_id)
    return {
        "success": True,
        "message": "Public on Products" if payload.show_on_website else "Private (hidden from Products)",
        "item": item,
    }


@router.post("/inventory/{item_id}/stock")
async def admin_stock_adjust(
    item_id: int,
    payload: StockAdjust,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    try:
        item = database.stock_adjust(
            item_id,
            movement=payload.movement,
            quantity=payload.quantity,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "item": item}


@router.get("/inventory/{item_id}/movements")
async def admin_stock_movements(
    item_id: int,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    return {"success": True, "items": database.list_stock_movements(item_id)}


# ---------------------------------------------------------------------------
# Sales returns & purchases
# ---------------------------------------------------------------------------

@router.get("/sales-returns")
async def admin_list_returns(_user: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"success": True, "items": database.list_sales_returns()}


@router.post("/sales-returns", status_code=status.HTTP_201_CREATED)
async def admin_create_return(
    payload: SalesReturnCreate,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    row_id = database.insert_sales_return(**payload.model_dump())
    return {"success": True, "id": row_id, "message": "Sales return recorded"}


@router.delete("/sales-returns/{row_id}")
async def admin_delete_return(
    row_id: int,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not database.delete_sales_return(row_id):
        raise HTTPException(status_code=404, detail="Not found")
    return {"success": True, "message": "Deleted"}


@router.get("/purchases")
async def admin_list_purchases(_user: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"success": True, "items": database.list_purchases()}


@router.post("/purchases", status_code=status.HTTP_201_CREATED)
async def admin_create_purchase(
    payload: PurchaseCreate,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    row_id = database.insert_purchase(**payload.model_dump())
    # Optional stock-in if linked inventory
    if payload.inventory_id and payload.quantity:
        try:
            database.stock_adjust(
                int(payload.inventory_id),
                movement="in",
                quantity=float(payload.quantity),
                note=f"Purchase {payload.purchase_no}",
            )
        except ValueError:
            pass
    return {"success": True, "id": row_id, "message": "Purchase recorded"}


@router.delete("/purchases/{row_id}")
async def admin_delete_purchase(
    row_id: int,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not database.delete_purchase(row_id):
        raise HTTPException(status_code=404, detail="Not found")
    return {"success": True, "message": "Deleted"}


# ---------------------------------------------------------------------------
# Reminders & communication
# ---------------------------------------------------------------------------

@router.get("/reminders")
async def admin_list_reminders(_user: dict = Depends(require_admin)) -> dict[str, Any]:
    data = database.list_reminders()
    return {"success": True, **data}


@router.post("/reminders")
async def admin_set_reminder(
    payload: ReminderPayload,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    ok = database.set_entity_reminder(
        payload.entity_type,
        payload.entity_id,
        payload.reminder_at,
        payload.reminder_note,
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid entity")
    return {"success": True, "message": "Reminder saved"}


@router.post("/communications")
async def admin_log_comm(
    payload: CommLogPayload,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    """Log WhatsApp/SMS/Email/Phone/Follow-up action (no fake SMS send)."""
    channel = payload.channel.strip().lower()
    allowed = {"whatsapp", "sms", "phone", "email", "followup", "intimation"}
    if channel not in allowed:
        raise HTTPException(status_code=400, detail=f"channel must be one of {sorted(allowed)}")
    log_id = database.log_communication(
        payload.entity_type,
        payload.entity_id,
        channel,
        payload.detail,
    )
    # Email structure only — no fake provider
    email_hint = None
    if channel == "email":
        email_hint = {
            "mode": "mailto",
            "note": "Opens client mailer. Configure SMTP later via env if needed.",
        }
    if channel == "sms":
        email_hint = {
            "mode": "ui_only",
            "note": "SMS provider not configured. UI logs intent only.",
        }
    return {
        "success": True,
        "id": log_id,
        "message": "Communication logged",
        "provider": email_hint,
    }


# ---------------------------------------------------------------------------
# Exports (Excel / PDF) + DB backup
# ---------------------------------------------------------------------------

from fastapi.responses import Response, FileResponse  # noqa: E402
from api.exports import filename, rows_to_pdf, rows_to_xlsx  # noqa: E402


def _export_bundle(kind: str) -> tuple[str, list[str], list[list[Any]]]:
    """Return title, headers, rows for export kind."""
    if kind == "leads":
        items = database.list_leads(500)
        headers = ["ID", "Name", "Phone", "Email", "Source", "Interest", "Status", "Reminder", "Created"]
        rows = [
            [i.get("id"), i.get("name"), i.get("phone"), i.get("email"), i.get("source"),
             i.get("interest"), i.get("status"), i.get("reminder_at"), i.get("created_at")]
            for i in items
        ]
        return "Leads", headers, rows
    if kind == "customers":
        items = database.list_customers(500)
        headers = ["ID", "Name", "Phone", "Email", "City", "Address", "Created"]
        rows = [
            [i.get("id"), i.get("name"), i.get("phone"), i.get("email"),
             i.get("city"), i.get("address"), i.get("created_at")]
            for i in items
        ]
        return "Customers", headers, rows
    if kind == "sales":
        items = database.list_sales(500)
        headers = ["ID", "Invoice", "Customer", "Phone", "Product", "Qty", "Amount", "Date", "Status"]
        rows = [
            [i.get("id"), i.get("invoice_no"), i.get("customer_name"), i.get("customer_phone"),
             i.get("product_name"), i.get("quantity"), i.get("amount"), i.get("sale_date"), i.get("status")]
            for i in items
        ]
        return "Sales", headers, rows
    if kind == "sales-returns":
        items = database.list_sales_returns(500)
        headers = ["ID", "Return No", "Invoice", "Customer", "Product", "Qty", "Amount", "Date", "Status"]
        rows = [
            [i.get("id"), i.get("return_no"), i.get("original_invoice"), i.get("customer_name"),
             i.get("product_name"), i.get("quantity"), i.get("amount"), i.get("return_date"), i.get("status")]
            for i in items
        ]
        return "Sales Returns", headers, rows
    if kind == "purchases":
        items = database.list_purchases(500)
        headers = ["ID", "Purchase No", "Supplier", "Product", "Category", "Qty", "Amount", "Date", "Status"]
        rows = [
            [i.get("id"), i.get("purchase_no"), i.get("supplier_name"), i.get("product_name"),
             i.get("category"), i.get("quantity"), i.get("amount"), i.get("purchase_date"), i.get("status")]
            for i in items
        ]
        return "Purchases", headers, rows
    if kind == "inventory":
        items = database.list_inventory(limit=500)
        headers = ["ID", "Name", "Category", "SKU", "Brand", "Qty", "Reorder", "Purchase", "Selling", "Status", "Web"]
        rows = [
            [i.get("id"), i.get("name"), i.get("category"), i.get("sku"), i.get("brand"),
             i.get("quantity"), i.get("reorder_level"), i.get("purchase_price"),
             i.get("selling_price"), i.get("status"), i.get("show_on_website")]
            for i in items
        ]
        return "Inventory", headers, rows
    if kind == "tiles":
        items = database.list_tiles(limit=500)
        headers = ["ID", "Name", "Model", "Colour", "Pattern", "Category", "Finish", "Active"]
        rows = [
            [i.get("id"), i.get("name"), i.get("model_number"), i.get("colour"),
             i.get("pattern"), i.get("material_category"), i.get("finish"), i.get("is_active")]
            for i in items
        ]
        return "Tiles", headers, rows
    if kind == "queries":
        contacts = database.list_contact_messages(300)
        enquiries = database.list_enquiries(300)
        headers = ["Type", "ID", "Name", "Phone", "Email", "Message/Product", "Status", "Created"]
        rows = []
        for i in contacts:
            rows.append(["contact", i.get("id"), i.get("name"), i.get("phone"), i.get("email"),
                         (i.get("message") or "")[:120], i.get("status"), i.get("created_at")])
        for i in enquiries:
            rows.append(["enquiry", i.get("id"), i.get("name"), i.get("phone"), i.get("email"),
                         i.get("product_name") or (i.get("message") or "")[:80],
                         i.get("status"), i.get("created_at")])
        return "Queries", headers, rows
    if kind == "dashboard":
        s = database.get_dashboard_stats()
        headers = ["Metric", "Value"]
        rows = [[k, v] for k, v in s.items() if k != "sales_by_day"]
        return "Dashboard", headers, rows
    raise HTTPException(status_code=400, detail="Unknown export kind")


@router.get("/export/{kind}")
async def admin_export(
    kind: str,
    format: str = "xlsx",
    _user: dict = Depends(require_admin),
):
    title, headers, rows = _export_bundle(kind)
    fmt = (format or "xlsx").lower()
    if fmt == "xlsx":
        data = rows_to_xlsx(title, headers, rows)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        fname = filename(f"chalukya_{kind}", "xlsx")
    elif fmt == "pdf":
        data = rows_to_pdf(title, headers, rows)
        media = "application/pdf"
        fname = filename(f"chalukya_{kind}", "pdf")
    else:
        raise HTTPException(status_code=400, detail="format must be xlsx or pdf")
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/backup/database")
async def admin_db_backup(_user: dict = Depends(require_admin)):
    """Download SQLite database file (proper backup, not spreadsheet)."""
    path = database.DATABASE_PATH
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Database file not found")
    database.log_user(_user.get("username", "admin"), "backup.database")
    return FileResponse(
        path=str(path),
        filename=filename("chalukya_showroom_backup", "db"),
        media_type="application/octet-stream",
    )


@router.get("/analytics")
async def admin_analytics(_user: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"success": True, "data": database.get_analytics_payload()}


# ---------------------------------------------------------------------------
# Reviews / feedback / ratings (admin moderation)
# ---------------------------------------------------------------------------

class ReviewStatusPayload(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(pending|approved|rejected)$")
    is_featured: Optional[int] = Field(default=None, ge=0, le=1)


@router.get("/reviews")
async def admin_list_reviews(
    _user: dict = Depends(require_admin),
    status: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "success": True,
        "items": database.list_reviews(status=status, limit=300),
    }


@router.patch("/reviews/{review_id}")
async def admin_update_review(
    review_id: int,
    payload: ReviewStatusPayload,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if payload.status is not None:
        fields["status"] = payload.status
    if payload.is_featured is not None:
        fields["is_featured"] = int(payload.is_featured)
    if not fields:
        raise HTTPException(status_code=400, detail="Nothing to update")
    if not database.update_review(review_id, **fields):
        raise HTTPException(status_code=404, detail="Review not found")
    database.log_user(
        _user.get("username", "admin"),
        "review.moderate",
        entity_type="review",
        entity_id=review_id,
        detail=str(fields),
    )
    return {"success": True, "message": "Review updated"}


@router.delete("/reviews/{review_id}")
async def admin_delete_review(
    review_id: int,
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not database.delete_review(review_id):
        raise HTTPException(status_code=404, detail="Review not found")
    database.log_user(
        _user.get("username", "admin"),
        "review.delete",
        entity_type="review",
        entity_id=review_id,
    )
    return {"success": True, "message": "Review deleted"}


@router.get("/logs/app")
async def admin_app_logs(
    _user: dict = Depends(require_admin),
    level: Optional[str] = None,
    limit: int = 200,
) -> dict[str, Any]:
    return {"success": True, "items": database.list_app_logs(limit=limit, level=level)}


@router.get("/logs/user")
async def admin_user_logs(
    _user: dict = Depends(require_admin),
    username: Optional[str] = None,
    limit: int = 200,
) -> dict[str, Any]:
    return {
        "success": True,
        "items": database.list_user_logs(limit=limit, username=username),
    }


@router.get("/logs/cli")
async def admin_logs_cli(
    _user: dict = Depends(require_admin),
    kind: str = "both",
    limit: int = 100,
) -> Response:
    """CLI-friendly plain-text dump of logs (timestamps)."""
    lines: list[str] = []
    lines.append(f"# Chalukya Tiles logs dump (UTC) · {database.utc_now_iso()}")
    lines.append(f"# kind={kind} limit={limit}")
    if kind in ("app", "both"):
        lines.append("## APPLICATION LOGS")
        for r in database.list_app_logs(limit=limit):
            lines.append(
                f"[{r.get('created_at')}] {r.get('level')} {r.get('source')}: {r.get('message')}"
                + (f" | {r.get('detail')}" if r.get("detail") else "")
            )
    if kind in ("user", "both"):
        lines.append("## USER LOGS")
        for r in database.list_user_logs(limit=limit):
            lines.append(
                f"[{r.get('created_at')}] user={r.get('username')} action={r.get('action')}"
                + (f" entity={r.get('entity_type')}:{r.get('entity_id')}" if r.get("entity_type") else "")
                + (f" | {r.get('detail')}" if r.get("detail") else "")
            )
    text = "\n".join(lines) + "\n"
    return Response(
        content=text,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename("chalukya_logs", "txt")}"'
        },
    )


@router.post("/import/json")
async def admin_import_json(
    payload: dict[str, Any],
    _user: dict = Depends(require_admin),
) -> dict[str, Any]:
    """
    Import JSON: { "inventory": [ {...}, ... ], "customers": [...] optional }
    Inventory rows use same fields as create (name, category, material_category, ...).
    """
    inv_rows = payload.get("inventory") or []
    cust_rows = payload.get("customers") or []
    created_inv = 0
    created_cust = 0
    errors: list[str] = []
    for i, row in enumerate(inv_rows):
        try:
            if not isinstance(row, dict) or not row.get("name") or not row.get("category"):
                errors.append(f"inventory[{i}]: name and category required")
                continue
            database.insert_inventory_item(
                name=str(row["name"]).strip(),
                category=str(row["category"]).strip(),
                brand=row.get("brand"),
                sku=row.get("sku"),
                description=row.get("description"),
                unit=row.get("unit") or "pieces",
                quantity=float(row.get("quantity") or 0),
                reorder_level=float(row.get("reorder_level") or 0),
                purchase_price=float(row.get("purchase_price") or 0),
                selling_price=float(row.get("selling_price") or 0),
                supplier=row.get("supplier"),
                tax_gst=float(row.get("tax_gst") or 0),
                status=row.get("status") or "active",
                item_date=row.get("item_date"),
                notes=row.get("notes"),
                colour=row.get("colour"),
                pattern=row.get("pattern") or "",
                show_on_website=int(row.get("show_on_website") or 0),
                material_category=row.get("material_category"),
                size_label=row.get("size_label"),
                finish=row.get("finish"),
                dim_length=row.get("dim_length"),
                dim_width=row.get("dim_width"),
                dim_unit=row.get("dim_unit"),
            )
            created_inv += 1
        except Exception as exc:  # pragma: no cover
            errors.append(f"inventory[{i}]: {exc}")
    for i, row in enumerate(cust_rows):
        try:
            if not isinstance(row, dict) or not row.get("name") or not row.get("phone"):
                errors.append(f"customers[{i}]: name and phone required")
                continue
            database.insert_customer(
                name=str(row["name"]).strip(),
                phone=str(row["phone"]).strip(),
                email=row.get("email"),
                address=row.get("address"),
                city=row.get("city"),
                notes=row.get("notes"),
            )
            created_cust += 1
        except database.DuplicateError as exc:
            errors.append(f"customers[{i}]: {exc.message}")
        except Exception as exc:  # pragma: no cover
            errors.append(f"customers[{i}]: {exc}")
    database.log_user(
        _user.get("username", "admin"),
        "import.json",
        detail=f"inv={created_inv} cust={created_cust} errors={len(errors)}",
    )
    database.log_app(
        f"JSON import finished inv={created_inv} cust={created_cust}",
        source="import",
        detail="; ".join(errors[:20]) if errors else None,
    )
    return {
        "success": True,
        "created_inventory": created_inv,
        "created_customers": created_cust,
        "errors": errors,
    }



