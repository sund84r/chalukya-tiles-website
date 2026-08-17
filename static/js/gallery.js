/**
 * Chalukya Tiles — gallery.js
 * Category filters, masonry item visibility, accessible lightbox with zoom.
 */

(function () {
  "use strict";

  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  /* ----------------------------------------------------------------------
     Filters
     ---------------------------------------------------------------------- */
  function initGalleryFilters() {
    const bar = document.querySelector("[data-gallery-filters]");
    const grid = document.querySelector("[data-gallery-grid]");
    if (!bar || !grid) return;

    const buttons = Array.from(bar.querySelectorAll("[data-filter]"));
    const items = Array.from(grid.querySelectorAll("[data-category]"));
    const countEl = document.querySelector("[data-gallery-count]");
    const emptyEl = document.querySelector("[data-gallery-empty]");
    const labelEl = document.querySelector("[data-gallery-category-label]");

    function applyFilter(filter) {
      let visible = 0;

      items.forEach((item) => {
        const match = filter === "all" || item.dataset.category === filter;
        item.hidden = !match;
        item.classList.toggle("is-hidden", !match);
        if (match) visible += 1;
      });

      buttons.forEach((btn) => {
        const active = btn.dataset.filter === filter;
        btn.classList.toggle("is-active", active);
        btn.setAttribute("aria-pressed", active ? "true" : "false");
      });

      if (countEl) countEl.textContent = String(visible);

      if (labelEl) {
        if (filter === "all") {
          labelEl.textContent = "All categories";
        } else {
          const activeBtn = buttons.find((b) => b.dataset.filter === filter);
          labelEl.textContent = activeBtn
            ? activeBtn.textContent.trim()
            : filter;
        }
      }

      if (emptyEl) {
        emptyEl.classList.toggle("is-visible", visible === 0);
        emptyEl.hidden = visible !== 0;
      }
    }

    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        applyFilter(btn.dataset.filter || "all");
      });
    });

    document.querySelectorAll("[data-gallery-reset]").forEach((btn) => {
      btn.addEventListener("click", () => applyFilter("all"));
    });

    const params = new URLSearchParams(window.location.search);
    const fromQuery = params.get("category");
    const initial = buttons.some((b) => b.dataset.filter === fromQuery)
      ? fromQuery
      : "all";

    applyFilter(initial);
  }

  /* ----------------------------------------------------------------------
     Lightbox
     ---------------------------------------------------------------------- */
  function initLightbox() {
    const root = document.querySelector("[data-lightbox]");
    const grid = document.querySelector("[data-gallery-grid]");
    if (!root || !grid) return;

    const stage = root.querySelector("[data-lightbox-stage]");
    const captionTitle = root.querySelector("[data-lightbox-title]");
    const captionMeta = root.querySelector("[data-lightbox-meta]");
    const counter = root.querySelector("[data-lightbox-counter]");
    const btnClose = root.querySelector("[data-lightbox-close]");
    const btnPrev = root.querySelector("[data-lightbox-prev]");
    const btnNext = root.querySelector("[data-lightbox-next]");
    const backdrop = root.querySelector("[data-lightbox-backdrop]");

    let items = [];
    let index = 0;
    let lastFocus = null;
    let mediaEl = null;

    function getVisibleItems() {
      return Array.from(
        grid.querySelectorAll(".gallery-item[data-category]:not([hidden])")
      );
    }

    function trapFocus(event) {
      if (event.key !== "Tab" || !root.classList.contains("is-open")) return;
      const focusable = root.querySelectorAll(
        'button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
      );
      const list = Array.from(focusable).filter(
        (el) => el.offsetParent !== null || el === btnClose
      );
      if (!list.length) return;
      const first = list[0];
      const last = list[list.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    function clearMedia() {
      if (mediaEl && mediaEl.tagName === "VIDEO") {
        mediaEl.pause();
      }
      if (stage) stage.innerHTML = "";
      mediaEl = null;
    }

    function render() {
      const item = items[index];
      if (!item || !stage) return;

      clearMedia();

      const type = item.dataset.type || "image";
      const src = item.dataset.src || "";
      const alt = item.dataset.alt || item.dataset.title || "Gallery image";
      const title = item.dataset.title || "";
      const meta = item.dataset.meta || "";

      if (type === "video") {
        mediaEl = document.createElement("video");
        mediaEl.className = "lightbox__media lightbox__media--video";
        mediaEl.controls = true;
        mediaEl.playsInline = true;
        mediaEl.setAttribute("controlsList", "nodownload");
        if (item.dataset.poster) {
          mediaEl.poster = item.dataset.poster;
        }
        // Prefer data-src; fall back to nested source
        const nested = item.querySelector("video source, video");
        if (src) {
          mediaEl.src = src;
        } else if (nested && nested.src) {
          mediaEl.src = nested.src;
        } else if (nested && nested.getAttribute("src")) {
          mediaEl.src = nested.getAttribute("src");
        }
        mediaEl.addEventListener(
          "loadeddata",
          () => mediaEl.classList.add("is-loaded"),
          { once: true }
        );
        // If no real video file, still show poster frame state
        window.setTimeout(() => {
          if (mediaEl) mediaEl.classList.add("is-loaded");
        }, 80);
      } else {
        mediaEl = document.createElement("img");
        mediaEl.className = "lightbox__media";
        mediaEl.alt = alt;
        mediaEl.decoding = "async";
        mediaEl.addEventListener(
          "load",
          () => mediaEl.classList.add("is-loaded"),
          { once: true }
        );
        mediaEl.src = src;
        if (mediaEl.complete) mediaEl.classList.add("is-loaded");
      }

      stage.appendChild(mediaEl);

      if (captionTitle) captionTitle.textContent = title;
      if (captionMeta) captionMeta.textContent = meta;
      if (counter) {
        counter.textContent = `${index + 1} / ${items.length}`;
      }

      if (btnPrev) btnPrev.disabled = items.length < 2;
      if (btnNext) btnNext.disabled = items.length < 2;
    }

    function open(startIndex) {
      items = getVisibleItems();
      if (!items.length) return;

      index = Math.max(0, Math.min(startIndex, items.length - 1));
      lastFocus = document.activeElement;

      root.classList.add("is-open");
      root.setAttribute("aria-hidden", "false");
      document.body.classList.add("lightbox-open");
      render();

      window.setTimeout(() => {
        if (btnClose) btnClose.focus();
      }, 50);
    }

    function close() {
      root.classList.remove("is-open");
      root.setAttribute("aria-hidden", "true");
      document.body.classList.remove("lightbox-open");
      clearMedia();
      if (lastFocus && typeof lastFocus.focus === "function") {
        lastFocus.focus({ preventScroll: true });
      }
    }

    function next() {
      if (items.length < 2) return;
      index = (index + 1) % items.length;
      render();
    }

    function prev() {
      if (items.length < 2) return;
      index = (index - 1 + items.length) % items.length;
      render();
    }

    grid.addEventListener("click", (event) => {
      const item = event.target.closest(".gallery-item[data-category]");
      if (!item || item.hidden) return;
      // Ignore pure filter chrome
      const visible = getVisibleItems();
      const i = visible.indexOf(item);
      if (i === -1) return;
      open(i);
    });

    grid.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const item = event.target.closest(".gallery-item[data-category]");
      if (!item) return;
      event.preventDefault();
      const visible = getVisibleItems();
      const i = visible.indexOf(item);
      if (i !== -1) open(i);
    });

    if (btnClose) btnClose.addEventListener("click", close);
    if (backdrop) backdrop.addEventListener("click", close);
    if (btnNext) btnNext.addEventListener("click", next);
    if (btnPrev) btnPrev.addEventListener("click", prev);

    document.addEventListener("keydown", (event) => {
      if (!root.classList.contains("is-open")) return;
      if (event.key === "Escape") {
        event.preventDefault();
        close();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        next();
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        prev();
      } else {
        trapFocus(event);
      }
    });
  }

  /* ----------------------------------------------------------------------
     Lazy video posters in grid (optional play on hover desktop)
     ---------------------------------------------------------------------- */
  function initInlineVideos() {
    if (prefersReducedMotion) return;

    document.querySelectorAll("[data-gallery-grid] video[data-hover-play]").forEach((video) => {
      const item = video.closest(".gallery-item");
      if (!item) return;

      item.addEventListener("mouseenter", () => {
        const p = video.play();
        if (p && typeof p.catch === "function") p.catch(() => {});
      });
      item.addEventListener("mouseleave", () => {
        video.pause();
        video.currentTime = 0;
      });
    });
  }

  function boot() {
    initGalleryFilters();
    initLightbox();
    initInlineVideos();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
