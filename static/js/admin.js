/**
 * Chalukya Tiles — Admin panel client
 * Login + dashboard sections for tiles, videos, sales, leads, queries, customers.
 */
(function () {
  "use strict";

  const TITLES = {
    dashboard: "Dashboard",
    "inv-overview": "Inventory overview",
    tiles: "New Arrivals",
    videos: "Collection Videos",
    "concept-gallery": "Concept Gallery",
    sales: "Sales",
    "sales-returns": "Sales Return",
    purchases: "Purchase",
    leads: "Leads",
    queries: "Queries",
    customers: "Customer Details",
    reviews: "Reviews & Ratings",
    inventory: "Inventory / Stock",
    "inventory-add": "Add Inventory",
    "data-tools": "Backup / Export / Import",
    "app-logs": "Application Logs",
    "user-logs": "User Logs",
    users: "User Management",
  };

  let currentAdmin = {
    id: null,
    username: "",
    is_superadmin: false,
    permissions: {},
  };
  let permissionModules = [];

  // Expose toast/api for admin-biz.js
  window.ChalukyaAdmin = window.ChalukyaAdmin || {};

  function money(n) {
    const v = Number(n || 0);
    return "₹" + v.toLocaleString("en-IN", { maximumFractionDigits: 0 });
  }

  function esc(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function statusBadge(status) {
    const s = String(status || "new").toLowerCase();
    return `<span class="admin-status admin-status--${esc(s)}">${esc(s)}</span>`;
  }

  async function api(path, options) {
    const opts = options || {};
    const res = await fetch(path, {
      credentials: "same-origin",
      ...opts,
      headers: {
        ...(opts.body && !(opts.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...(opts.headers || {}),
      },
    });
    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      data = null;
    }
    if (!res.ok) {
      const detail =
        (data && (data.detail || data.message)) ||
        `Request failed (${res.status})`;
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg || JSON.stringify(d)).join(", ")
        : String(detail);
      throw new Error(msg);
    }
    return data;
  }

  function toast(message, type) {
    const el = document.querySelector("[data-admin-toast]");
    if (!el) return;
    el.hidden = false;
    el.textContent = message;
    el.classList.remove("is-error", "is-success");
    if (type) el.classList.add(type === "error" ? "is-error" : "is-success");
    window.clearTimeout(toast._t);
    toast._t = window.setTimeout(() => {
      el.hidden = true;
    }, 3200);
  }

  window.ChalukyaAdmin.api = api;
  window.ChalukyaAdmin.toast = toast;
  window.ChalukyaAdmin.esc = esc;
  window.ChalukyaAdmin.money = money;
  window.ChalukyaAdmin.statusBadge = statusBadge;

  /* ------------------------------------------------------------------ */
  /* Login page                                                         */
  /* ------------------------------------------------------------------ */
  function initLogin() {
    const form = document.getElementById("admin-login-form");
    if (!form) return;

    const err = document.getElementById("login-error");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (err) {
        err.hidden = true;
        err.textContent = "";
      }
      const fd = new FormData(form);
      try {
        await api("/api/admin/login", {
          method: "POST",
          body: JSON.stringify({
            username: String(fd.get("username") || "").trim(),
            password: String(fd.get("password") || ""),
          }),
        });
        window.location.href = "/admin";
      } catch (ex) {
        if (err) {
          err.hidden = false;
          err.textContent = ex.message || "Login failed";
        }
      }
    });
  }

  /* ------------------------------------------------------------------ */
  /* Dashboard app                                                      */
  /* ------------------------------------------------------------------ */
  function initApp() {
    const root = document.querySelector("[data-admin-app]");
    if (!root) return;

    const titleEl = document.querySelector("[data-admin-title]");
    const panels = Array.from(document.querySelectorAll("[data-admin-panel]"));
    const navItems = Array.from(document.querySelectorAll("[data-admin-nav]"));
    const shell = document.querySelector("[data-admin-shell]");
    const sidebar = document.querySelector("[data-admin-sidebar]");
    const backdrop = document.querySelector("[data-admin-backdrop]");
    const menuBtn = document.querySelector("[data-admin-menu]");

    const STORAGE_KEY = "chalukya_admin_sidebar_open";

    function isMobile() {
      return window.matchMedia("(max-width: 900px)").matches;
    }

    function readStoredOpen() {
      try {
        const v = localStorage.getItem(STORAGE_KEY);
        if (v === null) return !isMobile(); // desktop open by default, mobile closed
        return v === "1";
      } catch (_) {
        return !isMobile();
      }
    }

    function writeStoredOpen(open) {
      try {
        localStorage.setItem(STORAGE_KEY, open ? "1" : "0");
      } catch (_) {
        /* ignore */
      }
    }

    function setSidebarOpen(open, options) {
      const opts = options || {};
      if (!shell || !sidebar) return;

      // On mobile, "open" means drawer visible; desktop uses closed class inverted
      shell.classList.toggle("is-sidebar-closed", !open);
      sidebar.classList.toggle("is-open", open);
      sidebar.setAttribute("aria-hidden", open ? "false" : "true");

      if (menuBtn) {
        menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
        menuBtn.setAttribute(
          "aria-label",
          open ? "Close menu" : "Open menu"
        );
      }

      // Backdrop only useful on small screens when open
      if (backdrop) {
        const showBack = open && isMobile();
        backdrop.hidden = !showBack;
        backdrop.classList.toggle("is-visible", showBack);
        backdrop.setAttribute("aria-hidden", showBack ? "false" : "true");
      }

      const mobileOpen = open && isMobile();
      document.body.classList.toggle("admin-menu-open", mobileOpen);
      document.documentElement.classList.toggle("admin-menu-open", mobileOpen);

      if (!opts.skipStore) {
        // Persist desktop preference only; mobile always starts closed
        if (!isMobile()) {
          writeStoredOpen(open);
        }
      }
    }

    function toggleSidebar() {
      const open = shell && !shell.classList.contains("is-sidebar-closed");
      setSidebarOpen(!open);
    }

    // Initial state: mobile always starts with drawer closed
    setSidebarOpen(isMobile() ? false : readStoredOpen(), { skipStore: true });

    if (menuBtn) {
      menuBtn.addEventListener("click", (e) => {
        e.preventDefault();
        toggleSidebar();
      });
    }
    if (backdrop) {
      backdrop.addEventListener("click", () => setSidebarOpen(false));
    }

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && shell && !shell.classList.contains("is-sidebar-closed")) {
        setSidebarOpen(false);
      }
    });

    // On resize: keep UX sane (close drawer on mobile by default when shrinking)
    let lastMobile = isMobile();
    window.addEventListener("resize", () => {
      const nowMobile = isMobile();
      if (nowMobile !== lastMobile) {
        lastMobile = nowMobile;
        if (nowMobile) {
          setSidebarOpen(false, { skipStore: true });
        } else {
          setSidebarOpen(readStoredOpen(), { skipStore: true });
        }
      } else if (backdrop) {
        const open = shell && !shell.classList.contains("is-sidebar-closed");
        const showBack = open && nowMobile;
        backdrop.hidden = !showBack;
        backdrop.classList.toggle("is-visible", showBack);
      }
    });

    function canAccess(moduleKey) {
      if (currentAdmin.is_superadmin) return true;
      if (moduleKey === "users") return false;
      return Number((currentAdmin.permissions || {})[moduleKey] || 0) === 1;
    }

    function applyNavPermissions() {
      navItems.forEach((btn) => {
        const key = btn.getAttribute("data-admin-nav");
        const allowed = canAccess(key);
        btn.hidden = !allowed;
        if (btn.hasAttribute("data-admin-super-only")) {
          btn.hidden = !currentAdmin.is_superadmin;
        }
      });
      // Hide empty group labels when all siblings hidden
      document.querySelectorAll(".admin-nav__group").forEach((group) => {
        let el = group.nextElementSibling;
        let any = false;
        while (el && !el.classList.contains("admin-nav__group")) {
          if (
            el.classList.contains("admin-nav__item") &&
            !el.hidden
          ) {
            any = true;
          }
          el = el.nextElementSibling;
        }
        group.hidden = !any;
      });
    }

    function firstAllowedPanel() {
      const order = Object.keys(TITLES);
      for (const key of order) {
        if (canAccess(key)) return key;
      }
      return "dashboard";
    }

    function showPanel(name) {
      if (!canAccess(name)) {
        name = firstAllowedPanel();
      }
      panels.forEach((p) => {
        const active = p.getAttribute("data-admin-panel") === name;
        p.classList.toggle("is-active", active);
        p.hidden = !active;
      });
      navItems.forEach((btn) => {
        btn.classList.toggle(
          "is-active",
          btn.getAttribute("data-admin-nav") === name
        );
      });
      if (titleEl) titleEl.textContent = TITLES[name] || name;

      // Charts + Refresh only on Dashboard section tabs
      const dashTools = document.querySelector("[data-admin-dashboard-tools]");
      if (dashTools) {
        const onDashboard =
          name === "dashboard" || name === "inv-overview";
        dashTools.hidden = !onDashboard || !canAccess(name);
      }

      // On mobile, close menu after choosing a section
      if (isMobile()) {
        setSidebarOpen(false);
      }
      loadSection(name);
    }

    navItems.forEach((btn) => {
      btn.addEventListener("click", () => {
        showPanel(btn.getAttribute("data-admin-nav"));
      });
    });

    const logoutBtn = document.querySelector("[data-admin-logout]");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", async () => {
        try {
          await api("/api/admin/logout", { method: "POST", body: "{}" });
        } catch (_) {
          /* still redirect */
        }
        window.location.href = "/admin/login";
      });
    }

    const refreshBtn = document.querySelector("[data-admin-refresh]");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => {
        const active = document.querySelector(".admin-panel.is-active");
        const name = active
          ? active.getAttribute("data-admin-panel")
          : "dashboard";
        loadSection(name);
        toast("Refreshed", "success");
      });
    }

    bindForms();

    api("/api/admin/me")
      .then((data) => {
        currentAdmin = data.user || currentAdmin;
        permissionModules = data.modules || [];
        const nameEl = document.querySelector("[data-admin-username]");
        if (nameEl && currentAdmin.username) {
          nameEl.textContent = currentAdmin.username;
        }
        applyNavPermissions();
        renderCreatePermGrid();
        showPanel(firstAllowedPanel());
      })
      .catch((ex) => {
        toast(ex.message || "Session error", "error");
        showPanel("dashboard");
      });
  }

  function loadSection(name) {
    if (name === "dashboard") return loadDashboard();
    if (name === "tiles") return loadTiles();
    if (name === "videos") return loadVideos();
    if (name === "concept-gallery") return loadConceptGallery();
    if (name === "sales") return loadSales();
    if (name === "leads") return loadLeads();
    if (name === "queries") return loadQueries();
    if (name === "customers") return loadCustomers();
    if (name === "reviews") return loadReviews();
    if (name === "users") return loadUsers();
    if (window.ChalukyaAdminBiz && typeof window.ChalukyaAdminBiz.load === "function") {
      return window.ChalukyaAdminBiz.load(name);
    }
  }

  function renderPermCheckboxes(container, selected) {
    if (!container) return;
    const sel = selected || {};
    const mods = permissionModules.length
      ? permissionModules
      : Object.keys(TITLES)
          .filter((k) => k !== "users")
          .map((k) => ({ key: k, label: TITLES[k] }));
    container.innerHTML = mods
      .map(
        (m) => `<label class="admin-perm-item">
          <input type="checkbox" name="perm_${esc(m.key)}" value="${esc(m.key)}" ${
          Number(sel[m.key]) === 1 ? "checked" : ""
        }>
          <span>${esc(m.label)}</span>
        </label>`
      )
      .join("");
  }

  function readPermCheckboxes(container) {
    const out = {};
    if (!container) return out;
    container.querySelectorAll('input[type="checkbox"]').forEach((box) => {
      out[box.value] = box.checked ? 1 : 0;
    });
    return out;
  }

  function renderCreatePermGrid() {
    renderPermCheckboxes(document.querySelector("[data-user-perm-grid]"), {});
  }

  function permTagsHtml(user) {
    if (user.is_superadmin) {
      return '<span class="admin-perm-tag">All access</span>';
    }
    const perms = user.permissions || {};
    const labels = (permissionModules.length
      ? permissionModules
      : Object.keys(TITLES).map((k) => ({ key: k, label: TITLES[k] }))
    ).filter((m) => Number(perms[m.key]) === 1);
    if (!labels.length) {
      return '<span class="admin-muted">No tabs</span>';
    }
    return `<div class="admin-perm-tags">${labels
      .map((m) => `<span class="admin-perm-tag">${esc(m.label)}</span>`)
      .join("")}</div>`;
  }

  async function loadUsers() {
    if (!currentAdmin.is_superadmin) {
      toast("Only the main admin can manage users", "error");
      return;
    }
    try {
      const data = await api("/api/admin/users");
      permissionModules = data.modules || permissionModules;
      renderCreatePermGrid();
      const body = document.querySelector("[data-users-table]");
      if (!body) return;
      const items = data.items || [];
      body.innerHTML = items.length
        ? items
            .map((u) => {
              const isSelf = Number(u.id) === Number(currentAdmin.id);
              const superU = !!u.is_superadmin;
              return `<tr data-user-row="${u.id}">
              <td><strong>${esc(u.username)}</strong></td>
              <td>${superU ? '<span class="admin-status admin-status--won">superadmin</span>' : "staff"}</td>
              <td>${
                Number(u.is_active) === 1
                  ? '<span class="admin-status admin-status--approved">active</span>'
                  : '<span class="admin-status admin-status--rejected">disabled</span>'
              }</td>
              <td>${permTagsHtml(u)}</td>
              <td class="admin-row-actions">
                ${
                  superU
                    ? isSelf
                      ? `<button type="button" class="admin-btn admin-btn--outline admin-btn--sm" data-user-pw="${u.id}">Change password</button>`
                      : `<span class="admin-muted">Protected</span>`
                    : `<button type="button" class="admin-btn admin-btn--outline admin-btn--sm" data-user-edit="${u.id}">Edit access</button>
                       <button type="button" class="admin-btn admin-btn--outline admin-btn--sm" data-user-toggle="${u.id}" data-active="${u.is_active}">${
                         Number(u.is_active) === 1 ? "Disable" : "Enable"
                       }</button>
                       <button type="button" class="admin-btn admin-btn--danger admin-btn--sm" data-user-delete="${u.id}">Delete</button>`
                }
              </td>
            </tr>
            ${
              superU
                ? ""
                : `<tr data-user-editor="${u.id}" hidden><td colspan="5">
              <div class="admin-user-edit">
                <p class="admin-help">Tick tabs for <strong>${esc(u.username)}</strong></p>
                <div class="admin-perm-grid" data-edit-perms="${u.id}"></div>
                <label class="admin-field"><span>New password (optional)</span><input type="password" data-edit-password="${u.id}" minlength="6" placeholder="Leave blank to keep"></label>
                <button type="button" class="admin-btn admin-btn--primary admin-btn--sm" data-user-save="${u.id}">Save</button>
              </div>
            </td></tr>`
            }`;
            })
            .join("")
        : `<tr><td colspan="5" class="admin-empty">No users yet</td></tr>`;

      items.forEach((u) => {
        if (u.is_superadmin) return;
        renderPermCheckboxes(
          document.querySelector(`[data-edit-perms="${u.id}"]`),
          u.permissions || {}
        );
      });

      body.querySelectorAll("[data-user-edit]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const id = btn.getAttribute("data-user-edit");
          const row = document.querySelector(`[data-user-editor="${id}"]`);
          if (row) row.hidden = !row.hidden;
        });
      });

      body.querySelectorAll("[data-user-save]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const id = btn.getAttribute("data-user-save");
          const grid = document.querySelector(`[data-edit-perms="${id}"]`);
          const pw = document.querySelector(`[data-edit-password="${id}"]`);
          const payload = { permissions: readPermCheckboxes(grid) };
          if (pw && pw.value.trim()) payload.password = pw.value.trim();
          try {
            await api(`/api/admin/users/${id}`, {
              method: "PATCH",
              body: JSON.stringify(payload),
            });
            toast("User permissions saved", "success");
            loadUsers();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });

      body.querySelectorAll("[data-user-toggle]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const id = btn.getAttribute("data-user-toggle");
          const active = Number(btn.getAttribute("data-active")) === 1 ? 0 : 1;
          try {
            await api(`/api/admin/users/${id}`, {
              method: "PATCH",
              body: JSON.stringify({ is_active: active }),
            });
            toast(active ? "User enabled" : "User disabled", "success");
            loadUsers();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });

      body.querySelectorAll("[data-user-delete]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!window.confirm("Delete this staff user permanently?")) return;
          try {
            await api(`/api/admin/users/${btn.getAttribute("data-user-delete")}`, {
              method: "DELETE",
            });
            toast("User deleted", "success");
            loadUsers();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });

      body.querySelectorAll("[data-user-pw]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const pw = window.prompt("New password for your admin account (min 6 chars):");
          if (!pw) return;
          try {
            await api(`/api/admin/users/${btn.getAttribute("data-user-pw")}`, {
              method: "PATCH",
              body: JSON.stringify({ password: pw }),
            });
            toast("Password updated", "success");
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  async function loadDashboard() {
    try {
      const data = await api("/api/admin/dashboard");
      const s = data.stats || {};
      const statsEl = document.querySelector("[data-dash-stats]");
      if (statsEl) {
        statsEl.innerHTML = [
          statCard("Sales total", money(s.sales_total), `${s.sales_count || 0} invoices`),
          statCard("This month", money(s.sales_month), "Completed sales sum"),
          statCard("Purchases", money(s.purchases_total), "All-time sum"),
          statCard("Returns", money(s.returns_total), "Sales returns"),
          statCard("Leads", s.leads || 0, `${s.leads_new || 0} new`),
          statCard("Queries", s.queries_total || 0, `${s.queries_new || 0} new`),
          statCard("Customers", s.customers || 0, "Master records"),
          statCard("Inventory", s.inventory_count || 0, `${s.low_stock || 0} low stock`),
          statCard("Reminders", s.reminders_pending || 0, `${s.reminders_overdue || 0} overdue`),
          statCard("New Arrivals", s.tiles || 0, `${s.tiles_active || 0} active`),
          statCard("Videos", s.videos || 0, `${s.videos_active || 0} on homepage`),
          statCard("Enquiries", s.enquiries || 0, `${s.enquiries_new || 0} new`),
        ].join("");
      }

      const salesBody = document.querySelector("[data-dash-sales]");
      if (salesBody) {
        const rows = (data.recent && data.recent.sales) || [];
        salesBody.innerHTML = rows.length
          ? rows
              .map(
                (r) => `<tr>
              <td>${esc(r.invoice_no)}</td>
              <td>${esc(r.customer_name)}</td>
              <td>${esc(r.product_name)}</td>
              <td>${money(r.amount)}</td>
              <td>${esc(r.sale_date)}</td>
            </tr>`
              )
              .join("")
          : `<tr><td colspan="5" class="admin-empty">No sales yet</td></tr>`;
      }

      const leadsBody = document.querySelector("[data-dash-leads]");
      if (leadsBody) {
        const rows = (data.recent && data.recent.leads) || [];
        leadsBody.innerHTML = rows.length
          ? rows
              .map(
                (r) => `<tr>
              <td>${esc(r.name)}</td>
              <td>${esc(r.phone)}</td>
              <td>${esc(r.interest || "—")}</td>
              <td>${statusBadge(r.status)}</td>
            </tr>`
              )
              .join("")
          : `<tr><td colspan="4" class="admin-empty">No leads yet</td></tr>`;
      }

      const qBody = document.querySelector("[data-dash-queries]");
      if (qBody) {
        const contacts = ((data.recent && data.recent.contacts) || []).map((c) => ({
          ...c,
          type: "Contact",
          detail: c.message,
        }));
        const enquiries = ((data.recent && data.recent.enquiries) || []).map((c) => ({
          ...c,
          type: "Enquiry",
          detail: c.product_name || c.message,
        }));
        const rows = contacts.concat(enquiries).slice(0, 10);
        qBody.innerHTML = rows.length
          ? rows
              .map(
                (r) => `<tr>
              <td>${esc(r.type)}</td>
              <td>${esc(r.name)}</td>
              <td>${esc(r.phone)}</td>
              <td>${esc((r.detail || "").slice(0, 80))}</td>
              <td>${statusBadge(r.status)}</td>
            </tr>`
              )
              .join("")
          : `<tr><td colspan="5" class="admin-empty">No queries yet</td></tr>`;
      }
    } catch (ex) {
      if (String(ex.message || "").toLowerCase().includes("login")) {
        window.location.href = "/admin/login";
        return;
      }
      toast(ex.message, "error");
    }
  }

  function statCard(label, value, meta) {
    return `<article class="admin-stat">
      <span class="admin-stat__label">${esc(label)}</span>
      <span class="admin-stat__value">${esc(value)}</span>
      <span class="admin-stat__meta">${esc(meta || "")}</span>
    </article>`;
  }

  async function loadTiles() {
    try {
      const data = await api("/api/admin/tiles");
      const items = data.items || [];
      const count = document.querySelector("[data-tiles-count]");
      if (count) count.textContent = String(items.length);
      const grid = document.querySelector("[data-tiles-grid]");
      if (!grid) return;
      if (!items.length) {
        grid.innerHTML = `<p class="admin-empty">No tiles uploaded yet. Use the form to add your first product image.</p>`;
        return;
      }
      grid.innerHTML = items
        .map(
          (t) => `<article class="admin-media-card">
          <img src="${esc(t.image_path)}" alt="${esc(t.name)}" loading="lazy">
          <div class="admin-media-card__body">
            <h3>${esc(t.name)}</h3>
            <p>Model: ${esc(t.model_number)}</p>
            <p>${esc(t.colour)} · ${esc(t.material_category)}</p>
            <p>${t.is_active ? "Active" : "Hidden"}</p>
            <div class="admin-media-card__actions">
              <button type="button" class="admin-btn admin-btn--outline admin-btn--sm" data-tile-toggle="${t.id}" data-active="${t.is_active}">
                ${t.is_active ? "Hide" : "Show"}
              </button>
              <button type="button" class="admin-btn admin-btn--danger admin-btn--sm" data-tile-delete="${t.id}">Delete</button>
            </div>
          </div>
        </article>`
        )
        .join("");

      grid.querySelectorAll("[data-tile-delete]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!window.confirm("Delete this tile?")) return;
          try {
            await api(`/api/admin/tiles/${btn.getAttribute("data-tile-delete")}`, {
              method: "DELETE",
            });
            toast("Tile deleted", "success");
            loadTiles();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });

      grid.querySelectorAll("[data-tile-toggle]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const id = btn.getAttribute("data-tile-toggle");
          const active = Number(btn.getAttribute("data-active")) === 1 ? 0 : 1;
          const fd = new FormData();
          fd.append("is_active", String(active));
          try {
            await api(`/api/admin/tiles/${id}`, { method: "PATCH", body: fd });
            toast(active ? "Shown on Home Latest Collections" : "Hidden from Home", "success");
            loadTiles();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  async function loadVideos() {
    try {
      const data = await api("/api/admin/videos");
      const items = data.items || [];
      const list = document.querySelector("[data-videos-list]");
      if (!list) return;
      if (!items.length) {
        list.innerHTML = `<p class="admin-empty">No collection videos yet.</p>`;
        return;
      }
      list.innerHTML = items
        .map(
          (v) => `<article class="admin-video-item">
          <video src="${esc(v.video_path)}" controls preload="metadata" poster="${esc(v.poster_path || "")}"></video>
          <h3>${esc(v.title)}</h3>
          <p>${esc(v.description || "No description")} · sort ${esc(v.sort_order)} · ${v.is_active ? "Active on homepage" : "Hidden"}</p>
          <div class="admin-media-card__actions">
            <button type="button" class="admin-btn admin-btn--outline admin-btn--sm" data-video-toggle="${v.id}" data-active="${v.is_active}">
              ${v.is_active ? "Hide from homepage" : "Show on homepage"}
            </button>
            <button type="button" class="admin-btn admin-btn--danger admin-btn--sm" data-video-delete="${v.id}">Delete</button>
          </div>
        </article>`
        )
        .join("");

      list.querySelectorAll("[data-video-delete]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!window.confirm("Delete this video?")) return;
          try {
            await api(`/api/admin/videos/${btn.getAttribute("data-video-delete")}`, {
              method: "DELETE",
            });
            toast("Video deleted", "success");
            loadVideos();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });

      list.querySelectorAll("[data-video-toggle]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const id = btn.getAttribute("data-video-toggle");
          const active = Number(btn.getAttribute("data-active")) === 1 ? 0 : 1;
          const fd = new FormData();
          fd.append("is_active", String(active));
          try {
            await api(`/api/admin/videos/${id}`, { method: "PATCH", body: fd });
            toast("Video updated", "success");
            loadVideos();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  const GALLERY_CAT_LABELS = {
    living: "Living Room",
    bathroom: "Bathroom",
    parking: "Parking",
    elevation: "Elevation",
    outdoor: "Outdoor",
  };

  async function loadConceptGallery() {
    try {
      const data = await api("/api/admin/concept-gallery");
      const items = data.items || [];
      const count = document.querySelector("[data-concept-gallery-count]");
      if (count) count.textContent = String(items.length);
      const grid = document.querySelector("[data-concept-gallery-grid]");
      if (!grid) return;
      if (!items.length) {
        grid.innerHTML = `<p class="admin-empty">No concept gallery pictures yet. Upload images with a category to show them on the website Concept Gallery page.</p>`;
        return;
      }
      grid.innerHTML = items
        .map(
          (t) => `<article class="admin-media-card">
          <img src="${esc(t.image_path)}" alt="${esc(t.title)}" loading="lazy">
          <div class="admin-media-card__body">
            <h3>${esc(t.title)}</h3>
            <p>${esc(GALLERY_CAT_LABELS[t.category] || t.category)}</p>
            <p>${t.is_active ? "Posted on website" : "Hidden"}</p>
            <div class="admin-media-card__actions">
              <button type="button" class="admin-btn admin-btn--outline admin-btn--sm" data-cg-toggle="${t.id}" data-active="${t.is_active}">
                ${t.is_active ? "Hide" : "Post"}
              </button>
              <button type="button" class="admin-btn admin-btn--danger admin-btn--sm" data-cg-delete="${t.id}">Delete</button>
            </div>
          </div>
        </article>`
        )
        .join("");

      grid.querySelectorAll("[data-cg-delete]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!window.confirm("Delete this gallery picture?")) return;
          try {
            await api(
              `/api/admin/concept-gallery/${btn.getAttribute("data-cg-delete")}`,
              { method: "DELETE" }
            );
            toast("Deleted", "success");
            loadConceptGallery();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });

      grid.querySelectorAll("[data-cg-toggle]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const id = btn.getAttribute("data-cg-toggle");
          const active = Number(btn.getAttribute("data-active")) === 1 ? 0 : 1;
          const fd = new FormData();
          fd.append("is_active", String(active));
          try {
            await api(`/api/admin/concept-gallery/${id}`, {
              method: "PATCH",
              body: fd,
            });
            toast(active ? "Posted on Concept Gallery" : "Hidden from website", "success");
            loadConceptGallery();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  async function loadSales() {
    try {
      const data = await api("/api/admin/sales");
      const body = document.querySelector("[data-sales-table]");
      if (!body) return;
      const items = data.items || [];
      body.innerHTML = items.length
        ? items
            .map(
              (r) => `<tr>
            <td>${esc(r.invoice_no)}</td>
            <td>${esc(r.customer_name)}</td>
            <td>${esc(r.customer_phone || "—")}</td>
            <td>${esc(r.product_name)}</td>
            <td>${esc(r.quantity)}</td>
            <td>${money(r.amount)}</td>
            <td>${esc(r.sale_date)}</td>
            <td>${statusBadge(r.status)}</td>
            <td><button type="button" class="admin-btn admin-btn--danger admin-btn--sm" data-sale-delete="${r.id}">Delete</button></td>
          </tr>`
            )
            .join("")
        : `<tr><td colspan="9" class="admin-empty">No sales records</td></tr>`;

      body.querySelectorAll("[data-sale-delete]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!window.confirm("Delete this sale?")) return;
          try {
            await api(`/api/admin/sales/${btn.getAttribute("data-sale-delete")}`, {
              method: "DELETE",
            });
            toast("Sale deleted", "success");
            loadSales();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  async function loadReviews() {
    try {
      const filterEl = document.querySelector("[data-reviews-filter]");
      const status = filterEl ? String(filterEl.value || "") : "";
      const q = status ? `?status=${encodeURIComponent(status)}` : "";
      const data = await api(`/api/admin/reviews${q}`);
      const items = data.items || [];
      const count = document.querySelector("[data-reviews-count]");
      if (count) {
        count.textContent = `${items.length} review${items.length === 1 ? "" : "s"}`;
      }
      const body = document.querySelector("[data-reviews-table]");
      if (!body) return;

      function stars(n) {
        const r = Math.max(1, Math.min(5, Number(n) || 5));
        return "★".repeat(r) + "☆".repeat(5 - r) + ` (${r})`;
      }

      body.innerHTML = items.length
        ? items
            .map((r) => {
              const featured = Number(r.is_featured) === 1;
              const st = String(r.status || "pending");
              return `<tr>
            <td><strong>${esc(r.name)}</strong></td>
            <td title="${esc(r.rating)}">${stars(r.rating)}</td>
            <td>
              ${r.title ? `<strong>${esc(r.title)}</strong><br>` : ""}
              <span class="admin-muted">${esc((r.message || "").slice(0, 160))}${(r.message || "").length > 160 ? "…" : ""}</span>
            </td>
            <td class="text-sm">
              ${r.phone ? esc(r.phone) : "—"}
              ${r.email ? `<br><span class="admin-muted">${esc(r.email)}</span>` : ""}
            </td>
            <td>${statusBadge(st)}</td>
            <td>${featured ? '<span class="admin-status admin-status--won">featured</span>' : "—"}</td>
            <td class="text-sm">${esc((r.created_at || "").slice(0, 16).replace("T", " "))}</td>
            <td class="admin-row-actions">
              ${
                st !== "approved"
                  ? `<button type="button" class="admin-btn admin-btn--primary admin-btn--sm" data-review-action="approve" data-id="${r.id}">Approve</button>`
                  : ""
              }
              ${
                st !== "rejected"
                  ? `<button type="button" class="admin-btn admin-btn--outline admin-btn--sm" data-review-action="reject" data-id="${r.id}">Reject</button>`
                  : ""
              }
              ${
                st === "approved"
                  ? `<button type="button" class="admin-btn admin-btn--outline admin-btn--sm" data-review-action="feature" data-id="${r.id}" data-featured="${featured ? 1 : 0}">${
                      featured ? "Unfeature" : "Feature"
                    }</button>`
                  : ""
              }
              <button type="button" class="admin-btn admin-btn--danger admin-btn--sm" data-review-action="delete" data-id="${r.id}">Delete</button>
            </td>
          </tr>`;
            })
            .join("")
        : `<tr><td colspan="8" class="admin-empty">No reviews${status ? " with this status" : ""} yet. Customers can submit via the pen icon on the website.</td></tr>`;

      body.querySelectorAll("[data-review-action]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const id = btn.getAttribute("data-id");
          const action = btn.getAttribute("data-review-action");
          try {
            if (action === "delete") {
              if (!window.confirm("Delete this review permanently?")) return;
              await api(`/api/admin/reviews/${id}`, { method: "DELETE" });
              toast("Review deleted", "success");
            } else if (action === "approve") {
              await api(`/api/admin/reviews/${id}`, {
                method: "PATCH",
                body: JSON.stringify({ status: "approved" }),
              });
              toast("Review approved — visible on home", "success");
            } else if (action === "reject") {
              await api(`/api/admin/reviews/${id}`, {
                method: "PATCH",
                body: JSON.stringify({ status: "rejected", is_featured: 0 }),
              });
              toast("Review rejected", "success");
            } else if (action === "feature") {
              const was = Number(btn.getAttribute("data-featured")) === 1;
              await api(`/api/admin/reviews/${id}`, {
                method: "PATCH",
                body: JSON.stringify({
                  status: "approved",
                  is_featured: was ? 0 : 1,
                }),
              });
              toast(was ? "Removed from featured" : "Featured on home", "success");
            }
            loadReviews();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  async function loadLeads() {
    try {
      const data = await api("/api/admin/leads");
      const body = document.querySelector("[data-leads-table]");
      if (!body) return;
      const items = data.items || [];
      body.innerHTML = items.length
        ? items
            .map(
              (r) => `<tr>
            <td>${esc(r.name)}</td>
            <td>${esc(r.phone)}</td>
            <td>${esc(r.email || "—")}</td>
            <td>${esc(r.source || "—")}</td>
            <td>${esc(r.interest || "—")}</td>
            <td>${statusBadge(r.status)}</td>
            <td>${esc(r.reminder_at || "—")}${r.reminder_at && r.reminder_at < new Date().toISOString() ? ' <span class="admin-status admin-status--cancelled">overdue</span>' : ""}</td>
            <td class="admin-comm-actions" data-comm-row data-entity="lead" data-id="${r.id}" data-phone="${esc(r.phone)}" data-email="${esc(r.email || "")}" data-name="${esc(r.name)}"></td>
            <td><button type="button" class="admin-btn admin-btn--danger admin-btn--sm" data-lead-delete="${r.id}">Delete</button></td>
          </tr>`
            )
            .join("")
        : `<tr><td colspan="9" class="admin-empty">No leads</td></tr>`;

      body.querySelectorAll("[data-lead-delete]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!window.confirm("Delete this lead?")) return;
          try {
            await api(`/api/admin/leads/${btn.getAttribute("data-lead-delete")}`, {
              method: "DELETE",
            });
            toast("Lead deleted", "success");
            loadLeads();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });
      if (window.ChalukyaAdminBiz && window.ChalukyaAdminBiz.mountCommActions) {
        window.ChalukyaAdminBiz.mountCommActions(body);
      }
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  async function loadQueries() {
    try {
      const data = await api("/api/admin/queries");
      const cBody = document.querySelector("[data-contacts-table]");
      const eBody = document.querySelector("[data-enquiries-table]");

      if (cBody) {
        const items = data.contacts || [];
        cBody.innerHTML = items.length
          ? items
              .map(
                (r) => `<tr>
              <td>${esc(r.name)}</td>
              <td>${esc(r.phone)}</td>
              <td>${esc(r.email)}</td>
              <td>${esc((r.message || "").slice(0, 100))}</td>
              <td>
                <select data-contact-status="${r.id}">
                  ${["new", "read", "replied", "closed"]
                    .map(
                      (s) =>
                        `<option value="${s}" ${
                          r.status === s ? "selected" : ""
                        }>${s}</option>`
                    )
                    .join("")}
                </select>
              </td>
              <td>${esc((r.created_at || "").slice(0, 10))}</td>
              <td><button type="button" class="admin-btn admin-btn--danger admin-btn--sm" data-contact-delete="${r.id}">Delete</button></td>
            </tr>`
              )
              .join("")
          : `<tr><td colspan="7" class="admin-empty">No contact messages</td></tr>`;

        cBody.querySelectorAll("[data-contact-status]").forEach((sel) => {
          sel.addEventListener("change", async () => {
            try {
              await api(`/api/admin/queries/contact/${sel.getAttribute("data-contact-status")}`, {
                method: "PATCH",
                body: JSON.stringify({ status: sel.value }),
              });
              toast("Contact status updated", "success");
            } catch (ex) {
              toast(ex.message, "error");
            }
          });
        });
        cBody.querySelectorAll("[data-contact-delete]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            if (!window.confirm("Delete this message?")) return;
            try {
              await api(
                `/api/admin/queries/contact/${btn.getAttribute("data-contact-delete")}`,
                { method: "DELETE" }
              );
              toast("Deleted", "success");
              loadQueries();
            } catch (ex) {
              toast(ex.message, "error");
            }
          });
        });
      }

      if (eBody) {
        const items = data.enquiries || [];
        eBody.innerHTML = items.length
          ? items
              .map(
                (r) => `<tr>
              <td>${esc(r.name)}</td>
              <td>${esc(r.phone)}</td>
              <td>${esc(r.product_name || "—")}</td>
              <td>${esc(r.product_category || "—")}</td>
              <td>${esc((r.message || "").slice(0, 80))}</td>
              <td>
                <select data-enquiry-status="${r.id}">
                  ${["new", "read", "replied", "closed"]
                    .map(
                      (s) =>
                        `<option value="${s}" ${
                          r.status === s ? "selected" : ""
                        }>${s}</option>`
                    )
                    .join("")}
                </select>
              </td>
              <td>${esc((r.created_at || "").slice(0, 10))}</td>
              <td><button type="button" class="admin-btn admin-btn--danger admin-btn--sm" data-enquiry-delete="${r.id}">Delete</button></td>
            </tr>`
              )
              .join("")
          : `<tr><td colspan="8" class="admin-empty">No product enquiries</td></tr>`;

        eBody.querySelectorAll("[data-enquiry-status]").forEach((sel) => {
          sel.addEventListener("change", async () => {
            try {
              await api(
                `/api/admin/queries/enquiry/${sel.getAttribute("data-enquiry-status")}`,
                {
                  method: "PATCH",
                  body: JSON.stringify({ status: sel.value }),
                }
              );
              toast("Enquiry status updated", "success");
            } catch (ex) {
              toast(ex.message, "error");
            }
          });
        });
        eBody.querySelectorAll("[data-enquiry-delete]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            if (!window.confirm("Delete this enquiry?")) return;
            try {
              await api(
                `/api/admin/queries/enquiry/${btn.getAttribute("data-enquiry-delete")}`,
                { method: "DELETE" }
              );
              toast("Deleted", "success");
              loadQueries();
            } catch (ex) {
              toast(ex.message, "error");
            }
          });
        });
      }
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  async function loadCustomers() {
    try {
      const data = await api("/api/admin/customers");
      const body = document.querySelector("[data-customers-table]");
      if (!body) return;
      const items = data.items || [];
      body.innerHTML = items.length
        ? items
            .map(
              (r) => `<tr>
            <td>${esc(r.name)}</td>
            <td>${esc(r.phone)}</td>
            <td>${esc(r.email || "—")}</td>
            <td>${esc(r.city || "—")}</td>
            <td>${esc(r.address || "—")}</td>
            <td>${esc((r.created_at || "").slice(0, 10))}</td>
            <td><button type="button" class="admin-btn admin-btn--danger admin-btn--sm" data-customer-delete="${r.id}">Delete</button></td>
          </tr>`
            )
            .join("")
        : `<tr><td colspan="7" class="admin-empty">No customers</td></tr>`;

      body.querySelectorAll("[data-customer-delete]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!window.confirm("Delete this customer?")) return;
          try {
            await api(
              `/api/admin/customers/${btn.getAttribute("data-customer-delete")}`,
              { method: "DELETE" }
            );
            toast("Customer deleted", "success");
            loadCustomers();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  function formToJson(form) {
    const fd = new FormData(form);
    const obj = {};
    fd.forEach((v, k) => {
      obj[k] = typeof v === "string" ? v.trim() : v;
    });
    return obj;
  }

  function bindForms() {
    const reviewsFilter = document.querySelector("[data-reviews-filter]");
    if (reviewsFilter && !reviewsFilter.dataset.bound) {
      reviewsFilter.dataset.bound = "1";
      reviewsFilter.addEventListener("change", () => loadReviews());
    }
    const reviewsRefresh = document.querySelector("[data-reviews-refresh]");
    if (reviewsRefresh && !reviewsRefresh.dataset.bound) {
      reviewsRefresh.dataset.bound = "1";
      reviewsRefresh.addEventListener("click", () => {
        loadReviews();
        toast("Reviews refreshed", "success");
      });
    }

    const usersRefresh = document.querySelector("[data-users-refresh]");
    if (usersRefresh && !usersRefresh.dataset.bound) {
      usersRefresh.dataset.bound = "1";
      usersRefresh.addEventListener("click", () => {
        loadUsers();
        toast("Users refreshed", "success");
      });
    }

    const userForm = document.getElementById("admin-user-form");
    if (userForm && !userForm.dataset.bound) {
      userForm.dataset.bound = "1";
      userForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(userForm);
        const username = String(fd.get("username") || "").trim();
        const password = String(fd.get("password") || "");
        const permissions = readPermCheckboxes(
          document.querySelector("[data-user-perm-grid]")
        );
        try {
          await api("/api/admin/users", {
            method: "POST",
            body: JSON.stringify({ username, password, permissions }),
          });
          userForm.reset();
          renderCreatePermGrid();
          toast("Staff user created", "success");
          loadUsers();
        } catch (ex) {
          toast(ex.message, "error");
        }
      });
    }

    const tileForm = document.getElementById("tile-upload-form");
    if (tileForm) {
      tileForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(tileForm);
        try {
          await api("/api/admin/tiles", { method: "POST", body: fd });
          tileForm.reset();
          toast("New arrival uploaded — shown on Home → Latest Collections", "success");
          loadTiles();
        } catch (ex) {
          toast(ex.message, "error");
        }
      });
    }

    const videoForm = document.getElementById("video-upload-form");
    if (videoForm) {
      videoForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(videoForm);
        try {
          await api("/api/admin/videos", { method: "POST", body: fd });
          videoForm.reset();
          toast("Video uploaded — active videos show on Home", "success");
          loadVideos();
        } catch (ex) {
          toast(ex.message, "error");
        }
      });
    }

    const cgForm = document.getElementById("concept-gallery-form");
    if (cgForm && !cgForm.dataset.bound) {
      cgForm.dataset.bound = "1";
      cgForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(cgForm);
        try {
          await api("/api/admin/concept-gallery", { method: "POST", body: fd });
          cgForm.reset();
          toast("Picture uploaded — check website Concept Gallery", "success");
          loadConceptGallery();
        } catch (ex) {
          toast(ex.message, "error");
        }
      });
    }

    const saleForm = document.getElementById("sale-form");
    if (saleForm) {
      saleForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const obj = formToJson(saleForm);
        obj.quantity = Number(obj.quantity || 1);
        obj.amount = Number(obj.amount || 0);
        try {
          await api("/api/admin/sales", {
            method: "POST",
            body: JSON.stringify(obj),
          });
          saleForm.reset();
          toast("Sale saved", "success");
          loadSales();
        } catch (ex) {
          toast(ex.message, "error");
        }
      });
    }

    const leadForm = document.getElementById("lead-form");
    if (leadForm) {
      leadForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          await api("/api/admin/leads", {
            method: "POST",
            body: JSON.stringify(formToJson(leadForm)),
          });
          leadForm.reset();
          toast("Lead saved", "success");
          loadLeads();
        } catch (ex) {
          toast(ex.message, "error");
        }
      });
    }

    const customerForm = document.getElementById("customer-form");
    if (customerForm) {
      customerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          await api("/api/admin/customers", {
            method: "POST",
            body: JSON.stringify(formToJson(customerForm)),
          });
          customerForm.reset();
          toast("Customer saved", "success");
          loadCustomers();
        } catch (ex) {
          toast(ex.message, "error");
        }
      });
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    initLogin();
    initApp();
  });
})();
