"""
Chalukya Tiles — Floor & Interior Tiles Showroom
FastAPI application entry point.

Serves:
- HTML pages from templates/
- Static assets from static/
- JSON API under /api/* (modular routers in api/)
- Admin panel under /admin/*
- SEO helpers: robots.txt, sitemap.xml
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from api.admin import router as admin_router
from api.enquiry import router as enquiry_router
import random

from database.db import (
    CONCEPT_GALLERY_CATEGORIES,
    INVENTORY_CATEGORIES,
    category_slug,
    init_db,
    list_collection_videos,
    list_concept_gallery,
    list_public_inventory_products,
    list_public_reviews,
    list_tiles,
    main_category_slug,
    sub_category_label,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Public site origin for sitemap absolute URLs (override in production)
SITE_URL = os.environ.get("SITE_URL", "https://www.chalukyatiles.example")

# Session secret for admin login (set ADMIN_SECRET in production)
SESSION_SECRET = os.environ.get(
    "ADMIN_SECRET",
    "chalukya-tiles-dev-secret-change-me-in-production-v15",
)

APP_VERSION = "1.6.15"

# ---------------------------------------------------------------------------
# Lifespan: init DB on startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize database tables when the server starts."""
    init_db()
    yield


# ---------------------------------------------------------------------------
# Security headers (lightweight, production-friendly defaults)
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        # Avoid indexing admin
        if request.url.path.startswith("/admin"):
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        return response


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Chalukya Tiles Showroom",
    description="Premium floor tiles and interior tiles showroom website API & pages.",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Session first (outermost added last in Starlette — add session before security)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="chalukya_admin_session",
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 12,  # 12 hours
)

# Static files: CSS, JS, images, videos, icons, uploads
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Modular API routers
app.include_router(enquiry_router)
app.include_router(admin_router)


# ---------------------------------------------------------------------------
# Page helpers
# ---------------------------------------------------------------------------

def render_page(request: Request, template_name: str, page_title: str, **extra) -> HTMLResponse:
    """
    Render an HTML template with shared context.

    Keeps page routes DRY. Extra context keys are merged into the template.
    """
    context = {
        "page_title": page_title,
        "brand_name": "Chalukya Tiles",
        "brand_tagline": "Floor & Interior Tiles Showroom",
        "site_url": SITE_URL,
        **extra,
    }
    # Starlette 1.x: TemplateResponse(request, name, context)
    return templates.TemplateResponse(request, template_name, context)


def admin_user_from_request(request: Request):
    return request.session.get("admin_user")


# ---------------------------------------------------------------------------
# HTML page routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse, tags=["pages"])
async def home(request: Request) -> HTMLResponse:
    """Home page — hero, shuffled posted products + concept gallery previews."""
    collection_videos = list_collection_videos(active_only=True, limit=6)

    inv = list_public_inventory_products(limit=50)
    for item in inv:
        item["link"] = "/products"
        item["badge"] = item.get("category") or "Product"
        item["kind"] = "product"

    concepts = list_concept_gallery(active_only=True, limit=50)
    cat_labels = {s: lab for s, lab in CONCEPT_GALLERY_CATEGORIES}
    for item in concepts:
        item["image_path"] = item.get("image_path")
        item["name"] = item.get("title")
        item["description"] = item.get("description") or cat_labels.get(
            item.get("category"), "Concept"
        )
        item["link"] = "/gallery"
        item["badge"] = cat_labels.get(item.get("category"), "Concept")
        item["kind"] = "concept"
        item["material_category"] = item["badge"]

    # Shuffle few items from both products + concept gallery for home
    pool_products = list(inv)
    pool_concepts = list(concepts)
    random.shuffle(pool_products)
    random.shuffle(pool_concepts)

    # Featured: mix up to 2 products + up to 2 concepts, then fill to 3
    featured_products: list = []
    pi, ci = 0, 0
    while len(featured_products) < 3 and (pi < len(pool_products) or ci < len(pool_concepts)):
        if pi < len(pool_products) and (len(featured_products) % 2 == 0 or ci >= len(pool_concepts)):
            featured_products.append(pool_products[pi])
            pi += 1
        elif ci < len(pool_concepts):
            featured_products.append(pool_concepts[ci])
            ci += 1
        else:
            break
    random.shuffle(featured_products)

    # Gallery preview: prefer concepts, top up with product images
    gallery_preview = [
        {
            "image_path": c.get("image_path"),
            "title": c.get("title") or c.get("name"),
            "link": "/gallery",
            "category_label": c.get("badge") or "Concept",
        }
        for c in pool_concepts[:5]
    ]
    if len(gallery_preview) < 5:
        for p in pool_products:
            if len(gallery_preview) >= 5:
                break
            gallery_preview.append(
                {
                    "image_path": p.get("image_path") or "/static/images/product-vitrified.svg",
                    "title": p.get("name"),
                    "link": "/products",
                    "category_label": p.get("category") or "Product",
                }
            )
    random.shuffle(gallery_preview)

    home_reviews = list_public_reviews(limit=8)

    # New Arrivals (Admin → New Arrivals / tiles) → Home "Latest Collections"
    new_arrivals = list_tiles(active_only=True, limit=12)
    for tile in new_arrivals:
        meta_bits = [
            b
            for b in (
                tile.get("material_category"),
                tile.get("colour"),
                tile.get("size_label"),
                tile.get("finish"),
            )
            if b
        ]
        tile["meta"] = " · ".join(meta_bits) if meta_bits else (tile.get("model_number") or "New arrival")
        tile["link"] = (
            "/contact?product="
            + quote(tile.get("name") or "")
            + "&category="
            + quote(tile.get("material_category") or "New Arrivals")
        )

    return render_page(
        request,
        "index.html",
        page_title="Home",
        active_page="home",
        collection_videos=collection_videos,
        featured_tiles=featured_products,  # template still uses this name
        featured_products=featured_products,
        gallery_preview_items=gallery_preview,
        home_reviews=home_reviews,
        new_arrivals=new_arrivals,
    )


@app.get("/about", response_class=HTMLResponse, tags=["pages"])
async def about(request: Request) -> HTMLResponse:
    """About page — story, mission, vision, timeline, achievements."""
    return render_page(
        request,
        "about.html",
        page_title="About Us",
        active_page="about",
    )


@app.get("/products", response_class=HTMLResponse, tags=["pages"])
async def products(request: Request) -> HTMLResponse:
    """Products catalogue — only inventory items posted to the website."""
    inv_products = list_public_inventory_products(limit=200)
    for item in inv_products:
        main_label = (item.get("category") or "Others").strip()
        sub_label = sub_category_label(item)
        item["main_category"] = main_label
        item["main_category_slug"] = main_category_slug(main_label)
        item["sub_category_label"] = sub_label
        item["sub_category_slug"] = category_slug(sub_label)
        item["category_slug"] = item["sub_category_slug"]
        item["enquire_url"] = (
            "/contact?product="
            + quote(item.get("name") or "")
            + "&category="
            + quote(sub_label if sub_label != "General" else main_label)
        )
        item["_src"] = "inventory"

    sub_map: dict[str, dict[str, str]] = {}
    for item in inv_products:
        m = item["main_category_slug"]
        s = item["sub_category_slug"]
        sub_map.setdefault(m, {})[s] = item["sub_category_label"]

    product_subcategories = {
        main: [
            {"slug": s, "label": lab}
            for s, lab in sorted(subs.items(), key=lambda x: x[1].lower())
        ]
        for main, subs in sub_map.items()
    }

    return render_page(
        request,
        "products.html",
        page_title="Products",
        active_page="products",
        db_tiles=[],  # no New Arrivals / templates on Products
        inv_products=inv_products,
        inventory_categories=list(INVENTORY_CATEGORIES),
        product_subcategories=product_subcategories,
    )


@app.get("/gallery", response_class=HTMLResponse, tags=["pages"])
async def gallery(request: Request) -> HTMLResponse:
    """Concept Gallery — only admin-uploaded pictures (no static templates)."""
    concept_items = list_concept_gallery(active_only=True, limit=200)
    cat_labels = {s: lab for s, lab in CONCEPT_GALLERY_CATEGORIES}
    for item in concept_items:
        item["category_label"] = cat_labels.get(item.get("category"), item.get("category"))
    return render_page(
        request,
        "gallery.html",
        page_title="Concept Gallery",
        active_page="gallery",
        concept_gallery=concept_items,
        concept_gallery_categories=list(CONCEPT_GALLERY_CATEGORIES),
    )


@app.get("/contact", response_class=HTMLResponse, tags=["pages"])
async def contact(request: Request) -> HTMLResponse:
    """Contact page — map, form, hours, social links."""
    return render_page(
        request,
        "contact.html",
        page_title="Contact",
        active_page="contact",
    )


@app.get("/testimonials", response_class=HTMLResponse, tags=["pages"])
async def testimonials(request: Request) -> HTMLResponse:
    """Customer testimonials — approved reviews from Admin moderation."""
    reviews = list_public_reviews(limit=48)
    ratings = [int(r.get("rating") or 5) for r in reviews]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
    high_count = sum(1 for r in ratings if r >= 4)
    recommend_pct = int(round((high_count / len(ratings)) * 100)) if ratings else 0
    featured_quote = next((r for r in reviews if int(r.get("is_featured") or 0) == 1), None)
    if featured_quote is None and reviews:
        featured_quote = reviews[0]
    return render_page(
        request,
        "testimonials.html",
        page_title="Testimonials",
        active_page="testimonials",
        public_reviews=reviews,
        reviews_avg=avg_rating,
        reviews_count=len(reviews),
        reviews_recommend_pct=recommend_pct,
        featured_review=featured_quote,
    )


@app.get("/docs", response_class=HTMLResponse, tags=["pages"])
async def project_docs(request: Request) -> HTMLResponse:
    """Full project documentation — architecture, structure, features, usage."""
    return render_page(
        request,
        "docs.html",
        page_title="Project Documentation",
        active_page="docs",
    )


@app.get("/user-guide", response_class=HTMLResponse, tags=["pages"], include_in_schema=False)
@app.get("/user-guide/", response_class=HTMLResponse, tags=["pages"], include_in_schema=False)
async def user_guide() -> HTMLResponse:
    """Complete standalone user guide handbook (also on disk as USER_GUIDE.html)."""
    guide_path = BASE_DIR / "USER_GUIDE.html"
    if not guide_path.is_file():
        return HTMLResponse(
            content="<h1>User guide file missing</h1><p>Expected USER_GUIDE.html in project root.</p>",
            status_code=404,
        )
    html = guide_path.read_text(encoding="utf-8")
    # When served from /user-guide, force absolute static paths
    html = html.replace('href="static/', 'href="/static/')
    html = html.replace('src="static/', 'src="/static/')
    return HTMLResponse(content=html, status_code=200)


# ---------------------------------------------------------------------------
# Admin HTML pages
# ---------------------------------------------------------------------------


@app.get("/login", response_class=HTMLResponse, tags=["admin"], include_in_schema=False)
async def admin_login_page(request: Request) -> HTMLResponse:
    if admin_user_from_request(request):
        return RedirectResponse(url="/admin", status_code=302)
    return render_page(
        request,
        "admin_login.html",
        page_title="Login",
    )


@app.get("/admin/login", include_in_schema=False)
async def admin_login_legacy_redirect() -> RedirectResponse:
    """Old URL → /login."""
    return RedirectResponse(url="/login", status_code=302)


@app.get("/admin", response_class=HTMLResponse, tags=["admin"], include_in_schema=False)
@app.get("/admin/", response_class=HTMLResponse, tags=["admin"], include_in_schema=False)
async def admin_dashboard_page(request: Request):
    user = admin_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return render_page(
        request,
        "admin.html",
        page_title="Admin Dashboard",
        admin_user=user,
    )


# ---------------------------------------------------------------------------
# SEO: robots.txt + sitemap.xml
# ---------------------------------------------------------------------------

SITEMAP_PATHS = (
    "/",
    "/about",
    "/products",
    "/gallery",
    "/testimonials",
    "/contact",
    "/docs",
    "/user-guide",
)


@app.get("/robots.txt", response_class=PlainTextResponse, tags=["seo"], include_in_schema=False)
async def robots_txt() -> str:
    """Serve robots.txt (also available under /static/robots.txt)."""
    robots_path = STATIC_DIR / "robots.txt"
    if robots_path.is_file():
        text = robots_path.read_text(encoding="utf-8")
        if "Disallow: /admin" not in text:
            text = text.rstrip() + "\nDisallow: /admin\nDisallow: /admin/\n"
        if "Sitemap:" not in text:
            text = text.rstrip() + f"\n\nSitemap: {SITE_URL}/sitemap.xml\n"
        return text
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /admin/\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )


@app.get("/sitemap.xml", tags=["seo"], include_in_schema=False)
async def sitemap_xml() -> Response:
    """Minimal XML sitemap for public HTML pages."""
    urls = []
    for path in SITEMAP_PATHS:
        loc = f"{SITE_URL.rstrip('/')}{path}"
        priority = "1.0" if path == "/" else "0.8"
        urls.append(
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>"
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    return Response(content=body, media_type="application/xml")


# ---------------------------------------------------------------------------
# Health check (useful for deployment)
# ---------------------------------------------------------------------------


@app.get("/api/health", tags=["system"])
async def health() -> dict:
    """Lightweight health endpoint for monitoring / load balancers."""
    return {
        "success": True,
        "status": "ok",
        "service": "chalukya-tiles",
        "version": APP_VERSION,
    }


# ---------------------------------------------------------------------------
# 404 handler
# ---------------------------------------------------------------------------


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Render a branded HTML 404 for missing pages; keep default handling for API/static."""
    if exc.status_code == 404:
        path = request.url.path
        if not path.startswith("/api/") and not path.startswith("/static/"):
            return templates.TemplateResponse(
                request,
                "404.html",
                {
                    "page_title": "Not Found",
                    "brand_name": "Chalukya Tiles",
                    "brand_tagline": "Floor & Interior Tiles Showroom",
                },
                status_code=404,
            )
    return await http_exception_handler(request, exc)
