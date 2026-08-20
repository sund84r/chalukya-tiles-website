/**
 * Chalukya Tiles — main.js
 * Global UI: loading screen, scroll-to-top, button ripple,
 * Intersection Observer animations, counters, typing, parallax.
 * Keep this lean — page-specific logic lives in feature modules.
 */

(function () {
  "use strict";

  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  /* ======================================================================
     1. Loading screen
     ====================================================================== */
  function initLoader() {
    const loader = document.querySelector("[data-loader]");
    if (!loader) return;

    const hide = () => {
      loader.classList.add("is-hidden");
      loader.setAttribute("aria-busy", "false");
      loader.setAttribute("aria-hidden", "true");
      // Remove from a11y tree after transition
      window.setTimeout(() => {
        if (loader.parentNode) {
          loader.style.display = "none";
        }
      }, 700);
    };

    if (document.readyState === "complete") {
      window.setTimeout(hide, prefersReducedMotion ? 0 : 400);
    } else {
      window.addEventListener("load", () => {
        window.setTimeout(hide, prefersReducedMotion ? 0 : 400);
      });
    }

    // Failsafe — never block the page
    window.setTimeout(hide, 4000);
  }

  /* ======================================================================
     2. Scroll to top
     ====================================================================== */
  function initScrollTop() {
    const btn = document.querySelector("[data-scroll-top]");
    if (!btn) return;

    const THRESHOLD = 400;
    let ticking = false;

    const update = () => {
      const show = window.scrollY > THRESHOLD;
      btn.classList.toggle("is-visible", show);
      btn.setAttribute("aria-hidden", show ? "false" : "true");
      btn.tabIndex = show ? 0 : -1;
      ticking = false;
    };

    window.addEventListener(
      "scroll",
      () => {
        if (!ticking) {
          window.requestAnimationFrame(update);
          ticking = true;
        }
      },
      { passive: true }
    );

    btn.addEventListener("click", (event) => {
      event.preventDefault();
      window.scrollTo({
        top: 0,
        behavior: prefersReducedMotion ? "auto" : "smooth",
      });
    });

    update();
  }

  /* ======================================================================
     3. Button ripple effect
     ====================================================================== */
  function initRipple() {
    document.addEventListener("click", (event) => {
      const btn = event.target.closest(".btn");
      if (!btn || btn.disabled || prefersReducedMotion) return;

      const rect = btn.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const ripple = document.createElement("span");
      ripple.className = "btn__ripple";
      ripple.style.width = `${size}px`;
      ripple.style.height = `${size}px`;
      ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
      ripple.style.top = `${event.clientY - rect.top - size / 2}px`;

      btn.appendChild(ripple);
      window.setTimeout(() => ripple.remove(), 650);
    });
  }

  /* ======================================================================
     4. Intersection Observer — scroll animations & image reveal
     ====================================================================== */
  function initScrollAnimations() {
    const targets = document.querySelectorAll(
      "[data-animate], .reveal-image"
    );
    if (!targets.length) return;

    if (prefersReducedMotion || !("IntersectionObserver" in window)) {
      targets.forEach((el) => {
        el.classList.add("is-inview");
        if (el.classList.contains("reveal-image")) {
          el.classList.add("is-revealed");
        }
      });
      return;
    }

    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const el = entry.target;
          el.classList.add("is-inview");
          if (el.classList.contains("reveal-image")) {
            el.classList.add("is-revealed");
          }
          obs.unobserve(el);
        });
      },
      {
        root: null,
        rootMargin: "0px 0px -8% 0px",
        threshold: 0.12,
      }
    );

    targets.forEach((el) => observer.observe(el));
  }

  /* ======================================================================
     5. Counter animation
     ====================================================================== */
  function animateCounter(el) {
    const target = Number(el.dataset.counterTarget || el.textContent || 0);
    const duration = Number(el.dataset.counterDuration || 1600);
    const suffix = el.dataset.counterSuffix || "";
    const prefix = el.dataset.counterPrefix || "";

    if (prefersReducedMotion || Number.isNaN(target)) {
      el.textContent = `${prefix}${target}${suffix}`;
      return;
    }

    const start = performance.now();
    const from = 0;

    const tick = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      // easeOutCubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = Math.round(from + (target - from) * eased);
      el.textContent = `${prefix}${value}${suffix}`;
      if (progress < 1) {
        requestAnimationFrame(tick);
      }
    };

    requestAnimationFrame(tick);
  }

  function initCounters() {
    const counters = document.querySelectorAll("[data-counter-target]");
    if (!counters.length) return;

    if (!("IntersectionObserver" in window)) {
      counters.forEach(animateCounter);
      return;
    }

    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          animateCounter(entry.target);
          obs.unobserve(entry.target);
        });
      },
      { threshold: 0.4 }
    );

    counters.forEach((el) => observer.observe(el));
  }

  /* ======================================================================
     6. Typing effect
     ====================================================================== */
  function initTyping() {
    const el = document.querySelector("[data-typing]");
    if (!el) return;

    const phrases = (el.dataset.typingPhrases || el.textContent || "")
      .split("|")
      .map((s) => s.trim())
      .filter(Boolean);

    if (!phrases.length) return;

    const textNode = el.querySelector("[data-typing-text]") || el;
    let caret = el.querySelector(".typing-caret");
    if (!caret) {
      caret = document.createElement("span");
      caret.className = "typing-caret";
      caret.setAttribute("aria-hidden", "true");
      el.appendChild(caret);
    }

    if (prefersReducedMotion) {
      textNode.textContent = phrases[0];
      caret.classList.add("is-done");
      return;
    }

    let phraseIndex = 0;
    let charIndex = 0;
    let deleting = false;

    const TYPE_MS = 70;
    const DELETE_MS = 40;
    const HOLD_MS = 1800;
    const GAP_MS = 400;

    const step = () => {
      const current = phrases[phraseIndex];

      if (!deleting) {
        charIndex += 1;
        textNode.textContent = current.slice(0, charIndex);
        if (charIndex === current.length) {
          window.setTimeout(() => {
            deleting = true;
            step();
          }, HOLD_MS);
          return;
        }
        window.setTimeout(step, TYPE_MS);
        return;
      }

      charIndex -= 1;
      textNode.textContent = current.slice(0, charIndex);
      if (charIndex === 0) {
        deleting = false;
        phraseIndex = (phraseIndex + 1) % phrases.length;
        window.setTimeout(step, GAP_MS);
        return;
      }
      window.setTimeout(step, DELETE_MS);
    };

    textNode.textContent = "";
    step();
  }

  /* ======================================================================
     7. Light parallax on hero layers
     ====================================================================== */
  function initParallax() {
    const layers = document.querySelectorAll("[data-parallax]");
    if (!layers.length || prefersReducedMotion) return;
    // Skip on phones — parallax crops/breaks the wide hero photo
    if (window.matchMedia("(max-width: 767px)").matches) return;

    let ticking = false;

    const update = () => {
      const y = window.scrollY;
      layers.forEach((layer) => {
        const speed = Number(layer.dataset.parallax || 0.25);
        // Only shift modestly while near top of page
        const offset = Math.min(y * speed, 180);
        layer.style.transform = `translate3d(0, ${offset}px, 0)`;
      });
      ticking = false;
    };

    window.addEventListener(
      "scroll",
      () => {
        if (!ticking) {
          requestAnimationFrame(update);
          ticking = true;
        }
      },
      { passive: true }
    );

    update();
  }

  /* ======================================================================
     8. Newsletter form (footer) — client-side only feedback
     ====================================================================== */
  function initNewsletter() {
    const form = document.querySelector("[data-newsletter-form]");
    if (!form) return;

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const input = form.querySelector('input[type="email"]');
      const note = form.parentElement.querySelector(
        "[data-newsletter-note]"
      );
      if (!input) return;

      const email = input.value.trim();
      const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

      if (!valid) {
        input.focus();
        if (note) {
          note.textContent = "Please enter a valid email address.";
        }
        return;
      }

      if (note) {
        note.textContent = "Thank you for subscribing. Welcome to Chalukya Tiles.";
      }
      form.reset();
    });
  }

  /* ======================================================================
     9. Current year in footer
     ====================================================================== */
  function initYear() {
    document.querySelectorAll("[data-year]").forEach((el) => {
      el.textContent = String(new Date().getFullYear());
    });
  }

  /* ======================================================================
     10. Product filters — main inventory category + sub-types under it
     Main:  [data-product-main-filters] [data-main-filter]
     Sub:   [data-product-sub-filters]  [data-sub-filter]
     Cards: [data-main-category] [data-sub-category]
     JSON:  #product-subcategories-data
     ====================================================================== */
  function initProductFilters() {
    const mainBar = document.querySelector("[data-product-main-filters]");
    const subBar = document.querySelector("[data-product-sub-filters]");
    const subWrap = document.querySelector("[data-product-sub-wrap]");
    const subParentLabel = document.querySelector("[data-sub-parent-label]");
    const grid = document.querySelector("[data-products-grid]");
    if (!mainBar || !grid) return;

    const mainButtons = Array.from(mainBar.querySelectorAll("[data-main-filter]"));
    const cards = Array.from(
      grid.querySelectorAll("[data-main-category], [data-category]")
    );
    const countEl = document.querySelector("[data-products-count]");
    const emptyEl = document.querySelector("[data-products-empty]");
    const categoryLabel = document.querySelector("[data-products-category-label]");

    let subMap = {};
    const jsonEl = document.getElementById("product-subcategories-data");
    if (jsonEl) {
      try {
        subMap = JSON.parse(jsonEl.textContent || "{}") || {};
      } catch (_) {
        subMap = {};
      }
    }

    let activeMain = "all";
    let activeSub = "all";

    function mainLabel(slug) {
      const btn = mainButtons.find((b) => b.dataset.mainFilter === slug);
      return btn ? btn.textContent.trim() : slug;
    }

    function setMainActive(main) {
      mainButtons.forEach((btn) => {
        const on = btn.dataset.mainFilter === main;
        btn.classList.toggle("is-active", on);
        btn.setAttribute("aria-pressed", on ? "true" : "false");
      });
    }

    function renderSubFilters(main) {
      if (!subBar || !subWrap) return;
      if (main === "all") {
        subWrap.hidden = true;
        subBar.innerHTML = "";
        return;
      }
      const list = subMap[main] || [];
      if (!list.length) {
        // Build from cards currently under this main
        const found = {};
        cards.forEach((card) => {
          if ((card.dataset.mainCategory || "") === main) {
            const s = card.dataset.subCategory || card.dataset.category || "general";
            if (!found[s]) {
              found[s] = s
                .split("-")
                .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                .join(" ");
            }
          }
        });
        const keys = Object.keys(found);
        if (!keys.length) {
          subWrap.hidden = true;
          subBar.innerHTML = "";
          return;
        }
        subBar.innerHTML =
          `<button type="button" class="filter-btn is-active" data-sub-filter="all" aria-pressed="true">All types</button>` +
          keys
            .sort()
            .map(
              (s) =>
                `<button type="button" class="filter-btn" data-sub-filter="${s}" aria-pressed="false">${found[s]}</button>`
            )
            .join("");
      } else {
        subBar.innerHTML =
          `<button type="button" class="filter-btn is-active" data-sub-filter="all" aria-pressed="true">All types</button>` +
          list
            .map(
              (item) =>
                `<button type="button" class="filter-btn" data-sub-filter="${item.slug}" aria-pressed="false">${item.label}</button>`
            )
            .join("");
      }
      subWrap.hidden = false;
      if (subParentLabel) subParentLabel.textContent = mainLabel(main);

      subBar.querySelectorAll("[data-sub-filter]").forEach((btn) => {
        btn.addEventListener("click", () => {
          activeSub = btn.dataset.subFilter || "all";
          applyFilters();
        });
      });
    }

    function applyFilters() {
      let visible = 0;
      cards.forEach((card) => {
        const main = card.dataset.mainCategory || "others";
        const sub = card.dataset.subCategory || card.dataset.category || "general";
        let match = true;
        if (activeMain !== "all" && main !== activeMain) match = false;
        if (match && activeSub !== "all" && sub !== activeSub) match = false;
        card.hidden = !match;
        card.classList.toggle("is-hidden", !match);
        if (match) visible += 1;
      });

      setMainActive(activeMain);

      if (subBar) {
        subBar.querySelectorAll("[data-sub-filter]").forEach((btn) => {
          const on = btn.dataset.subFilter === activeSub;
          btn.classList.toggle("is-active", on);
          btn.setAttribute("aria-pressed", on ? "true" : "false");
        });
      }

      if (countEl) countEl.textContent = String(visible);

      if (categoryLabel) {
        if (activeMain === "all") {
          categoryLabel.textContent = "All categories";
        } else if (activeSub === "all") {
          categoryLabel.textContent = mainLabel(activeMain) + " · all types";
        } else {
          const subBtn = subBar
            ? subBar.querySelector(`[data-sub-filter="${activeSub}"]`)
            : null;
          const subText = subBtn
            ? subBtn.textContent.trim()
            : activeSub;
          categoryLabel.textContent = mainLabel(activeMain) + " · " + subText;
        }
      }

      if (emptyEl) {
        emptyEl.classList.toggle("is-visible", visible === 0);
        emptyEl.hidden = visible !== 0;
      }

      cards.forEach((card) => {
        if (!card.hidden && card.hasAttribute("data-animate")) {
          card.classList.add("is-inview");
        }
      });
    }

    mainButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        activeMain = btn.dataset.mainFilter || "all";
        activeSub = "all";
        renderSubFilters(activeMain);
        applyFilters();
      });
    });

    document.querySelectorAll("[data-products-reset]").forEach((btn) => {
      btn.addEventListener("click", () => {
        activeMain = "all";
        activeSub = "all";
        renderSubFilters("all");
        applyFilters();
      });
    });

    // Deep-link: ?category=tiles or ?category=marble-finish or ?main=tiles&sub=...
    const params = new URLSearchParams(window.location.search);
    const fromMain = params.get("main") || params.get("category") || "";
    const fromSub = params.get("sub") || "";
    const fromHash = window.location.hash.replace(/^#/, "");
    const initial = fromMain || fromHash || "all";

    const mainSlugs = mainButtons.map((b) => b.dataset.mainFilter);
    if (mainSlugs.includes(initial)) {
      activeMain = initial;
      activeSub = fromSub || "all";
    } else if (initial !== "all") {
      // Treat as sub-category under Tiles (legacy deep-links)
      activeMain = "tiles";
      activeSub = initial;
    } else {
      activeMain = "all";
      activeSub = "all";
    }

    renderSubFilters(activeMain);
    if (activeSub !== "all" && subBar) {
      // ensure activeSub button exists; if not, reset
      if (!subBar.querySelector(`[data-sub-filter="${activeSub}"]`)) {
        activeSub = "all";
      }
    }
    applyFilters();
  }

  /* ======================================================================
     WhatsApp deep-link — open native app on phones
     ====================================================================== */
  function initWhatsAppDeepLink() {
    const links = document.querySelectorAll(
      'a[href*="api.whatsapp.com"], a[href*="wa.me"], a.float-btn--whatsapp'
    );
    if (!links.length) return;

    const isMobile = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);

    links.forEach((link) => {
      // Ensure country-code form for India (+91)
      try {
        const url = new URL(link.href, window.location.origin);
        if (url.hostname.includes("wa.me")) {
          const parts = url.pathname.replace(/^\//, "").split("?")[0];
          if (parts && !parts.startsWith("91") && parts.length === 10) {
            url.pathname = "/91" + parts;
            link.href = url.toString();
          }
        }
      } catch (_) {
        /* ignore bad URLs */
      }

      if (!isMobile) return;

      // Same-tab navigation triggers WhatsApp app more reliably than target=_blank
      link.addEventListener(
        "click",
        (e) => {
          e.preventDefault();
          window.location.href = link.href;
        },
        { passive: false }
      );
    });
  }

  /* ======================================================================
     Boot
     ====================================================================== */
  function boot() {
    initLoader();
    initScrollTop();
    initRipple();
    initScrollAnimations();
    initCounters();
    initTyping();
    initParallax();
    initNewsletter();
    initYear();
    initProductFilters();
    initWhatsAppDeepLink();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
