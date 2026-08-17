/**
 * Chalukya Admin — inventory, finance extras, exports, communications
 */
(function () {
  "use strict";

  function A() {
    return window.ChalukyaAdmin || {};
  }
  function api(path, opts) {
    return A().api(path, opts);
  }
  function toast(msg, type) {
    return A().toast(msg, type);
  }
  function esc(s) {
    return A().esc(s);
  }
  function money(n) {
    return A().money(n);
  }

  function fillExportButtons() {
    document.querySelectorAll("[data-export-kind]").forEach((host) => {
      if (host.dataset.ready) return;
      host.dataset.ready = "1";
      const kind = host.getAttribute("data-export-kind");
      host.innerHTML = `
        <button type="button" class="admin-btn admin-btn--outline admin-btn--sm" data-export="${kind}" data-fmt="xlsx">Excel</button>
        <button type="button" class="admin-btn admin-btn--outline admin-btn--sm" data-export="${kind}" data-fmt="pdf">PDF</button>
      `;
      host.querySelectorAll("[data-export]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const k = btn.getAttribute("data-export");
          const f = btn.getAttribute("data-fmt");
          window.location.href = `/api/admin/export/${k}?format=${f}`;
        });
      });
    });
    const db = document.querySelector("[data-admin-db-backup]");
    if (db && !db.dataset.ready) {
      db.dataset.ready = "1";
      db.addEventListener("click", (e) => {
        e.preventDefault();
        window.location.href = "/api/admin/backup/database";
      });
    }
  }

  function phoneDigits(p) {
    return String(p || "").replace(/\D+/g, "");
  }

  function mountCommActions(root) {
    root.querySelectorAll("[data-comm-row]").forEach((cell) => {
      if (cell.dataset.ready) return;
      cell.dataset.ready = "1";
      const et = cell.getAttribute("data-entity");
      const id = cell.getAttribute("data-id");
      const phone = cell.getAttribute("data-phone") || "";
      const email = cell.getAttribute("data-email") || "";
      const name = cell.getAttribute("data-name") || "";
      const dig = phoneDigits(phone);
      const wa = dig
        ? `https://wa.me/91${dig.slice(-10)}?text=${encodeURIComponent(
            `Hello ${name}, this is Chalukya Tiles. Following up regarding your enquiry.`
          )}`
        : "";
      const mail = email
        ? `mailto:${email}?subject=${encodeURIComponent("Chalukya Tiles — follow-up")}&body=${encodeURIComponent(
            `Hello ${name},\n\nThank you for contacting Chalukya Tiles.\n\n`
          )}`
        : "";
      const tel = phone ? `tel:${phone}` : "";

      cell.innerHTML = `
        <div class="admin-action-dd">
          <label class="sr-only" for="lead-act-${esc(id)}">Actions</label>
          <select
            id="lead-act-${esc(id)}"
            class="admin-action-select"
            data-comm-select
            data-entity="${esc(et)}"
            data-id="${esc(id)}"
            data-phone="${esc(phone)}"
            data-email="${esc(email)}"
            data-name="${esc(name)}"
            data-wa="${esc(wa)}"
            data-mail="${esc(mail)}"
            data-tel="${esc(tel)}"
            aria-label="Lead actions"
          >
            <option value="">Actions…</option>
            <option value="reminder">Reminder</option>
            <option value="whatsapp"${wa ? "" : " disabled"}>WhatsApp</option>
            <option value="phone"${tel ? "" : " disabled"}>Call / Phone</option>
            <option value="sms">SMS</option>
            <option value="email"${mail ? "" : " disabled"}>Email</option>
            <option value="followup">Follow-up / Intimation</option>
          </select>
        </div>
      `;

      const select = cell.querySelector("[data-comm-select]");
      if (!select) return;

      select.addEventListener("change", async () => {
        const act = select.value;
        select.value = "";
        if (!act) return;

        if (act === "reminder") {
          const when = window.prompt(
            "Reminder date-time (YYYY-MM-DDTHH:MM)",
            new Date(Date.now() + 86400000).toISOString().slice(0, 16)
          );
          if (!when) return;
          const note = window.prompt("Reminder note (optional)", "") || "";
          try {
            await api("/api/admin/reminders", {
              method: "POST",
              body: JSON.stringify({
                entity_type: et,
                entity_id: Number(id),
                reminder_at: when.length === 16 ? when + ":00" : when,
                reminder_note: note || null,
              }),
            });
            toast("Reminder set", "success");
          } catch (ex) {
            toast(ex.message, "error");
          }
          return;
        }

        if (act === "sms") {
          try {
            await api("/api/admin/communications", {
              method: "POST",
              body: JSON.stringify({
                entity_type: et,
                entity_id: Number(id),
                channel: "sms",
                detail: "SMS intent logged — provider not configured",
              }),
            });
            toast("SMS logged (provider not configured)", "success");
          } catch (ex) {
            toast(ex.message, "error");
          }
          return;
        }

        if (act === "followup") {
          try {
            await api("/api/admin/communications", {
              method: "POST",
              body: JSON.stringify({
                entity_type: et,
                entity_id: Number(id),
                channel: "followup",
                detail: "Follow-up / intimation logged",
              }),
            });
            toast("Follow-up logged", "success");
          } catch (ex) {
            toast(ex.message, "error");
          }
          return;
        }

        const channelMap = {
          whatsapp: "whatsapp",
          phone: "phone",
          email: "email",
        };
        const channel = channelMap[act];
        if (channel) {
          try {
            await api("/api/admin/communications", {
              method: "POST",
              body: JSON.stringify({
                entity_type: et,
                entity_id: Number(id),
                channel,
                detail: `${channel} action`,
              }),
            });
          } catch (_) {
            /* non-blocking */
          }
          if (act === "whatsapp" && wa) {
            window.open(wa, "_blank", "noopener");
          } else if (act === "phone" && tel) {
            window.location.href = tel;
          } else if (act === "email" && mail) {
            window.location.href = mail;
          } else {
            toast("Contact details missing for this action", "error");
          }
        }
      });
    });
  }

  let invCache = {};
  let invSubMap = {
    Tiles: [
      "Vitrified Tiles",
      "Ceramic Tiles",
      "Parking Tiles",
      "Outdoor Tiles",
      "Wooden Finish",
      "Marble Finish",
      "Bathroom Tiles",
      "Kitchen Tiles",
      "Elevation Tiles",
    ],
    Paste: ["Wall Paste", "Floor Paste", "Waterproofing Paste", "Joint Filler"],
    Adhesive: ["Tile Adhesive", "Epoxy Adhesive", "Cement Adhesive", "Stone Adhesive"],
    "Sanitary Wares": ["Pipes", "Showers", "Sinks", "Closets", "Faucets", "Accessories"],
    Beading: ["Corner Beading", "Edge Beading", "Transition Profiles", "Skirting"],
    Others: ["General", "Tools", "Accessories"],
  };

  const CUSTOM_SUB = "__custom__";

  function fillSubSelect(form, category, selected) {
    if (!form) return;
    const subSel = form.querySelector("[data-inv-sub-select]");
    const customWrap = form.querySelector("[data-inv-sub-custom-wrap]");
    const customInput = form.querySelector("[data-inv-sub-custom]");
    if (!subSel) return;
    const list = invSubMap[category] || ["General"];
    const sel = (selected || "").trim();
    const isCustom = sel && list.indexOf(sel) === -1;
    subSel.innerHTML =
      list
        .map(
          (s) =>
            `<option value="${esc(s)}"${s === sel ? " selected" : ""}>${esc(s)}</option>`
        )
        .join("") +
      `<option value="${CUSTOM_SUB}"${isCustom ? " selected" : ""}>Other / Custom…</option>`;
    if (customWrap) customWrap.hidden = !isCustom;
    if (customInput) {
      customInput.value = isCustom ? sel : "";
      customInput.required = isCustom;
    }
    toggleDimRow(form, category);
  }

  function toggleDimRow(form, category) {
    if (!form) return;
    const dimRow = form.querySelector("[data-inv-dim-row]");
    if (!dimRow) return;
    dimRow.hidden = String(category || "") !== "Tiles";
  }

  function fillListSubFilter(category) {
    const subFilter = document.querySelector("[data-inv-filter-sub]");
    if (!subFilter) return;
    const list = category && category !== "all" ? invSubMap[category] || [] : [];
    const prev = subFilter.value || "all";
    let opts = `<option value="all">All subcategories</option>`;
    list.forEach((s) => {
      opts += `<option value="${esc(s)}">${esc(s)}</option>`;
    });
    // Also allow free filter of known values from current list will be merged on load
    subFilter.innerHTML = opts;
    if ([...subFilter.options].some((o) => o.value === prev)) subFilter.value = prev;
    else subFilter.value = "all";
  }

  function bindCategorySubSelects(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-inv-cat-select]").forEach((catSel) => {
      if (catSel.dataset.subBound) return;
      catSel.dataset.subBound = "1";
      const form = catSel.closest("form");
      const subSel = form && form.querySelector("[data-inv-sub-select]");
      const customWrap = form && form.querySelector("[data-inv-sub-custom-wrap]");
      const customInput = form && form.querySelector("[data-inv-sub-custom]");

      fillSubSelect(form, catSel.value, subSel ? subSel.value : "");

      catSel.addEventListener("change", () => {
        fillSubSelect(form, catSel.value, "");
      });
      if (subSel) {
        subSel.addEventListener("change", () => {
          const isCustom = subSel.value === CUSTOM_SUB;
          if (customWrap) customWrap.hidden = !isCustom;
          if (customInput) {
            customInput.required = isCustom;
            if (!isCustom) customInput.value = "";
            if (isCustom) customInput.focus();
          }
        });
      }
    });
  }

  function resolveSubcategory(form) {
    const subSel = form.querySelector("[data-inv-sub-select]");
    const customInput = form.querySelector("[data-inv-sub-custom]");
    if (!subSel) return "";
    if (subSel.value === CUSTOM_SUB) {
      return (customInput && customInput.value.trim()) || "";
    }
    return (subSel.value || "").trim();
  }

  function openInvEditModal(item) {
    const modal = document.querySelector("[data-inv-edit-modal]");
    const form = document.getElementById("inventory-edit-form");
    if (!modal || !form || !item) return;
    bindCategorySubSelects(form);
    form.elements.namedItem("id").value = item.id;
    const fields = [
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
      "tax_gst",
      "supplier",
      "status",
      "show_on_website",
      "colour",
      "pattern",
      "size_label",
      "finish",
      "item_date",
      "notes",
    ];
    fields.forEach((key) => {
      const el = form.elements.namedItem(key);
      if (!el) return;
      let val = item[key];
      if (val == null) val = "";
      if (key === "show_on_website") val = Number(item.show_on_website) === 1 ? "1" : "0";
      if (key === "item_date" && val) val = String(val).slice(0, 10);
      el.value = val;
    });
    fillSubSelect(
      form,
      item.category || "Tiles",
      item.material_category || ""
    );
    ["dim_length", "dim_width", "dim_unit"].forEach((key) => {
      const el = form.elements.namedItem(key);
      if (!el) return;
      el.value = item[key] != null ? item[key] : key === "dim_unit" ? "mm" : "";
    });
    modal.hidden = false;
    document.body.classList.add("admin-modal-open");
    const nameInput = form.elements.namedItem("name");
    if (nameInput) nameInput.focus();
  }

  function closeInvEditModal() {
    const modal = document.querySelector("[data-inv-edit-modal]");
    if (modal) modal.hidden = true;
    document.body.classList.remove("admin-modal-open");
  }

  function bindInvEditModal() {
    const modal = document.querySelector("[data-inv-edit-modal]");
    const form = document.getElementById("inventory-edit-form");
    if (!modal || !form || form.dataset.bound) return;
    form.dataset.bound = "1";

    modal.querySelectorAll("[data-inv-edit-close]").forEach((el) => {
      el.addEventListener("click", closeInvEditModal);
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal && !modal.hidden) closeInvEditModal();
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = form.elements.namedItem("id").value;
      const sub = resolveSubcategory(form);
      if (!sub) {
        toast("Please choose or enter a subcategory", "error");
        return;
      }
      const payload = {
        name: form.elements.namedItem("name").value.trim(),
        category: form.elements.namedItem("category").value,
        brand: form.elements.namedItem("brand").value.trim() || null,
        sku: form.elements.namedItem("sku").value.trim() || null,
        description: form.elements.namedItem("description").value.trim() || null,
        unit: form.elements.namedItem("unit").value.trim() || "pcs",
        quantity: Number(form.elements.namedItem("quantity").value || 0),
        reorder_level: Number(form.elements.namedItem("reorder_level").value || 0),
        purchase_price: Number(form.elements.namedItem("purchase_price").value || 0),
        selling_price: Number(form.elements.namedItem("selling_price").value || 0),
        tax_gst: Number(form.elements.namedItem("tax_gst").value || 0),
        supplier: form.elements.namedItem("supplier").value.trim() || null,
        status: form.elements.namedItem("status").value || "active",
        show_on_website: Number(form.elements.namedItem("show_on_website").value || 0),
        colour: form.elements.namedItem("colour").value.trim() || null,
        pattern: form.elements.namedItem("pattern").value.trim() || "",
        material_category: sub,
        size_label: form.elements.namedItem("size_label")
          ? form.elements.namedItem("size_label").value.trim() || null
          : null,
        finish: form.elements.namedItem("finish").value.trim() || null,
        item_date: form.elements.namedItem("item_date").value || null,
        notes: form.elements.namedItem("notes").value.trim() || null,
        dim_length: form.elements.namedItem("dim_length")
          ? Number(form.elements.namedItem("dim_length").value || 0) || null
          : null,
        dim_width: form.elements.namedItem("dim_width")
          ? Number(form.elements.namedItem("dim_width").value || 0) || null
          : null,
        dim_unit: form.elements.namedItem("dim_unit")
          ? form.elements.namedItem("dim_unit").value || null
          : null,
      };
      try {
        await api(`/api/admin/inventory/${id}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
        toast("Inventory updated", "success");
        closeInvEditModal();
        loadInventory();
      } catch (ex) {
        toast(ex.message, "error");
      }
    });
  }

  async function loadInventory() {
    fillExportButtons();
    bindInvEditModal();
    const q = (document.querySelector("[data-inv-search]") || {}).value || "";
    const cat = (document.querySelector("[data-inv-filter-cat]") || {}).value || "all";
    const subF = (document.querySelector("[data-inv-filter-sub]") || {}).value || "all";
    const low = (document.querySelector("[data-inv-low-only]") || {}).value || "0";
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (cat) params.set("category", cat);
    if (low === "1") params.set("low_stock", "1");
    try {
      const data = await api("/api/admin/inventory?" + params.toString());
      if (data.subcategories) invSubMap = data.subcategories;
      fillListSubFilter(cat);
      // re-apply subcategory selection after rebuild
      const subEl = document.querySelector("[data-inv-filter-sub]");
      if (subEl && subF !== "all") {
        // ensure option exists for custom subs present in data
        let items0 = data.items || [];
        const known = new Set(
          [...subEl.options].map((o) => o.value)
        );
        items0.forEach((it) => {
          const s = (it.material_category || "").trim();
          if (s && !known.has(s)) {
            const opt = document.createElement("option");
            opt.value = s;
            opt.textContent = s;
            subEl.appendChild(opt);
            known.add(s);
          }
        });
        if ([...subEl.options].some((o) => o.value === subF)) subEl.value = subF;
      }
      const body = document.querySelector("[data-inventory-table]");
      if (!body) return;
      let items = data.items || [];
      if (subF && subF !== "all") {
        items = items.filter(
          (it) => String(it.material_category || "").trim() === subF
        );
      }
      invCache = {};
      items.forEach((it) => {
        invCache[it.id] = it;
      });
      body.innerHTML = items.length
        ? items
            .map(
              (r) => `<tr class="admin-inv-row ${r.is_low_stock ? "is-low-stock" : ""}">
            <td>
              <div class="admin-inv-name-cell">
                <span>${esc(r.name)}</span>
                <button
                  type="button"
                  class="admin-inv-edit-btn"
                  data-inv-edit="${r.id}"
                  title="Edit stock &amp; details"
                  aria-label="Edit ${esc(r.name)}"
                >
                  <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
                    <path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zm17.71-10.04a1 1 0 0 0 0-1.41l-2.51-2.51a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 2-1.66z"/>
                  </svg>
                </button>
              </div>
            </td>
            <td>${esc(r.category)}</td>
            <td><span class="admin-sub-tag">${esc(r.material_category || "—")}</span></td>
            <td>${esc(r.sku || "—")}</td>
            <td><strong>${esc(r.quantity)}</strong></td>
            <td>${esc(r.unit || "—")}</td>
            <td>${esc(r.reorder_level)}</td>
            <td>${money(r.selling_price)}</td>
            <td>
              <label class="admin-vis-toggle ${Number(r.show_on_website) === 1 ? "is-public" : "is-private"}" title="Post item on website Products page">
                <input
                  type="checkbox"
                  data-vis-toggle="${r.id}"
                  ${Number(r.show_on_website) === 1 ? "checked" : ""}
                  aria-label="Post in website"
                >
                <span class="admin-vis-toggle__track" aria-hidden="true">
                  <span class="admin-vis-toggle__thumb"></span>
                </span>
                <span class="admin-vis-toggle__label" data-vis-label>${Number(r.show_on_website) === 1 ? "Posted" : "Not posted"}</span>
              </label>
            </td>
            <td>${esc(r.status)}${r.is_low_stock ? ' <span class="admin-status admin-status--pending">Low</span>' : ""}</td>
            <td>
              <button type="button" class="admin-btn admin-btn--outline admin-btn--sm" data-stock-in="${r.id}">In</button>
              <button type="button" class="admin-btn admin-btn--outline admin-btn--sm" data-stock-out="${r.id}">Out</button>
            </td>
            <td><button type="button" class="admin-btn admin-btn--danger admin-btn--sm" data-inv-del="${r.id}">Del</button></td>
          </tr>`
            )
            .join("")
        : `<tr><td colspan="12" class="admin-empty">No inventory items</td></tr>`;

      body.querySelectorAll("[data-inv-edit]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const id = btn.getAttribute("data-inv-edit");
          const item = invCache[id];
          if (item) openInvEditModal(item);
          else toast("Item not found", "error");
        });
      });

      body.querySelectorAll("[data-vis-toggle]").forEach((input) => {
        input.addEventListener("change", async () => {
          const itemId = input.getAttribute("data-vis-toggle");
          const on = input.checked ? 1 : 0;
          const wrap = input.closest(".admin-vis-toggle");
          const label = wrap && wrap.querySelector("[data-vis-label]");
          try {
            await api(`/api/admin/inventory/${itemId}/visibility`, {
              method: "PATCH",
              body: JSON.stringify({ show_on_website: on }),
            });
            if (wrap) {
              wrap.classList.toggle("is-public", on === 1);
              wrap.classList.toggle("is-private", on === 0);
            }
            if (label) label.textContent = on === 1 ? "Public" : "Private";
            toast(
              on === 1
                ? "Posted on website Products page"
                : "Removed from website Products page",
              "success"
            );
          } catch (ex) {
            input.checked = !input.checked;
            toast(ex.message, "error");
          }
        });
      });

      body.querySelectorAll("[data-stock-in]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const qty = window.prompt("Stock IN quantity", "1");
          if (!qty) return;
          try {
            await api(`/api/admin/inventory/${btn.getAttribute("data-stock-in")}/stock`, {
              method: "POST",
              body: JSON.stringify({ movement: "in", quantity: Number(qty) }),
            });
            toast("Stock updated", "success");
            loadInventory();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });
      body.querySelectorAll("[data-stock-out]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const qty = window.prompt("Stock OUT quantity", "1");
          if (!qty) return;
          try {
            await api(`/api/admin/inventory/${btn.getAttribute("data-stock-out")}/stock`, {
              method: "POST",
              body: JSON.stringify({ movement: "out", quantity: Number(qty) }),
            });
            toast("Stock updated", "success");
            loadInventory();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });
      body.querySelectorAll("[data-inv-del]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!window.confirm("Delete inventory item?")) return;
          try {
            await api(`/api/admin/inventory/${btn.getAttribute("data-inv-del")}`, {
              method: "DELETE",
            });
            toast("Deleted", "success");
            loadInventory();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  async function loadInvOverview() {
    fillExportButtons();
    try {
      const dash = await api("/api/admin/dashboard");
      const s = dash.stats || {};
      const el = document.querySelector("[data-inv-overview-stats]");
      if (el) {
        el.innerHTML = [
          card("Items", s.inventory_count || 0, "Active catalogue"),
          card("Low stock", s.low_stock || 0, "At or below reorder"),
          card("New Arrivals", s.tiles || 0, "New arrival media"),
          card("Web products", "—", "Flag show_on_website"),
        ].join("");
      }
      const low = await api("/api/admin/inventory?low_stock=1");
      const body = document.querySelector("[data-low-stock-table]");
      if (body) {
        const items = low.items || [];
        body.innerHTML = items.length
          ? items
              .map(
                (r) => `<tr>
              <td>${esc(r.name)}</td><td>${esc(r.category)}</td>
              <td>${esc(r.quantity)}</td><td>${esc(r.reorder_level)}</td>
              <td>${esc(r.status)}</td></tr>`
              )
              .join("")
          : `<tr><td colspan="5" class="admin-empty">No low-stock items</td></tr>`;
      }
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  function card(label, value, meta) {
    return `<article class="admin-stat">
      <span class="admin-stat__label">${esc(label)}</span>
      <span class="admin-stat__value">${esc(value)}</span>
      <span class="admin-stat__meta">${esc(meta || "")}</span>
    </article>`;
  }

  async function loadReturns() {
    fillExportButtons();
    try {
      const data = await api("/api/admin/sales-returns");
      const body = document.querySelector("[data-returns-table]");
      if (!body) return;
      const items = data.items || [];
      body.innerHTML = items.length
        ? items
            .map(
              (r) => `<tr>
            <td>${esc(r.return_no)}</td><td>${esc(r.original_invoice || "—")}</td>
            <td>${esc(r.customer_name)}</td><td>${esc(r.product_name)}</td>
            <td>${esc(r.quantity)}</td><td>${money(r.amount)}</td>
            <td>${esc(r.return_date)}</td>
            <td><button type="button" class="admin-btn admin-btn--danger admin-btn--sm" data-ret-del="${r.id}">Del</button></td>
          </tr>`
            )
            .join("")
        : `<tr><td colspan="8" class="admin-empty">No returns</td></tr>`;
      body.querySelectorAll("[data-ret-del]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!window.confirm("Delete return?")) return;
          try {
            await api(`/api/admin/sales-returns/${btn.getAttribute("data-ret-del")}`, {
              method: "DELETE",
            });
            toast("Deleted", "success");
            loadReturns();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  async function loadPurchases() {
    fillExportButtons();
    try {
      const data = await api("/api/admin/purchases");
      const body = document.querySelector("[data-purchases-table]");
      if (!body) return;
      const items = data.items || [];
      body.innerHTML = items.length
        ? items
            .map(
              (r) => `<tr>
            <td>${esc(r.purchase_no)}</td><td>${esc(r.supplier_name)}</td>
            <td>${esc(r.product_name)}</td><td>${esc(r.category || "—")}</td>
            <td>${esc(r.quantity)}</td><td>${money(r.amount)}</td>
            <td>${esc(r.purchase_date)}</td>
            <td><button type="button" class="admin-btn admin-btn--danger admin-btn--sm" data-pur-del="${r.id}">Del</button></td>
          </tr>`
            )
            .join("")
        : `<tr><td colspan="8" class="admin-empty">No purchases</td></tr>`;
      body.querySelectorAll("[data-pur-del]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!window.confirm("Delete purchase?")) return;
          try {
            await api(`/api/admin/purchases/${btn.getAttribute("data-pur-del")}`, {
              method: "DELETE",
            });
            toast("Deleted", "success");
            loadPurchases();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
      });
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  function bindForms() {
    const invForm = document.getElementById("inventory-form");
    if (invForm && !invForm.dataset.bound) {
      invForm.dataset.bound = "1";
      bindCategorySubSelects(invForm);
      invForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const sub = resolveSubcategory(invForm);
        if (!sub) {
          toast("Please choose or enter a subcategory", "error");
          return;
        }
        const fd = new FormData(invForm);
        fd.set("material_category", sub);
        fd.delete("material_category_custom");
        try {
          await api("/api/admin/inventory", { method: "POST", body: fd });
          invForm.reset();
          fillSubSelect(invForm, invForm.querySelector("[data-inv-cat-select]").value, "");
          toast("Inventory item saved — set Public to show on Products", "success");
        } catch (ex) {
          toast(ex.message, "error");
        }
      });
    }
    const retForm = document.getElementById("return-form");
    if (retForm && !retForm.dataset.bound) {
      retForm.dataset.bound = "1";
      retForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(retForm);
        const obj = Object.fromEntries(fd.entries());
        obj.quantity = Number(obj.quantity || 1);
        obj.amount = Number(obj.amount || 0);
        try {
          await api("/api/admin/sales-returns", {
            method: "POST",
            body: JSON.stringify(obj),
          });
          retForm.reset();
          toast("Return saved", "success");
          loadReturns();
        } catch (ex) {
          toast(ex.message, "error");
        }
      });
    }
    const purForm = document.getElementById("purchase-form");
    if (purForm && !purForm.dataset.bound) {
      purForm.dataset.bound = "1";
      purForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(purForm);
        const obj = Object.fromEntries(fd.entries());
        obj.quantity = Number(obj.quantity || 1);
        obj.amount = Number(obj.amount || 0);
        if (obj.inventory_id) obj.inventory_id = Number(obj.inventory_id);
        else delete obj.inventory_id;
        try {
          await api("/api/admin/purchases", {
            method: "POST",
            body: JSON.stringify(obj),
          });
          purForm.reset();
          toast("Purchase saved", "success");
          loadPurchases();
        } catch (ex) {
          toast(ex.message, "error");
        }
      });
    }
    const invRef = document.querySelector("[data-inv-refresh]");
    if (invRef && !invRef.dataset.bound) {
      invRef.dataset.bound = "1";
      invRef.addEventListener("click", () => loadInventory());
    }
    const catFilter = document.querySelector("[data-inv-filter-cat]");
    if (catFilter && !catFilter.dataset.bound) {
      catFilter.dataset.bound = "1";
      catFilter.addEventListener("change", () => {
        fillListSubFilter(catFilter.value);
        loadInventory();
      });
    }
    const subFilter = document.querySelector("[data-inv-filter-sub]");
    if (subFilter && !subFilter.dataset.bound) {
      subFilter.dataset.bound = "1";
      subFilter.addEventListener("change", () => loadInventory());
    }
    const importBtn = document.querySelector("[data-import-run]");
    if (importBtn && !importBtn.dataset.bound) {
      importBtn.dataset.bound = "1";
      importBtn.addEventListener("click", async () => {
        const ta = document.querySelector("[data-import-json]");
        if (!ta) return;
        let payload;
        try {
          payload = JSON.parse(ta.value || "{}");
        } catch (_) {
          toast("Invalid JSON", "error");
          return;
        }
        try {
          const res = await api("/api/admin/import/json", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          toast(
            `Imported inventory ${res.created_inventory || 0}, customers ${res.created_customers || 0}` +
              (res.errors && res.errors.length ? ` · ${res.errors.length} errors` : ""),
            res.errors && res.errors.length ? "error" : "success"
          );
        } catch (ex) {
          toast(ex.message, "error");
        }
      });
    }
    document.querySelectorAll("[data-logs-refresh]").forEach((btn) => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        const kind = btn.getAttribute("data-logs-refresh");
        if (kind === "app") loadAppLogs();
        else loadUserLogs();
      });
    });
  }

  async function loadAppLogs() {
    try {
      const data = await api("/api/admin/logs/app?limit=200");
      const body = document.querySelector("[data-app-logs-table]");
      if (!body) return;
      const items = data.items || [];
      body.innerHTML = items.length
        ? items
            .map(
              (r) => `<tr>
            <td>${esc(r.created_at)}</td>
            <td>${esc(r.level)}</td>
            <td>${esc(r.source)}</td>
            <td>${esc(r.message)}</td>
            <td>${esc(r.detail || "—")}</td>
          </tr>`
            )
            .join("")
        : `<tr><td colspan="5" class="admin-empty">No application logs yet</td></tr>`;
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  async function loadUserLogs() {
    try {
      const data = await api("/api/admin/logs/user?limit=200");
      const body = document.querySelector("[data-user-logs-table]");
      if (!body) return;
      const items = data.items || [];
      body.innerHTML = items.length
        ? items
            .map(
              (r) => `<tr>
            <td>${esc(r.created_at)}</td>
            <td>${esc(r.username)}</td>
            <td>${esc(r.action)}</td>
            <td>${esc(r.entity_type || "—")}${r.entity_id != null ? ":" + r.entity_id : ""}</td>
            <td>${esc(r.detail || "—")}</td>
            <td>${esc(r.ip || "—")}</td>
          </tr>`
            )
            .join("")
        : `<tr><td colspan="6" class="admin-empty">No user logs yet</td></tr>`;
    } catch (ex) {
      toast(ex.message, "error");
    }
  }

  function load(name) {
    fillExportButtons();
    bindForms();
    bindCategorySubSelects(document);
    if (name === "inventory" || name === "inventory-add") return loadInventory();
    if (name === "inv-overview") return loadInvOverview();
    if (name === "sales-returns") return loadReturns();
    if (name === "purchases") return loadPurchases();
    if (name === "data-tools") {
      fillExportButtons();
      return;
    }
    if (name === "app-logs") return loadAppLogs();
    if (name === "user-logs") return loadUserLogs();
    if (name === "dashboard" || name === "sales" || name === "leads" || name === "queries" || name === "customers" || name === "tiles") {
      fillExportButtons();
    }
  }

  window.ChalukyaAdminBiz = {
    load,
    mountCommActions,
    fillExportButtons,
  };

  document.addEventListener("DOMContentLoaded", () => {
    fillExportButtons();
    bindForms();
    bindCategorySubSelects(document);
    // Prefetch subcategory map
    api("/api/admin/inventory")
      .then((data) => {
        if (data && data.subcategories) invSubMap = data.subcategories;
        bindCategorySubSelects(document);
      })
      .catch(() => {
        bindCategorySubSelects(document);
      });
  });
})();
