/**
 * Chalukya Tiles — navbar.js
 * Sticky header scroll state, mobile drawer, keyboard a11y.
 *
 * Mobile drawer is moved to document.body so it is never clipped by the
 * fixed header (backdrop-filter / height containing-block issues when scrolled).
 */

(function () {
  "use strict";

  const header = document.querySelector("[data-header]");
  const toggle = document.querySelector("[data-nav-toggle]");
  let drawer = document.querySelector("[data-nav-drawer]");
  let overlay = document.querySelector("[data-nav-overlay]");

  if (!header) return;

  const SCROLL_THRESHOLD = 40;
  let isOpen = false;
  let ticking = false;
  let scrollLockY = 0;

  /* ----------------------------------------------------------------------
     Portal drawer to <body> (full-viewport fixed layer)
     ---------------------------------------------------------------------- */
  if (drawer && drawer.parentElement !== document.body) {
    document.body.appendChild(drawer);
  }
  // Re-query overlay after portal (same node, keep reference)
  overlay = drawer ? drawer.querySelector("[data-nav-overlay]") : null;
  const drawerLinks = drawer ? drawer.querySelectorAll("a[href]") : [];

  /* ----------------------------------------------------------------------
     Scroll: transparent → solid
     ---------------------------------------------------------------------- */
  function updateScrollState() {
    // Do not thrash header classes while the menu is open
    if (!isOpen) {
      const scrolled = window.scrollY > SCROLL_THRESHOLD;
      header.classList.toggle("is-scrolled", scrolled);
    }
    ticking = false;
  }

  function onScroll() {
    if (!ticking) {
      window.requestAnimationFrame(updateScrollState);
      ticking = true;
    }
  }

  updateScrollState();
  window.addEventListener("scroll", onScroll, { passive: true });

  /* ----------------------------------------------------------------------
     Mobile drawer
     ---------------------------------------------------------------------- */
  function lockScroll(lock) {
    if (lock) {
      scrollLockY = window.scrollY || window.pageYOffset || 0;
      document.documentElement.classList.add("nav-open");
      document.body.classList.add("nav-open");
      document.body.style.top = `-${scrollLockY}px`;
      document.body.style.position = "fixed";
      document.body.style.width = "100%";
      document.body.style.left = "0";
      document.body.style.right = "0";
    } else {
      document.documentElement.classList.remove("nav-open");
      document.body.classList.remove("nav-open");
      document.body.style.position = "";
      document.body.style.top = "";
      document.body.style.width = "";
      document.body.style.left = "";
      document.body.style.right = "";
      window.scrollTo(0, scrollLockY);
    }
  }

  function setDrawer(open) {
    if (!toggle || !drawer) return;

    isOpen = open;
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    drawer.classList.toggle("is-open", open);
    drawer.setAttribute("aria-hidden", open ? "false" : "true");
    lockScroll(open);

    // Solid header chrome while open so logo/X stay readable over any page
    if (open) {
      header.classList.add("is-scrolled");
      const firstLink = drawer.querySelector("a, button");
      if (firstLink) {
        window.setTimeout(() => {
          try {
            firstLink.focus({ preventScroll: true });
          } catch (_) {
            /* ignore */
          }
        }, 50);
      }
    } else {
      updateScrollState();
    }
  }

  function closeDrawer() {
    setDrawer(false);
    if (toggle) {
      try {
        toggle.focus({ preventScroll: true });
      } catch (_) {
        /* ignore */
      }
    }
  }

  if (toggle && drawer) {
    toggle.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      setDrawer(!isOpen);
    });

    if (overlay) {
      overlay.addEventListener("click", closeDrawer);
    }

    drawerLinks.forEach((link) => {
      link.addEventListener("click", () => setDrawer(false));
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && isOpen) {
        closeDrawer();
      }
    });

    // Close drawer when resizing to desktop
    const mq = window.matchMedia("(min-width: 992px)");
    const onBreakpoint = (e) => {
      if (e.matches && isOpen) setDrawer(false);
    };
    if (mq.addEventListener) {
      mq.addEventListener("change", onBreakpoint);
    } else {
      mq.addListener(onBreakpoint);
    }
  }

  /* ----------------------------------------------------------------------
     Mark active nav link from body[data-page] or .is-active already in HTML
     ---------------------------------------------------------------------- */
  const page = document.body.dataset.page;
  if (page) {
    document
      .querySelectorAll(`[data-nav-link="${page}"]`)
      .forEach((el) => el.classList.add("is-active"));
  }
})();
