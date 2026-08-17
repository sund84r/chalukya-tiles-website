# Chalukya Tiles — Floor & Interior Tiles Showroom

A modern, premium, production-ready website for a floor tiles and interior tiles showroom.

**Stack:** FastAPI (Python) · HTML5 · CSS3 · Vanilla JavaScript (ES6+)  
**No** React, Vue, Angular, Bootstrap, or jQuery.

---

## Features

- Mobile-first, fully responsive UI
- Premium theme (elegant blue + white)
- Sticky navbar (transparent → solid), hamburger menu
- Hero with optional showroom video + typing headline
- **Collection videos** mid-down homepage (admin-uploaded)
- Product catalogue with 9 category filters + **admin-uploaded tiles**
- Masonry gallery + accessible lightbox (images & video)
- Testimonials with ratings
- Contact & product enquiry forms → SQLite via JSON API
- **Admin panel** (`/admin`): dashboard analytics, sales, leads, queries, customers, tile media + video upload
- SEO: semantic HTML, meta tags, `robots.txt`, `sitemap.xml`, JSON-LD
- Accessibility: skip link, ARIA, keyboard nav, focus styles
- Performance: lazy images/videos, modular CSS/JS, minimal dependencies
- Security headers middleware
- Branded 404 page

---

## Quick start (Windows)

```powershell
cd path\to\chalukya-tiles-website
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8002
```

Open **http://127.0.0.1:8002**  
Admin panel: **http://127.0.0.1:8002/admin**  
User guide: **http://127.0.0.1:8002/user-guide** (file: `USER_GUIDE.html`)  
Default login: `admin` / `chalukya@2026` — **change before production**

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Clone from GitHub

```powershell
git clone https://github.com/YOUR_USERNAME/chalukya-tiles-website.git
cd chalukya-tiles-website
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8002
```

SQLite database (`database/showroom.db`) and uploaded media are **local-only** (gitignored). They are created at runtime / via Admin.

---

## Git workflow (avoid merge conflicts)

Solo / small team on **`main`** only:

1. Before you start work: `git pull origin main`
2. Make changes in VS Code
3. Commit often with clear messages
4. Push: `git push origin main`
5. **Never** force-push to `main` unless you know why
6. Do **not** commit `.venv/`, `.env`, `database/*.db`, or `static/uploads/*` media

If two people edit the same file: pull first, resolve in VS Code, then commit and push.

---

## Project structure

```
website_tiles1/
├── app.py                 # FastAPI entry, pages, SEO, 404
├── requirements.txt
├── README.md
├── .gitignore
├── templates/             # HTML pages
│   ├── index.html
│   ├── about.html
│   ├── products.html
│   ├── gallery.html
│   ├── contact.html
│   ├── testimonials.html
│   └── 404.html
├── static/
│   ├── css/               # Modular stylesheets
│   ├── js/                # Modular scripts
│   ├── images/            # Photos / SVG placeholders
│   ├── videos/            # Optional showroom.mp4
│   ├── icons/             # favicon.svg
│   └── robots.txt
├── api/
│   └── enquiry.py         # POST /api/contact, /api/enquiry
├── database/
│   ├── db.py              # SQLite layer (MySQL-ready design)
│   └── showroom.db        # Created at runtime (gitignored)
└── assets/                # Source brand files (not public)
```

---

## Routes

### Pages

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home |
| GET | `/about` | About |
| GET | `/products` | Products (+ `?category=`) |
| GET | `/gallery` | Gallery (+ `?category=`) |
| GET | `/testimonials` | Testimonials |
| GET | `/contact` | Contact (+ `?product=&category=` for enquiry) |
| GET | `/docs` | Full project documentation (architecture handbook) |

### API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/contact` | Contact form → SQLite |
| POST | `/api/enquiry` | Product enquiry → SQLite |
| GET | `/api/health` | Health check |
| GET | `/api/docs` | OpenAPI Swagger UI |
| * | `/api/admin/*` | Admin auth, dashboard, tiles, videos, sales, leads, customers, queries |

### Admin

| Path | Description |
|------|-------------|
| `/admin/login` | Admin sign-in |
| `/admin` | Dashboard + media + CRM tables |

Tile uploads need: **name, model number, colour, material category, image**.  
Collection videos appear on the homepage mid-section when marked active.

### SEO

| Path | Description |
|------|-------------|
| `/robots.txt` | Crawler rules |
| `/sitemap.xml` | URL sitemap |

---

## Contact / enquiry API example

```powershell
curl -X POST http://127.0.0.1:8000/api/contact `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"Jane Doe\",\"phone\":\"+91 9876543210\",\"email\":\"jane@example.com\",\"message\":\"Looking for bathroom tiles.\"}"
```

Product enquiry payload may also include `product_name` and `product_category`.

---

## Database

- **SQLite** file: `database/showroom.db` (auto-created)
- Tables: `contact_messages`, `enquiries`
- Connection logic lives in `database/db.py` so you can later swap to **MySQL** without changing route handlers

### MySQL migration notes

1. Create equivalent tables with `INT AUTO_INCREMENT`, `VARCHAR`, `TEXT`, `DATETIME`
2. Replace `get_connection()` with a MySQL driver (e.g. PyMySQL / mysqlclient)
3. Keep the same column names used by `insert_*` helpers

---

## Frontend conventions

- No inline CSS or JavaScript in page modules
- CSS variables for theme tokens (`static/css/main.css`)
- Feature CSS: `navbar`, `hero`, `products`, `gallery`, `contact`, `footer`, `animations`
- Feature JS: `navbar`, `slider`, `gallery`, `contact`, `api`, `main`
- Lazy-loaded images; video `preload="none"` where appropriate
- `prefers-reduced-motion` respected for animations

---

## Brand details (Chalukya Tiles)

| Item | Value |
|------|-------|
| Brand name | Chalukya Tiles |
| Logo | `static/icons/logo-chalukya.png` |
| Phone / WhatsApp | 99407 18307 |
| Email | chalukyatiles@gmail.com |
| Address | No:370, Sathy main road, Kurumbapalayam, Coimbatore, TN 641 107 |
| GSTIN | 33AAWFC0185C1ZL |
| Managing Director | C. Venkatesan, MBA |
| Site URL (sitemap/JSON-LD) | `SITE_URL` in `app.py` (set real domain for production) |
| Product images | SVG placeholders in `static/images/` (replace with photos) |
| Hero video | Optional: `static/videos/showroom.mp4` |

---

## Production

```powershell
# Example (no reload)
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 2
```

Recommendations:

- Reverse proxy with HTTPS (Nginx, Caddy, IIS + ARR)
- Set a real `SITE_URL` in `app.py`
- Back up `database/showroom.db` regularly
- Replace SVG placeholders with optimized WebP/JPEG
- Add real map embed query for your exact address
- Review CORS only if a separate frontend origin will call the API

---

## Color theme

| Role | Hex | Use |
|------|-----|-----|
| Primary | `#FFFFFF` | Backgrounds |
| Secondary | `#1A1A1A` | Text, dark sections |
| Accent | `#8A8680` | Muted UI |
| Highlight | `#C4A574` | CTAs, accents |

Fonts: **Inter** + **Poppins** (Google Fonts)

---

## Module build status

All modules complete:

1. Foundation  
2. Backend core  
3. Global CSS & design tokens  
4. Navbar, footer & animations  
5. Home  
6. About  
7. Products  
8. Gallery  
9. Testimonials  
10. Contact & form wiring  
11. Polish (SEO, 404, docs, QA)  

---

## License

Private / proprietary — update as needed for your business.
