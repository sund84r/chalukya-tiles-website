/**
 * Chalukya Tiles — slider.js
 * Reviews carousel. Transform is applied to the track;
 * overflow:hidden stays on the outer viewport.
 */

(function () {
  "use strict";

  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  function initSlider(root) {
    const track = root.querySelector("[data-slider-track]");
    const slides = Array.from(root.querySelectorAll("[data-slider-slide]"));
    if (!track || slides.length < 2) return;

    const prevBtn = root.querySelector("[data-slider-prev]");
    const nextBtn = root.querySelector("[data-slider-next]");
    const dotsRoot = root.querySelector("[data-slider-dots]");
    const autoplay = root.dataset.autoplay !== "false";
    const intervalMs = Number(root.dataset.interval || 6000);

    let index = 0;
    let timer = null;
    let touchStartX = 0;
    let touchDeltaX = 0;
    let isDragging = false;

    /* Layout: viewport clips; track is a horizontal row of full-width slides */
    const viewport = root.querySelector(".reviews-slider__viewport") || root;
    viewport.style.overflow = "hidden";
    track.style.display = "flex";
    track.style.flexDirection = "row";
    track.style.flexWrap = "nowrap";
    track.style.willChange = "transform";
    track.style.margin = "0";
    track.style.padding = "0";

    function layoutSlides() {
      // Visible width of the clip container (not the expanded track)
      const w = Math.max(viewport.clientWidth || root.clientWidth, 1);
      track.style.width = w * slides.length + "px";
      slides.forEach(function (slide) {
        slide.style.flex = "0 0 " + w + "px";
        slide.style.flexShrink = "0";
        slide.style.width = w + "px";
        slide.style.minWidth = w + "px";
        slide.style.maxWidth = w + "px";
        slide.style.boxSizing = "border-box";
      });
    }

    /* Dots */
    const dots = [];
    if (dotsRoot) {
      dotsRoot.innerHTML = "";
      slides.forEach((_, i) => {
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = "reviews-slider__dot";
        dot.setAttribute("aria-label", "Go to slide " + (i + 1));
        dot.addEventListener("click", () => goTo(i, true));
        dotsRoot.appendChild(dot);
        dots.push(dot);
      });
    }

    function update(animate) {
      layoutSlides();
      const w = Math.max(viewport.clientWidth || root.clientWidth, 1);
      // Pixel translate — % of the multi-slide track jumps too far
      track.style.transition =
        animate === false || prefersReducedMotion
          ? "none"
          : "transform 0.55s cubic-bezier(0.22, 1, 0.36, 1)";
      track.style.transform = "translate3d(-" + index * w + "px, 0, 0)";

      slides.forEach((slide, i) => {
        const active = i === index;
        slide.setAttribute("aria-hidden", active ? "false" : "true");
        if (active) slide.removeAttribute("tabindex");
        else slide.setAttribute("tabindex", "-1");
      });

      dots.forEach((dot, i) => {
        dot.classList.toggle("is-active", i === index);
        dot.setAttribute("aria-current", i === index ? "true" : "false");
      });
    }

    function goTo(nextIndex, userAction) {
      index = ((nextIndex % slides.length) + slides.length) % slides.length;
      update(true);
      if (userAction) restartAutoplay();
    }

    function next(userAction) {
      goTo(index + 1, userAction);
    }

    function prev(userAction) {
      goTo(index - 1, userAction);
    }

    function startAutoplay() {
      stopAutoplay();
      if (!autoplay || prefersReducedMotion || slides.length < 2) return;
      timer = window.setInterval(function () {
        next(false);
      }, intervalMs);
    }

    function stopAutoplay() {
      if (timer) {
        window.clearInterval(timer);
        timer = null;
      }
    }

    function restartAutoplay() {
      stopAutoplay();
      startAutoplay();
    }

    if (prevBtn) prevBtn.addEventListener("click", function () { prev(true); });
    if (nextBtn) nextBtn.addEventListener("click", function () { next(true); });

    root.addEventListener("mouseenter", stopAutoplay);
    root.addEventListener("mouseleave", startAutoplay);
    root.addEventListener("focusin", stopAutoplay);
    root.addEventListener("focusout", function (event) {
      if (!root.contains(event.relatedTarget)) startAutoplay();
    });

    /* Pointer / touch swipe on the whole slider shell */
    function onPointerDown(clientX) {
      isDragging = true;
      touchStartX = clientX;
      touchDeltaX = 0;
      stopAutoplay();
      track.style.transition = "none";
    }

    function onPointerMove(clientX) {
      if (!isDragging) return;
      touchDeltaX = clientX - touchStartX;
      var width = Math.max(viewport.clientWidth || root.clientWidth, 1);
      track.style.transition = "none";
      track.style.transform =
        "translate3d(" + (-index * width + touchDeltaX) + "px, 0, 0)";
    }

    function onPointerUp() {
      if (!isDragging) return;
      isDragging = false;
      if (Math.abs(touchDeltaX) > 40) {
        if (touchDeltaX < 0) next(true);
        else prev(true);
      } else {
        update(true);
        startAutoplay();
      }
      touchDeltaX = 0;
    }

    track.addEventListener(
      "touchstart",
      function (e) {
        onPointerDown(e.changedTouches[0].clientX);
      },
      { passive: true }
    );
    track.addEventListener(
      "touchmove",
      function (e) {
        onPointerMove(e.changedTouches[0].clientX);
      },
      { passive: true }
    );
    track.addEventListener("touchend", onPointerUp, { passive: true });

    root.addEventListener("keydown", function (event) {
      if (event.key === "ArrowRight") {
        event.preventDefault();
        next(true);
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        prev(true);
      }
    });

    root.setAttribute("tabindex", "0");
    root.setAttribute("role", "region");
    if (!root.getAttribute("aria-roledescription")) {
      root.setAttribute("aria-roledescription", "carousel");
    }
    root.setAttribute("aria-label", root.getAttribute("aria-label") || "Reviews");

    window.addEventListener("resize", function () {
      update(false);
    });

    update(false);
    startAutoplay();

    document.addEventListener("visibilitychange", function () {
      if (document.hidden) stopAutoplay();
      else startAutoplay();
    });
  }

  function boot() {
    document.querySelectorAll("[data-slider]").forEach(initSlider);
  }

  function initHeroVideo() {
    const hero = document.querySelector("[data-hero]");
    const video = document.querySelector("[data-hero-video]");
    if (!hero || !video) return;

    const tryPlay = function () {
      const playPromise = video.play();
      if (playPromise && typeof playPromise.then === "function") {
        playPromise
          .then(function () {
            hero.classList.add("is-video-ready");
          })
          .catch(function () {});
      } else {
        hero.classList.add("is-video-ready");
      }
    };

    if (video.readyState >= 2) tryPlay();
    else {
      video.addEventListener("loadeddata", tryPlay, { once: true });
      video.addEventListener(
        "canplay",
        function () {
          hero.classList.add("is-video-ready");
        },
        { once: true }
      );
    }

    if (video.dataset.src && !video.getAttribute("src")) {
      video.src = video.dataset.src;
      video.load();
    }
  }

  function start() {
    boot();
    initHeroVideo();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
