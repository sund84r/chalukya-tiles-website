# PROJECT_MEMORY.md — Chalukya Tiles Showroom

> Permanent project memory. Update after every module or session.  
> **Do not delete useful history** — append or revise carefully.

---

## Project overview

**Name:** Chalukya Tiles — Floor & Interior Tiles Showroom  
**Workspace:** `C:\Users\Admin\Downloads\ChalukyaTiles_website\website_tiles1`  
**GitHub:** https://github.com/sund84r/chalukya-tiles-website (private, account **sund84r**)  
**Branch:** `main` (tracks `origin/main`)  
**Type:** Full-stack marketing / showroom website (SSR HTML + JSON API)  
**Goal:** Premium, modern, mobile-first, SEO-friendly, accessible, fast-loading website for a floor tiles and interior tiles showroom. Production-ready and easy to maintain.

**Brand:** Chalukya Tiles  
**Logo:** `static/icons/logo-chalukya.png` (source: official “logo final.png”; navy mark + cyan accent; no CSS recolour)  
**Theme:** Luxury **black + shine gold** (marble showroom); product media stays champagne-light so tile photos stay true  
**Home hero:** `static/images/hero-luxury.jpg` (full-bleed showroom; Chalukya logo removed from hero)  
**Phone / WhatsApp:** 99407 18307 (`+919940718307`)  
**Email:** chalukyatiles@gmail.com  
**Address:** No:370, Sathy main road, Kurumbapalayam, Coimbatore, TN - 641 107  
**GSTIN:** 33AAWFC0185C1ZL  
**MD:** C. Venkatesan, MBA

**Deploy note (2026-08):** Owner has a **domain** but **no host yet**. Domain alone cannot serve this FastAPI app. Needs a VPS/PaaS. SQLite can live on the **same host** first; separate MySQL later is optional. Cannot run as static-only without a major rewrite (admin, products, forms, reviews all need DB).

---

## Tech stack

| Layer | Choice | Notes |
|-------|--------|--------|
| Frontend | HTML5, CSS3, Vanilla JS (ES6+) | No React/Vue/Angular/Bootstrap/jQuery |
| Backend | Python, FastAPI | Uvicorn ASGI server |
| Templates | Jinja2 | Served by FastAPI |
| Database | SQLite (`database/showroom.db`) | Runtime file gitignored; MySQL-ready design |
| Validation | Pydantic v2 | API request models |
| Fonts | Google Fonts — Inter + Poppins | Linked from templates |
| Platform | Windows local + GitHub remote | VS Code; clone anywhere |
| VCS | Git + GitHub CLI | Logged in as **sund84r** |

**Strict exclusions:** React, Vue, Angular, Bootstrap, jQuery, unnecessary libraries.

**Git ignores (do not commit):** `.venv/`, `.env*`, `database/*.db`, uploaded media under `static/uploads/**` (keep `.gitkeep` + README only).

---

## Folder structure

```
website_tiles1/
├── PROJECT_MEMORY.md          # This file — permanent memory
├── app.py                     # FastAPI entry, pages, SEO, 404, security headers
├── requirements.txt
├── README.md                  # Run + clone + git workflow notes
├── .gitignore
├── .gitattributes             # LF normalization (fewer Windows merge issues)
├── templates/
│   ├── index.html             # Home
│   ├── about.html
│   ├── products.html
│   ├── gallery.html
│   ├── contact.html
│   ├── testimonials.html
│   ├── 404.html
│   └── docs.html              # Full project documentation (architecture/features)
├── static/
│   ├── css/
│   │   ├── main.css           # Tokens, layout, forms, about/testimonials, utilities
│   │   ├── navbar.css
│   │   ├── hero.css           # Home hero + home sections
│   │   ├── products.css
│   │   ├── gallery.css
│   │   ├── contact.css
│   │   ├── docs.css           # Project documentation page
│   │   ├── footer.css
│   │   └── animations.css
│   ├── js/
│   │   ├── main.js            # Loader, scroll-top, ripple, IO, counters, typing, product filters
│   │   ├── navbar.js
│   │   ├── slider.js          # Reviews carousel + hero video
│   │   ├── gallery.js         # Gallery filters + lightbox
│   │   ├── contact.js         # Form validation + Fetch submit
│   │   └── api.js             # ChalukyaAPI helpers
│   ├── images/                # SVG placeholders + README
│   ├── videos/                # Optional showroom.mp4 + README
│   ├── icons/favicon.svg
│   └── robots.txt
├── api/
│   ├── __init__.py
│   └── enquiry.py             # POST /api/contact, POST /api/enquiry
├── database/
│   ├── __init__.py
│   ├── db.py                  # SQLite connection, schema, inserts
│   └── showroom.db            # Runtime DB (gitignored)
└── assets/                    # Non-public brand sources + README
```

---

## Current architecture

```
Browser
  │
  ├─ GET HTML pages ──► FastAPI (app.py) ──► Jinja2 templates/
  ├─ GET /static/*   ──► StaticFiles
  └─ POST /api/*     ──► api/enquiry.py ──► database/db.py ──► SQLite
```

**Patterns:**
- Modular CSS/JS by feature (no inline CSS/JS on product pages)
- Shared design tokens in `:root` (`main.css`)
- Sticky navbar: transparent on home hero, solid on inner pages / scroll
- Forms: Vanilla JS validation → `ChalukyaAPI` Fetch → FastAPI Pydantic → SQLite
- Product enquire deep-link: `/contact?product=…&category=…` → `POST /api/enquiry`
- SEO: meta tags, JSON-LD (home), `/robots.txt`, `/sitemap.xml`, security headers
- A11y: skip link, ARIA, keyboard lightbox, focus-visible, reduced-motion

**Config knobs:**
- `SITE_URL` in `app.py` (sitemap + JSON-LD absolute URLs)
- Brand strings in templates + `render_page()` context

---

## Completed modules

| # | Module | Status |
|---|--------|--------|
| 1 | Project Foundation (structure, requirements, README, gitignore) | ✅ Done |
| 2 | Backend Core (app.py, database/db.py, api/enquiry.py) | ✅ Done |
| 3 | Global CSS & design tokens (main.css) | ✅ Done |
| 4 | Navbar, Footer & Animations + main.js, navbar.js, api.js | ✅ Done |
| 5 | Home Page (index.html, hero.css, slider.js, SVG placeholders) | ✅ Done |
| 6 | About Page (about.html + about styles in main.css) | ✅ Done |
| 7 | Products Page (products.html, products.css, filters in main.js) | ✅ Done |
| 8 | Gallery Page (gallery.html, gallery.css, gallery.js) | ✅ Done |
| 9 | Testimonials Page (testimonials.html + styles in main.css) | ✅ Done |
| 10 | Contact Page & form wiring (contact.html/css/js) | ✅ Done |
| 11 | Polish (404, robots, sitemap, security headers, README, QA) | ✅ Done |
| 12 | Project memory + full documentation HTML page | ✅ Done (this session) |

---

## Pending modules

| Item | Priority | Notes |
|------|----------|--------|
| Buy/configure **host** (VPS recommended) + point domain DNS | High | Domain exists; app not public until host runs uvicorn |
| Production `SITE_URL` + `ADMIN_SECRET` + change admin password | High | Before public launch |
| Real inventory photos (Post in website) + Concept Gallery + New Arrivals | High | Content via Admin |
| Collection videos via Admin | Medium | Homepage mid-section |
| Backup `showroom.db` + `static/uploads/` regularly | High | Not on GitHub |
| Sync USER_GUIDE.html / docs.html to v1.6.12+ features | Medium | Docs lag behind admin/reviews |
| MySQL migration | Optional | After host; SQLite fine for first deploy |
| Email on form/review submit | Optional | Currently store-only |
| Multi-language | Optional | Not started |

---

## Files created (cumulative)

### Root
- `app.py`, `requirements.txt`, `README.md`, `.gitignore`, `PROJECT_MEMORY.md`

### Backend
- `api/__init__.py`, `api/enquiry.py`
- `database/__init__.py`, `database/db.py`
- `database/showroom.db` (runtime)

### Templates
- `index.html`, `about.html`, `products.html`, `gallery.html`, `contact.html`, `testimonials.html`, `404.html`, `docs.html`

### CSS
- `static/css/main.css`, `navbar.css`, `hero.css`, `products.css`, `gallery.css`, `contact.css`, `docs.css`, `footer.css`, `animations.css`

### JS
- `static/js/main.js`, `navbar.js`, `slider.js`, `gallery.js`, `contact.js`, `api.js`

### Media / SEO / docs
- `static/icons/favicon.svg`
- Multiple SVG placeholders under `static/images/`
- `static/robots.txt`
- `static/images/README.md`, `static/videos/README.md`, `assets/README.md`

---

## Files modified (notable)

| File | Why |
|------|-----|
| `app.py` | Pages, SEO routes, security middleware, 404, `SITE_URL`, docs route |
| `main.css` | About, testimonials, error-page, design tokens |
| `main.js` | Product filters, global UI behaviors |
| `README.md` | Full production documentation |
| Templates | Iterative content/SEO; home JSON-LD + canonical |
| `PROJECT_MEMORY.md` | Created/updated this session |

---

## API endpoints

| Method | Path | Body / notes | Response |
|--------|------|--------------|----------|
| GET | `/` | — | HTML Home |
| GET | `/about` | — | HTML |
| GET | `/products` | `?category=` optional | HTML |
| GET | `/gallery` | `?category=` optional | HTML |
| GET | `/testimonials` | — | HTML |
| GET | `/contact` | `?product=&category=` optional | HTML |
| GET | `/docs` | — | HTML project documentation |
| POST | `/api/contact` | JSON: name, phone, email, message | 201 JSON success |
| POST | `/api/enquiry` | JSON: + optional product_name, product_category | 201 JSON success |
| POST | `/api/review` | JSON: name, message, rating (1–5), optional email/phone/title | 201 pending until admin |
| GET | `/api/admin/reviews` | Admin session; optional `?status=` | List reviews |
| PATCH | `/api/admin/reviews/{id}` | JSON: status and/or is_featured | Moderate |
| DELETE | `/api/admin/reviews/{id}` | Admin session | Delete review |
| GET | `/api/health` | — | JSON health |
| GET | `/api/docs` | — | Swagger UI |
| GET | `/robots.txt` | — | text |
| GET | `/sitemap.xml` | — | XML (update `SITE_URL`) |

**Success shape:**
```json
{ "success": true, "message": "...", "id": 1 }
```

---

## Database changes

### Schema (SQLite — `database/showroom.db`)

**`contact_messages`**
- id INTEGER PK AUTOINCREMENT  
- name VARCHAR(120) NOT NULL  
- phone VARCHAR(40) NOT NULL  
- email VARCHAR(180) NOT NULL  
- message TEXT NOT NULL  
- created_at TEXT NOT NULL (ISO UTC)  
- status VARCHAR(40) DEFAULT 'new'  

**`enquiries`**
- id INTEGER PK AUTOINCREMENT  
- name, phone, email, message (same idea)  
- product_name VARCHAR(200) NULL  
- product_category VARCHAR(100) NULL  
- created_at TEXT NOT NULL  
- status VARCHAR(40) DEFAULT 'new'  

**Indexes:** `created_at` on both tables.  
**Init:** `init_db()` on app lifespan startup.  
**Helpers:** `insert_contact_message`, `insert_enquiry`, `list_contact_messages`, `list_enquiries`.

No migrations framework yet — schema created with `CREATE TABLE IF NOT EXISTS`.

---

## Current TODO

- [x] Complete modules 1–11 (full site)
- [x] PROJECT_MEMORY.md permanent memory
- [x] HTML documentation page (`/docs`)
- [ ] Replace placeholder brand + SITE_URL for real business
- [ ] Replace SVG images with real photography
- [ ] Add showroom.mp4
- [ ] Optional: admin list of messages/enquiries
- [ ] Optional: email alerts on new submissions
- [ ] Keep PROJECT_MEMORY.md updated every session

---

## Next development task

1. **Launch prep:** Update brand name, contact info, `SITE_URL`, map embeds.  
2. **Media:** Drop real images/videos into `static/`.  
3. **Optional feature:** Simple password-protected admin page to list SQLite contact/enquiry rows (helpers already in `database/db.py`).  
4. Always update **this file** + regenerate CONTINUE PROMPT at session end.

---

## Current project version

**Version:** `1.6.14`  
**App version string:** `1.6.14` in FastAPI metadata / health  
**Memory schema version:** `1.6` (inventory, finance, exports, logs, charts, Concept Gallery, reviews, GitHub, user management)  
**Last memory update:** 2026-08-17 (Admin User Management + permissions)

| Version | Date | Notes |
|---------|------|--------|
| 1.0.0 | 2026-07-15 | Modules 1–11 complete, production-ready site |
| 1.1.0 | 2026-07-15 | PROJECT_MEMORY.md + `/docs` documentation page |
| 1.2.0 | 2026-07-23 | Rebrand Prestige → Chalukya Tiles (logo, contact, colors) |
| 1.3.0 | 2026-07-23 | Hero big centered logo; text collision fix; blue-white theme (later red) |
| 1.3.1 | 2026-07-23 | Navbar text brand; hero center vector+text blended (no PNG/white plate) |
| 1.3.2 | 2026-07-23 | Transparent logo PNG (removebg) in navbar + hero center + footer |
| 1.3.3 | 2026-07-23 | Nav/footer show name text; logo upscaled/sharpened HD assets |
| 1.3.4 | 2026-07-23 | New Picsart logo; fixed reviews carousel swipe (pixel transform) |
| 1.4.0 | 2026-07-23 | Elegant red theme sitewide; fonts Playfair Display + Manrope |
| 1.4.2 | 2026-07-23 | Reverted color palette to elegant blue + white |
| 1.4.3 | 2026-07-23 | Fonts restored to original Inter + Poppins |
| 1.5.0 | 2026-08-11 | Full admin panel: dashboard analytics, tile media upload, collection videos, sales/leads/customers/queries |
| 1.5.1 | 2026-08-11 | Mobile menu fix: drawer portal + z-index + no backdrop-filter clip when scrolled |
| 1.5.2 | 2026-08-11 | Admin sidebar collapsible menu + open/close switch |
| 1.6.0 | 2026-08-13 | Inventory, sales return, purchases, unique customers/tiles, exports xlsx/pdf, Concept Gallery rename, leads/queries comms |
| 1.6.7 | 2026-08-14 | Concept Gallery admin uploads only (no static templates) |
| 1.6.8 | 2026-08-14 | Products inventory-only; home shuffle products+concepts; public reviews FAB + admin moderation |
| 1.6.9 | 2026-08-14 | Home Latest Collections / New Arrivals driven by Admin → New Arrivals (active tiles) |
| 1.6.10 | 2026-08-17 | New official logo (logo final.png); natural colours |
| 1.6.11 | 2026-08-17 | Tried ivory·walnut·sage theme; logo no white plate; remove duplicate nav brand text |
| 1.6.12 | 2026-08-17 | Final theme: white + light Oxford blue; tile cards pure white; GitHub private repo live |
| 1.6.13 | 2026-08-17 | Admin User Management: create staff users + checkbox tab permissions (superadmin only) |
| 1.6.14 | 2026-08-20 | Luxury black+gold theme; hero uses marble showroom image (logo removed from hero) |

---

## Session log (append-only style)

### Session — luxury black + gold + hero image (v1.6.14)
- Home hero: removed Chalukya logo; full-bleed `hero-luxury.jpg` from ChatGPT showroom PNG
- Soft vignette overlay only (no white wash) so marble/gold stay vivid
- Sitewide + admin palette: black `#0a0a0a` / gold `#d4af37` / champagne accents
- Product/gallery media backgrounds stay light champagne for true tile colour
- Nav/footer/admin logo sit on soft champagne plate for contrast on black chrome
- Cache `?v181-luxury`

### Session — Admin User Management (v1.6.13)
- New System menu: **User Management** (visible only to **superadmin** / main `admin`)
- Create staff users with username/password + **checkbox** permissions per admin tab (Sales, Customers, Inventory, logs, etc.)
- Edit access / enable-disable / delete staff; cannot delete last superadmin or own account casually
- API: `GET/POST/PATCH/DELETE /api/admin/users` (superadmin); session `require_admin` enforces module permissions on other APIs
- Sidebar hides tabs the user cannot open; Application + User logs record create/update/delete
- DB: `admin_users.role`, `is_active`, `permissions` (JSON) via migrate; bootstrap `admin` promoted to `superadmin`
- Files: `database/db.py`, `migrate.py`, `api/admin.py`, `templates/admin.html`, `static/js/admin.js`, `admin.css`
- Smoke: staff with sales+customers → sales 200, tiles 403, users 403

### Session — GitHub + domain/host guidance (2026-08-17)
- **GitHub private repo:** https://github.com/sund84r/chalukya-tiles-website  
  - Owner account: **sund84r** (personal GitHub; not chalukyatiles@gmail.com for git auth)  
  - Local path remains `website_tiles1`; remote `origin` → that repo; branch `main`  
  - Clean baseline commits: ignore venv/DB/uploads media; `.gitattributes` LF; upload `.gitkeep`s  
  - GitHub CLI installed; authenticated as sund84r (device flow); `git push -u origin main` succeeded  
- **Git identity (local repo):** user.name `sund84r`, email `sund84r@users.noreply.github.com`  
- **What stays local only:** `database/showroom.db`, `static/uploads/*` binaries, `.venv/`  
- **Domain:** Owner has a domain but **no host** yet  
  - Domain alone cannot run FastAPI  
  - Cannot “go live without DB” — products, admin, forms, reviews require SQLite (or later MySQL)  
  - Recommendation: small VPS + SQLite on same server first; optional MySQL later; point domain A record to VPS  
  - Not suitable for GitHub Pages / pure static hosting as currently built  
- README updated with clone + solo `main` workflow (pull → edit → commit → push; no force-push)

### Session — admin brand corner polish (post v1.6.12)
- Admin sidebar **top-left brand area** full white panel (logo + ADMIN text)  
- Logo: no plate on PNG itself; sits on white corner  
- **ADMIN** label colour `#150f3e` (matches logo deep navy)  
- Cache bumps: `admin.css?v178-brand-corner` (and prior oxford/logo versions)

### Session — white + light Oxford blue (v1.6.12)
- Scaffolded full FastAPI + vanilla frontend showroom site
- SQLite contact + enquiry APIs
- All public pages + polish (404, robots, sitemap, security headers)
- Final QA suite: all pages 200, APIs 201, no inline CSS/JS

### Session — memory + documentation
- Created `PROJECT_MEMORY.md`
- Added `templates/docs.html` and route `GET /docs`
- Added `static/css/docs.css` (external styles, no inline CSS)
- Linked documentation from project memory CONTINUE PROMPT
- Bumped project version to 1.1.0; sitemap includes `/docs`

### Session end — 2026-07-15
- User requested session end
- Status: site complete (modules 1–11 + memory/docs); no open blockers
- Next session: launch prep (brand/SITE_URL/media) or optional admin inbox — see CONTINUE PROMPT

### Session — 2026-07-23 rebrand to Chalukya Tiles
- Applied official logo (`static/icons/logo-chalukya.png`) in navbar/footer
- Renamed brand from Prestige Tiles → Chalukya Tiles site-wide
- Contact from business card: phone 99407 18307, email chalukyatiles@gmail.com
- Address Coimbatore Kurumbapalayam; GSTIN 33AAWFC0185C1ZL; MD C. Venkatesan
- Theme charcoal shifted to brand navy; favicon updated
- Version 1.2.0

### Session — 2026-07-23 hero polish + blue/white theme
- Hero: large centered logo, cleaner headline/typing layout (no collision)
- Removed CHALUKYA TILES / SHOWROOM text from hero-poster.svg
- Site theme: elegant red + white (tokens, CTAs, accents, poster gradients)
- Version 1.3.0

### Session — 2026-07-23 brand lockup refinement
- Navbar/footer: text brand “Chalukya / Tiles” + CT mark (no PNG)
- Hero center: inline SVG shield + text wordmark, transparent (no white plate/image)
- Version 1.3.1

### Session end — 2026-07-23
- User confirmed everything fine and exited
- Status at exit: Chalukya Tiles branded site v1.3.4 — new Picsart logo, blue/white theme, reviews carousel fixed
- Resume via CONTINUE PROMPT in this file when needed

### Session — elegant red theme + fonts
- Sitewide palette: deep burgundy `#3b0a12`, crimson `#b01030`, soft ivory backgrounds
- Fonts: Playfair Display (headings) + Manrope (body) on all pages
- Hero poster, favicon, SVG accents, CTAs updated to red
- Version 1.4.0

### Session — 2026-07-23 theme/font reverts (1.4.2–1.4.3)
- 1.4.2: Reverted color palette to elegant blue + white
- 1.4.3: Fonts restored to original Inter + Poppins
- App metadata/version string: 1.4.3

### Session — 2026-08-11 resume (Grok Build)
- User opened project at new path: `C:\Users\Admin\Downloads\ChalukyaTiles_website\website_tiles1`
- Confirmed permanent rules: always follow PROJECT_MEMORY workflow
  - Read PROJECT_MEMORY.md at session start
  - Update PROJECT_MEMORY.md at end of every module/session (never discard useful history)
  - Keep `templates/docs.html` + `GET /docs` in sync with architecture changes
  - Refresh CONTINUE PROMPT at session end
  - Stack constraints: no React/Vue/Angular/Bootstrap/jQuery; modular CSS/JS; no inline CSS/JS
- Memory updates this session: workspace path corrected; version header aligned to 1.4.3; CONTINUE PROMPT refreshed

### Session — 2026-08-11 USER_GUIDE.html handbook
- Added complete categorized user guide: `USER_GUIDE.html` + `static/css/user-guide.css`
- Route: `GET /user-guide` serves the file; also openable from disk in browser
- Covers: VS Code run commands, URLs, tech stack, architecture, folders, public pages, admin, media, analytics, API, DB, SEO, brand, launch checklist, troubleshooting, versions
- Sitemap includes `/user-guide`

### Session end — 2026-08-11 (Grok Build)
- User confirmed site/admin/user-guide working; requested memory update and session close
- **Run notes (this machine):**
  - Prefer: `uvicorn app:app --reload --host 127.0.0.1 --port 8001` if port 8000 hits WinError 10013
  - With venv active: `uvicorn app:app --reload --host 127.0.0.1 --port 8001`
  - Or: `python -m uvicorn app:app --reload --host 127.0.0.1 --port 8001` (must include `python` before `-m`)
- **User guide fix:** `/user-guide` and `/user-guide/` return HTML from `USER_GUIDE.html` (absolute `/static/` asset paths); openable on disk without server
- **Admin:** `/admin` — default `admin` / `chalukya@2026`
- **Version remains:** 1.5.0 (admin panel + media + user guide)
- Next session: launch prep (real photos/videos, SITE_URL, change admin password) or email notifications
- CONTINUE PROMPT refreshed below

### Session — white + light Oxford blue (v1.6.12)
- Palette choice: pure **white** surfaces + **light Oxford blue** (`#002147` family) for chrome/UI
- Goal: posted tile photos render true colour (white card media, `object-fit: contain`)
- Public + admin themed; soft blue-mist alt sections; Oxford sidebar admin with white logo strip
- Cache `?v176-oxford`

### Session — premium palette + clean logo (v1.6.11)
- Removed white background / plate from all logos (nav, hero, footer, admin, user-guide)
- Removed duplicate **Chalukya Tiles** text beside logo (nav top bar, hero label, footer wordmark text, admin brand-name)
- Full site + admin theme: lite ivory, walnut brown, sage green, soft gold accents
- Hero uses light ivory overlay so dark official logo stays readable without a plate
- Admin: ivory sidebar, sage primary buttons, warm login backdrop
- Cache `?v175-premium`

### Session — new official logo (v1.6.10)
- Source: `C:\Users\Admin\Pictures\logo final.png` → `static/icons/logo-chalukya.png` (+ hero/src copies)
- Colours preserved as-given (navy shield + cyan accent); removed CSS `brightness` / heavy filters that tinted logos
- Light white plate behind logo on dark surfaces (hero, footer, transparent nav, admin sidebar) so dark mark stays readable
- Brand text areas use full **Chalukya Tiles** (nav, footer, hero label, admin login/sidebar)
- Favicon accents updated to logo cyan `#00a0e4` / navy `#150f3e`
- Cache `?v=174` / CSS `?v174-logo`

### Session — Home New Arrivals from admin tiles (v1.6.9)
- Home section **New Arrivals / Latest Collections** no longer uses static SVG placeholders
- Loads active rows from `tiles` table (Admin → **New Arrivals**), newest first (limit 12)
- Cards: image, name, meta (category · colour · size · finish); link enquires via `/contact?product=…`
- Empty state when none active; Admin help + toast mention Home Latest Collections
- Files: `app.py`, `templates/index.html`, `static/css/hero.css`, `admin.html`, `admin.js`

### Session — products inventory-only + home shuffle + reviews (v1.6.8)
- **Products page:** only inventory items with `show_on_website=1` (no static catalogue templates / New Arrivals dump)
- **Home:** Featured Products + Gallery Preview shuffle from **posted inventory** + **concept gallery** (random mix each load)
- **Pen FAB** under WhatsApp on all public pages → review modal (name, rating 1–5, title, feedback, optional email/phone)
- **Public API:** `POST /api/review` → status `pending` until admin approves
- **Admin tab Business → Reviews & Ratings:** list/filter pending|approved|rejected; Approve / Reject / Feature / Delete
- **Home reviews slider** shows approved reviews (featured first); empty state prompts pen button
- **Testimonials page** also lists all approved reviews (same source); summary avg / count / 4★+%; featured band from featured review
- Table `reviews` via migrate; helpers in `database/db.py`
- Files: `app.py`, `api/enquiry.py`, `api/admin.py`, `database/db.py`/`migrate.py`, `static/js/reviews.js`, `main.css`, `admin.js`/`admin.html`, all public templates
- Cache: `?v172-review`
- Smoke-tested: review submit → admin approve → appears on home + testimonials; admin panel markup present

### Session — Concept Gallery admin uploads (v1.6.7)
- New admin tab **Concept Gallery** (beside Collection Videos)
- Upload images with category dropdown: Living Room, Bathroom, Parking, Elevation, Outdoor
- Table `concept_gallery`; files in `static/uploads/gallery/`
- API: GET/POST/PATCH/DELETE `/api/admin/concept-gallery`
- Public `/gallery` shows **only** admin-uploaded concept pictures (static template placeholders removed)

### Session — gallery uploads only (v1.6.7b)
- Removed hardcoded SVG/template gallery items + showroom tile dump + featured videos block from `gallery.html`
- Concept Gallery page = active `concept_gallery` rows only

### Session — admin polish v1.6.6 (theme, charts, logs, dims, post website)
- Sidebar: logo + bold large **ADMIN** underneath
- Inventory list: separate Category + Subcategory columns; subcategory filter
- Rename Public/Private → **Post in website** (Posted / Not posted)
- Admin color theme refreshed (deeper navy + blue accents)
- Charts button top-right → sales/inventory/low-stock/posted charts (vanilla canvas)
- Add/Edit inventory: unit presets (pieces/kg/litre/grams…); Tiles → L×W + mm/cm/inches/ft
- System tabs: Backup/Export/Import JSON; Application Logs; User Logs (timestamps)
- CLI: `python -m tools.logs_cli --kind both --limit 100`
- API: `/api/admin/analytics`, `/logs/app|user|cli`, `/import/json`; inventory dim_* columns
- Cache `?v165-theme`

### Session — inventory subcategory → Products under-categories (v1.6.5)
- Admin Add/Edit Inventory: **Category** + **Subcategory** (presets per category, e.g. Sanitary Wares → Pipes/Showers/Sinks; custom allowed)
- Stored in `material_category`; drives Products page “type under category” filters
- `INVENTORY_SUBCATEGORIES` in `database/db.py`; API list returns `subcategories` map
- Cache: admin `?v164-subcat`

### Session — inventory edit pencil + modal (v1.6.4)
- Inventory list: edit icon on name cell corner opens modal to edit stock qty + full item fields
- Uses existing `PATCH /api/admin/inventory/{id}`
- Cache: admin.css/js `?v163-edit`

### Session — products hierarchical categories (v1.6.3)
- Public Products page: main filters match inventory categories (Tiles, Paste, Adhesive, Sanitary Wares, Beading, Others)
- Clicking a main category reveals **sub-types** (material_category / type under that category)
- Cards use `data-main-category` + `data-sub-category`; static catalogue under Tiles
- Files: `app.py`, `database/db.py` helpers, `templates/products.html`, `static/js/main.js`, `static/css/products.css`

### Session — inventory Public/Private toggle (v1.6.2)
- Inventory list: **Public / Private** switch per row (`show_on_website`)
- `PATCH /api/admin/inventory/{id}/visibility` — toggles website Products visibility
- Public = on Products page; Private = admin only (active status still required for public list)
- Cache: admin.css/js `?v162-vis`

### Session — admin leads actions dropdown + smaller menu text (v1.6.1)
- Leads **Actions** column: multi-button row → compact **select dropdown** (Reminder, WhatsApp, Call, SMS, Email, Follow-up) to stop overflow
- Admin sidebar menu text slightly smaller (~−1.5px): nav items `0.8rem`, groups/labels tightened
- Cache: `admin.css?v161-actions`, `admin-biz.js?v161`

### Session — v1.6.0 business / inventory / exports (2026-08-13)
- **Duplicates:** customers unique on `name_normalized + phone_normalized`; tiles unique on `name + colour + pattern` (dedupe then unique index via `database/migrate.py`)
- **Concept Gallery:** public “Gallery” labels renamed site-wide
- **Admin sidebar groups:** Dashboard · Finance · Business · Inventory (existing features kept)
- **Inventory:** categories Tiles/Paste/Adhesive/Sanitary Wares/Beading/Others; CRUD; stock in/out; low stock; `show_on_website` → public Products
- **Finance:** sales (existing) + sales returns + purchases
- **Exports:** Excel/PDF for leads, queries, customers, sales, returns, purchases, inventory, tiles, dashboard; DB backup via `/api/admin/backup/database`
- **Comms:** reminder, WhatsApp, Call, SMS (log only), Email (mailto), follow-up on leads
- **Deps:** openpyxl, fpdf2
- Files: `database/migrate.py`, `database/db.py`, `api/admin.py`, `api/exports.py`, `static/js/admin-biz.js`, `templates/admin.html`, products/gallery templates, `app.py`

### Session — admin sidebar toggle menu (v1.5.2)
- Admin left sidebar is a collapsible **Menu** with open/close switch
- Top bar: hamburger + **Menu** toggle switch (Open/Closed label)
- Backdrop on mobile, Escape to close
- Preference saved in `localStorage` (`chalukya_admin_sidebar_open`)
- Files: `templates/admin.html`, `static/css/admin.css`, `static/js/admin.js`
- v1.5.2 follow-up: removed red-circle sidebar × next to ADMIN; keep only top-bar close control (hamburger/X + Menu switch)

### Session — 2026-08-11 mobile nav overlap fix (v1.5.1)
- **Bug:** Mobile hamburger worked at top of page but after scroll, drawer overlapped / page content (product cards) showed through menu; WhatsApp float sat on top of menu.
- **Cause:** Scrolled header used `backdrop-filter` + fixed height; drawer lived inside header so `position:fixed` was trapped in a filter containing block / clipped to header bar. Drawer z-index (`--z-dropdown` 100) also below WhatsApp (850).
- **Fix:**
  - `static/js/navbar.js`: portal drawer to `document.body`; body scroll lock (`position: fixed` + restore scrollY); solid header while open
  - `static/css/navbar.css`: opaque scrolled header (no backdrop-filter); drawer at modal z-index full viewport; hide `.float-actions` while `body.nav-open`; header/toggle above drawer when open
  - Cache-bust `?v152-mobile-nav` on all templates for navbar.css/js
- Version **1.5.1**

### Session — 2026-08-11 admin panel + media (v1.5.0)
- Built full **Admin panel** (session cookie auth):
  - Pages: `/admin/login`, `/admin`
  - API: `/api/admin/*` in `api/admin.py`
  - UI: `templates/admin.html`, `admin_login.html`, `static/css/admin.css`, `static/js/admin.js`
- **Dashboard analytics:** sales total/month, leads, queries (contact+enquiry), customers, tiles, videos
- **Tile Media upload:** name, model number, colour, material category, image (+ optional size/finish/description)
  - Stored in SQLite `tiles` + files under `static/uploads/tiles/`
  - Rendered on `/products`, `/gallery`, Home featured
- **Collection Videos:** title, description, video, optional poster, active/sort
  - Files under `static/uploads/videos/` (+ posters)
  - Active videos mid-down homepage (after trust strip, before featured)
- **CRM tables:** sales, leads, customers CRUD; queries status/delete for contact + enquiries
- **DB:** expanded `database/db.py` schema + seed demo sales/leads/customers + default admin
- Default login: `admin` / `chalukya@2026` (env: `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_SECRET`)
- Session middleware + `itsdangerous` dependency
- `/docs` + README/memory updated; robots disallow `/admin`
- Version **1.5.0**
- Fixed `TemplateResponse` for Starlette 1.x (`request, name, context`)
- Fixed dashboard stats using closed SQLite connection
- Recreated `.venv` on Python 3.14 with flexible `requirements.txt`
- Smoke-tested: pages 200, admin login, dashboard, tile upload → appears on `/products`

---

## Admin module reference

| Area | Path / file |
|------|-------------|
| Login | GET `/admin/login` |
| Dashboard UI | GET `/admin` |
| Admin API | `/api/admin/*` — tiles, videos, concept-gallery, inventory, sales, returns, purchases, leads, customers, queries, reviews, analytics, logs, backup/export |
| Uploads | `static/uploads/{tiles,videos,posters,gallery,inventory}/` |
| Auth | Starlette sessions (`chalukya_admin_session`) |
| Default login | `admin` / `chalukya@2026` (change before production) |

### Public content sources (admin-driven)

| Surface | Source |
|---------|--------|
| Products page | Inventory with `show_on_website=1` only |
| Home Featured | Shuffle posted inventory + concept gallery |
| Home Latest Collections / New Arrivals | Active `tiles` (Admin → New Arrivals) |
| Concept Gallery page | Active `concept_gallery` only |
| Home + Testimonials reviews | Approved rows in `reviews` (pending until moderated) |
| Home videos | Active collection videos |

---

## Standing session rules (always)

1. **Read first:** `PROJECT_MEMORY.md` at the start of work on this project.
2. **Update always:** Append/revise PROJECT_MEMORY after every module or session; do not delete useful history.
3. **Docs sync:** Keep `templates/docs.html` and `GET /docs` accurate when architecture/features change.
4. **CONTINUE PROMPT:** Regenerate at session end for clean handoff.
5. **Stack:** HTML5 / CSS3 / Vanilla JS ES6+ only on frontend; FastAPI + Jinja2 + SQLite backend; modular `static/css/` and `static/js/`; no inline CSS or inline JS.
6. **Scope:** Module-by-module for large work; keep architecture modular.
7. **Git:** Prefer single `main` branch; `pull` before work; never force-push `main` casually; never commit secrets/DB/uploads binaries.

---

## CONTINUE PROMPT

Copy everything below into a **new conversation** to resume work:

```
You are continuing work on the Chalukya Tiles floor & interior tiles showroom website.

Workspace: C:\Users\Admin\Downloads\ChalukyaTiles_website\website_tiles1
GitHub (private): https://github.com/sund84r/chalukya-tiles-website — account sund84r, branch main.
Read PROJECT_MEMORY.md first and treat it as permanent project memory. Update it at the end of every module/session (never discard useful history). Keep templates/docs.html, USER_GUIDE.html, GET /docs + /user-guide in sync when architecture changes.

Stack (strict): HTML5, CSS3, Vanilla JS ES6+ only — no React/Vue/Angular/Bootstrap/jQuery. Backend: Python FastAPI + Jinja2. Database: SQLite database/showroom.db (gitignored; MySQL-ready). Modular static/css + static/js. No inline CSS/JS.

Brand: Chalukya Tiles. Logo: static/icons/logo-chalukya.png (official final logo; keep natural colours). Theme: white + light Oxford blue (#002147 family); product/media cards pure white + object-fit contain for true tile colour. Nav/footer: logo only (no extra “Chalukya Tiles” text beside mark). Admin sidebar: white top-left brand corner + ADMIN text #150f3e. Phone/WhatsApp 99407 18307. Email chalukyatiles@gmail.com. Address Coimbatore Kurumbapalayam. Version: 1.6.12.

What exists: Full public site + full Admin + USER_GUIDE.
Public: /, /about, /products (posted inventory only), /gallery (concept uploads only), /testimonials (approved reviews), /contact, /docs, /user-guide, 404.
Home: collection videos, featured shuffle (inventory+concepts), New Arrivals from tiles table, gallery preview, reviews slider, pen FAB → POST /api/review.
Admin: dashboard, inventory, New Arrivals, Collection Videos, Concept Gallery, sales/returns/purchases, leads, queries, customers, Reviews & Ratings, logs/backup/export.
DB: SQLite required for products/admin/forms/reviews — not a static site. Domain exists; no host yet — needs VPS/PaaS to go live; SQLite can stay on same server first.

Default admin: admin / chalukya@2026 (CHANGE before public). Env: ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_SECRET, SITE_URL.

Run (Windows; prefer 8002 if 8000 blocked):
  cd C:\Users\Admin\Downloads\ChalukyaTiles_website\website_tiles1
  .\.venv\Scripts\Activate.ps1
  python -m uvicorn app:app --reload --host 0.0.0.0 --port 8002
Open: http://127.0.0.1:8002  Admin: /admin  Repo: github.com/sund84r/chalukya-tiles-website

Git hygiene: pull before work; commit + push main; never commit .venv, .env, showroom.db, upload binaries.

Suggested next tasks:
1) Choose host (VPS recommended) + deploy + point domain DNS + HTTPS
2) Change admin password + ADMIN_SECRET + production SITE_URL
3) Upload real inventory/concepts/new arrivals/videos; backup DB + uploads
4) Sync USER_GUIDE / docs with v1.6.12 features
5) Optional: email on form/review; MySQL later

Rules: Module-by-module if large; modular architecture; update PROJECT_MEMORY.md before ending; refresh CONTINUE PROMPT; keep /docs and USER_GUIDE in sync with major changes.

User request: [PASTE USER REQUEST HERE]
```

---

*Last updated: 2026-08-11 · v1.5.1 mobile nav fix · Maintainer: development sessions via Grok Build*
