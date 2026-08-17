/**
 * Lightweight canvas charts for admin analytics (no external chart library).
 */
(function () {
  "use strict";

  function api(path, opts) {
    return (window.ChalukyaAdmin && window.ChalukyaAdmin.api
      ? window.ChalukyaAdmin.api(path, opts)
      : Promise.reject(new Error("Admin API not ready")));
  }

  function toast(msg, type) {
    if (window.ChalukyaAdmin && window.ChalukyaAdmin.toast) {
      window.ChalukyaAdmin.toast(msg, type);
    }
  }

  function clearCanvas(canvas) {
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth || 320;
    const h = canvas.height || 160;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { ctx, w, h };
  }

  function drawBars(canvas, points, color) {
    const { ctx, w, h } = clearCanvas(canvas);
    const pad = 28;
    const data = points || [];
    if (!data.length) {
      ctx.fillStyle = "#6b7c93";
      ctx.font = "12px Inter, sans-serif";
      ctx.fillText("No data", 12, 24);
      return;
    }
    const max = Math.max(...data.map((p) => Number(p.value) || 0), 1);
    const barW = (w - pad * 2) / data.length;
    data.forEach((p, i) => {
      const v = Number(p.value) || 0;
      const bh = ((h - pad * 1.5) * v) / max;
      const x = pad + i * barW + barW * 0.15;
      const y = h - pad - bh;
      ctx.fillStyle = color || "#2f7de1";
      ctx.fillRect(x, y, barW * 0.7, bh);
    });
    ctx.fillStyle = "#6b7c93";
    ctx.font = "10px Inter, sans-serif";
    data.forEach((p, i) => {
      const label = String(p.label || "").slice(-5);
      ctx.fillText(label, pad + i * barW + 2, h - 8);
    });
  }

  function drawHBars(canvas, points, color) {
    const { ctx, w, h } = clearCanvas(canvas);
    const data = points || [];
    if (!data.length) {
      ctx.fillStyle = "#6b7c93";
      ctx.font = "12px Inter, sans-serif";
      ctx.fillText("No data", 12, 24);
      return;
    }
    const max = Math.max(...data.map((p) => Number(p.value) || 0), 1);
    const rowH = (h - 16) / data.length;
    data.forEach((p, i) => {
      const v = Number(p.value) || 0;
      const bw = ((w - 100) * v) / max;
      const y = 8 + i * rowH;
      ctx.fillStyle = color || "#143064";
      ctx.fillRect(90, y + 4, Math.max(bw, 2), rowH - 8);
      ctx.fillStyle = "#0b1f4a";
      ctx.font = "11px Inter, sans-serif";
      ctx.fillText(String(p.label || "").slice(0, 12), 4, y + rowH * 0.65);
    });
  }

  function drawDonut(canvas, posted, total) {
    const { ctx, w, h } = clearCanvas(canvas);
    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(w, h) * 0.32;
    const t = Math.max(total, 1);
    const frac = Math.min(1, posted / t);
    ctx.lineWidth = 18;
    ctx.strokeStyle = "#d8e4f5";
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
    ctx.strokeStyle = "#2f7d4a";
    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * frac);
    ctx.stroke();
    ctx.fillStyle = "#0b1f4a";
    ctx.font = "bold 16px Poppins, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(String(posted), cx, cy - 2);
    ctx.font = "11px Inter, sans-serif";
    ctx.fillStyle = "#6b7c93";
    ctx.fillText("of " + String(total) + " posted", cx, cy + 14);
  }

  async function renderCharts() {
    try {
      const res = await api("/api/admin/analytics");
      const d = res.data || {};
      const sales = document.querySelector("[data-chart-sales]");
      const inv = document.querySelector("[data-chart-inv-cat]");
      const low = document.querySelector("[data-chart-low]");
      const posted = document.querySelector("[data-chart-posted]");
      if (sales) drawBars(sales, d.sales_by_day || [], "#2f7de1");
      if (inv) drawHBars(inv, d.inventory_by_category || [], "#143064");
      if (low) drawHBars(low, d.low_stock_items || [], "#c47b0a");
      if (posted) {
        drawDonut(
          posted,
          Number(d.posted_on_website || 0),
          Number(d.inventory_total || 0)
        );
      }
    } catch (ex) {
      toast(ex.message || "Charts failed", "error");
    }
  }

  function openCharts() {
    const panel = document.querySelector("[data-admin-charts-panel]");
    if (!panel) return;
    panel.hidden = false;
    document.body.classList.add("admin-modal-open");
    window.requestAnimationFrame(() => renderCharts());
  }

  function closeCharts() {
    const panel = document.querySelector("[data-admin-charts-panel]");
    if (panel) panel.hidden = true;
    document.body.classList.remove("admin-modal-open");
  }

  document.addEventListener("DOMContentLoaded", () => {
    const btn = document.querySelector("[data-admin-charts]");
    if (btn) btn.addEventListener("click", openCharts);
    document.querySelectorAll("[data-admin-charts-close]").forEach((el) => {
      el.addEventListener("click", closeCharts);
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeCharts();
    });
    window.addEventListener("resize", () => {
      const panel = document.querySelector("[data-admin-charts-panel]");
      if (panel && !panel.hidden) renderCharts();
    });
  });
})();
