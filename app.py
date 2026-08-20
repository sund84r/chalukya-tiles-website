"""
Chalukya Tiles — Floor & Interior Tiles Showroom
Flask (WSGI) application entry point.

Serves:
- HTML pages from templates/
- Static assets from static/
- JSON API under /api/* (blueprints in api/)
- Admin panel under /admin/*
- SEO helpers: robots.txt, sitemap.xml
"""

from __future__ import annotations

import logging
import os
import random
from pathlib import Path
from urllib.parse import quote

from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
)
from werkzeug.exceptions import HTTPException, NotFound

from api.admin import bp as admin_bp
from api.enquiry import bp as enquiry_bp
from database.db import (
    CONCEPT_GALLERY_CATEGORIES,
    INVENTORY_CATEGORIES,
    category_slug,
    get_site_stats,
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

logger = logging.getLogger("chalukya")

# ---------------------------------------------------------------------------
# Environment / production security
# ---------------------------------------------------------------------------

APP_ENV = os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "development")).strip().lower()
IS_PRODUCTION = APP_ENV in {"production", "prod", "live"}

SITE_URL = os.environ.get("SITE_URL", "https://www.chalukyatiles.example").rstrip("/")

_DEV_SESSION_FALLBACK = "chalukya-tiles-dev-secret-change-me-in-production-v15"
SESSION_SECRET = os.environ.get("ADMIN_SECRET", "").strip() or _DEV_SESSION_FALLBACK

_https_only_env = os.environ.get("SESSION_HTTPS_ONLY", "").strip().lower()
SESSION_HTTPS_ONLY = (
    _https_only_env in {"1", "true", "yes"}
    if _https_only_env
    else IS_PRODUCTION
)

_allowed_hosts_raw = os.environ.get("ALLOWED_HOSTS", "").strip()
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_raw.split(",") if h.strip()]

_enable_docs_env = os.environ.get("ENABLE_API_DOCS", "").strip().lower()
ENABLE_API_DOCS = (
    _enable_docs_env in {"1", "true", "yes"}
    if _enable_docs_env
    else not IS_PRODUCTION
)

if IS_PRODUCTION:
    if SESSION_SECRET == _DEV_SESSION_FALLBACK or len(SESSION_SECRET) < 32:
        raise RuntimeError(
            "Production requires a strong ADMIN_SECRET env var "
            "(at least 32 random characters). "
            'Example: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    if SITE_URL.endswith("chalukyatiles.example"):
        logger.warning(
            "SITE_URL still looks like a placeholder (%s). "
            "Set SITE_URL=https://your-real-domain.com before launch.",
            SITE_URL,
        )
elif SESSION_SECRET == _DEV_SESSION_FALLBACK:
    logger.warning(
        "Using development ADMIN_SECRET. Set ADMIN_SECRET before hosting."
    )

APP_VERSION = "1.7.0-flask"

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


def create_app() -> Flask:
    """Flask application factory."""
    app = Flask(
        __name__,
        template_folder=str(TEMPLATES_DIR),
        static_folder=str(STATIC_DIR),
        static_url_path="/static",
    )

    app.config.update(
        SECRET_KEY=SESSION_SECRET,
        SESSION_COOKIE_NAME="chalukya_admin_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=SESSION_HTTPS_ONLY,
        PERMANENT_SESSION_LIFETIME=60 * 60 * 12,
        SITE_URL=SITE_URL,
        APP_VERSION=APP_VERSION,
        MAX_CONTENT_LENGTH=130 * 1024 * 1024,  # headroom above 120MB video limit
    )

    init_db()

    app.register_blueprint(enquiry_bp)
    app.register_blueprint(admin_bp)

    @app.before_request
    def _enforce_allowed_hosts():
        if not ALLOWED_HOSTS:
            return None
        host = (request.host or "").split(":")[0].lower()
        allowed = {h.lower() for h in ALLOWED_HOSTS}
        if host and host not in allowed and host not in {"127.0.0.1", "localhost"}:
            abort(400, description="Invalid Host header")
        return None

    @app.after_request
    def _security_headers(response: Response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        if request.is_secure or SESSION_HTTPS_ONLY:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        path = request.path or ""
        if path.startswith("/admin") or path == "/login":
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        return response

    def render_page(template_name: str, page_title: str, **extra):
        context = {
            "page_title": page_title,
            "brand_name": "Chalukya Tiles",
            "brand_tagline": "Floor & Interior Tiles Showroom",
            "site_url": SITE_URL,
            **extra,
        }
        return render_template(template_name, **context)

    def admin_user_from_session():
        return session.get("admin_user")

    # ------------------------------------------------------------------ pages

    @app.get("/")
    def home():
        trust_stats = get_site_stats()
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

        pool_products = list(inv)
        pool_concepts = list(concepts)
        random.shuffle(pool_products)
        random.shuffle(pool_concepts)

        featured_products: list = []
        pi, ci = 0, 0
        while len(featured_products) < 3 and (pi < len(pool_products) or ci < len(pool_concepts)):
            if pi < len(pool_products) and (
                len(featured_products) % 2 == 0 or ci >= len(pool_concepts)
            ):
                featured_products.append(pool_products[pi])
                pi += 1
            elif ci < len(pool_concepts):
                featured_products.append(pool_concepts[ci])
                ci += 1
            else:
                break
        random.shuffle(featured_products)

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
                        "image_path": p.get("image_path")
                        or "/static/images/product-vitrified.svg",
                        "title": p.get("name"),
                        "link": "/products",
                        "category_label": p.get("category") or "Product",
                    }
                )
        random.shuffle(gallery_preview)

        home_reviews = list_public_reviews(limit=8)

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
            tile["meta"] = (
                " · ".join(meta_bits)
                if meta_bits
                else (tile.get("model_number") or "New arrival")
            )
            tile["link"] = (
                "/contact?product="
                + quote(tile.get("name") or "")
                + "&category="
                + quote(tile.get("material_category") or "New Arrivals")
            )

        return render_page(
            "index.html",
            page_title="Home",
            active_page="home",
            collection_videos=collection_videos,
            featured_tiles=featured_products,
            featured_products=featured_products,
            gallery_preview_items=gallery_preview,
            home_reviews=home_reviews,
            new_arrivals=new_arrivals,
            trust_stats=trust_stats,
        )

    @app.get("/about")
    def about():
        return render_page("about.html", page_title="About Us", active_page="about")

    @app.get("/products")
    def products():
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
            "products.html",
            page_title="Products",
            active_page="products",
            db_tiles=[],
            inv_products=inv_products,
            inventory_categories=list(INVENTORY_CATEGORIES),
            product_subcategories=product_subcategories,
        )

    @app.get("/gallery")
    def gallery():
        concept_items = list_concept_gallery(active_only=True, limit=200)
        cat_labels = {s: lab for s, lab in CONCEPT_GALLERY_CATEGORIES}
        for item in concept_items:
            item["category_label"] = cat_labels.get(
                item.get("category"), item.get("category")
            )
        return render_page(
            "gallery.html",
            page_title="Concept Gallery",
            active_page="gallery",
            concept_gallery=concept_items,
            concept_gallery_categories=list(CONCEPT_GALLERY_CATEGORIES),
        )

    @app.get("/contact")
    def contact():
        return render_page("contact.html", page_title="Contact", active_page="contact")

    @app.get("/testimonials")
    def testimonials():
        reviews = list_public_reviews(limit=48)
        ratings = [int(r.get("rating") or 5) for r in reviews]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
        high_count = sum(1 for r in ratings if r >= 4)
        recommend_pct = int(round((high_count / len(ratings)) * 100)) if ratings else 0
        featured_quote = next(
            (r for r in reviews if int(r.get("is_featured") or 0) == 1), None
        )
        if featured_quote is None and reviews:
            featured_quote = reviews[0]
        return render_page(
            "testimonials.html",
            page_title="Testimonials",
            active_page="testimonials",
            public_reviews=reviews,
            reviews_avg=avg_rating,
            reviews_count=len(reviews),
            reviews_recommend_pct=recommend_pct,
            featured_review=featured_quote,
        )

    @app.get("/docs")
    def project_docs():
        return render_page(
            "docs.html",
            page_title="Project Documentation",
            active_page="docs",
        )

    @app.get("/user-guide")
    @app.get("/user-guide/")
    def user_guide():
        guide_path = BASE_DIR / "USER_GUIDE.html"
        if not guide_path.is_file():
            return (
                "<h1>User guide file missing</h1>"
                "<p>Expected USER_GUIDE.html in project root.</p>",
                404,
            )
        html = guide_path.read_text(encoding="utf-8")
        html = html.replace('href="static/', 'href="/static/')
        html = html.replace('src="static/', 'src="/static/')
        return Response(html, mimetype="text/html")

    @app.get("/login")
    def admin_login_page():
        if admin_user_from_session():
            return redirect("/admin")
        return render_page("admin_login.html", page_title="Login")

    @app.get("/admin/login")
    def admin_login_legacy_redirect():
        return redirect("/login")

    @app.get("/admin")
    @app.get("/admin/")
    def admin_dashboard_page():
        user = admin_user_from_session()
        if not user:
            return redirect("/login")
        return render_page(
            "admin.html",
            page_title="Admin Dashboard",
            admin_user=user,
        )

    @app.get("/robots.txt")
    def robots_txt():
        robots_path = STATIC_DIR / "robots.txt"
        if robots_path.is_file():
            text = robots_path.read_text(encoding="utf-8")
            if "Disallow: /admin" not in text:
                text = text.rstrip() + "\nDisallow: /admin\nDisallow: /admin/\n"
            if "Sitemap:" not in text:
                text = text.rstrip() + f"\n\nSitemap: {SITE_URL}/sitemap.xml\n"
            return Response(text, mimetype="text/plain")
        return Response(
            "User-agent: *\n"
            "Allow: /\n"
            "Disallow: /admin\n"
            "Disallow: /admin/\n"
            f"Sitemap: {SITE_URL}/sitemap.xml\n",
            mimetype="text/plain",
        )

    @app.get("/sitemap.xml")
    def sitemap_xml():
        urls = []
        for path in SITEMAP_PATHS:
            loc = f"{SITE_URL.rstrip('/')}{path}"
            priority = "1.0" if path == "/" else "0.8"
            urls.append(
                "  <url>\n"
                f"    <loc>{loc}</loc>\n"
                "    <changefreq>weekly</changefreq>\n"
                f"    <priority>{priority}</priority>\n"
                "  </url>"
            )
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(urls)
            + "\n</urlset>\n"
        )
        return Response(body, mimetype="application/xml")

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "success": True,
                "status": "ok",
                "service": "chalukya-tiles",
                "version": APP_VERSION,
                "runtime": "flask-wsgi",
            }
        )

    @app.errorhandler(404)
    def not_found(exc: NotFound):
        path = request.path or ""
        if path.startswith("/api/"):
            return jsonify({"detail": "Not Found"}), 404
        if path.startswith("/static/"):
            return exc
        return (
            render_template(
                "404.html",
                page_title="Not Found",
                brand_name="Chalukya Tiles",
                brand_tagline="Floor & Interior Tiles Showroom",
            ),
            404,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        path = request.path or ""
        if path.startswith("/api/"):
            return jsonify({"detail": exc.description or exc.name}), exc.code or 500
        return exc

    # Silence unused import if send_file needed by blueprints only
    _ = (send_file, ENABLE_API_DOCS)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8002")), debug=not IS_PRODUCTION)
