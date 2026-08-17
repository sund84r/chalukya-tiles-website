/**
 * Chalukya Tiles — public review / rating modal
 * Opens from [data-review-open] pen FAB, submits POST /api/review.
 */
(function () {
  "use strict";

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function qsa(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function init() {
    const modal = qs("[data-review-modal]");
    const form = qs("[data-review-form]");
    if (!modal || !form) return;

    const statusEl = qs("[data-review-status]", form);
    let lastFocus = null;

    function setStatus(type, message) {
      if (!statusEl) return;
      statusEl.hidden = !message;
      statusEl.textContent = message || "";
      statusEl.classList.remove("is-success", "is-error");
      if (type === "success") statusEl.classList.add("is-success");
      if (type === "error") statusEl.classList.add("is-error");
    }

    function openModal() {
      lastFocus = document.activeElement;
      modal.hidden = false;
      document.body.classList.add("review-modal-open");
      setStatus("", "");
      const first = form.querySelector("input, select, textarea");
      if (first) {
        window.setTimeout(() => first.focus(), 40);
      }
    }

    function closeModal() {
      modal.hidden = true;
      document.body.classList.remove("review-modal-open");
      setStatus("", "");
      if (lastFocus && typeof lastFocus.focus === "function") {
        lastFocus.focus();
      }
    }

    qsa("[data-review-open]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        openModal();
      });
    });

    qsa("[data-review-close]", modal).forEach((el) => {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        closeModal();
      });
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !modal.hidden) {
        closeModal();
      }
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      setStatus("", "");

      const fd = new FormData(form);
      const name = String(fd.get("name") || "").trim();
      const message = String(fd.get("message") || "").trim();
      const rating = Number(fd.get("rating") || 5);
      const email = String(fd.get("email") || "").trim();
      const phone = String(fd.get("phone") || "").trim();
      const title = String(fd.get("title") || "").trim();

      if (name.length < 2) {
        setStatus("error", "Please enter your name (at least 2 characters).");
        return;
      }
      if (message.length < 10) {
        setStatus("error", "Please write at least 10 characters of feedback.");
        return;
      }
      if (rating < 1 || rating > 5) {
        setStatus("error", "Please choose a rating from 1 to 5.");
        return;
      }

      const payload = {
        name,
        message,
        rating,
        email: email || null,
        phone: phone || null,
        title: title || null,
      };

      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Submitting…";
      }

      try {
        let result;
        if (window.ChalukyaAPI && typeof window.ChalukyaAPI.postJSON === "function") {
          result = await window.ChalukyaAPI.postJSON("/api/review", payload);
        } else {
          const res = await fetch("/api/review", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Accept: "application/json",
            },
            body: JSON.stringify(payload),
          });
          let data = {};
          try {
            data = await res.json();
          } catch (_) {
            data = {};
          }
          result = { ok: res.ok, status: res.status, data };
        }

        if (!result.ok) {
          const detail = result.data && (result.data.detail || result.data.message);
          let msg = "Unable to submit review. Please try again.";
          if (typeof detail === "string") msg = detail;
          else if (Array.isArray(detail) && detail[0] && detail[0].msg) {
            msg = detail.map((d) => d.msg).join(" ");
          }
          setStatus("error", msg);
          return;
        }

        form.reset();
        const ratingSelect = form.querySelector('[name="rating"]');
        if (ratingSelect) ratingSelect.value = "5";
        setStatus(
          "success",
          (result.data && result.data.message) ||
            "Thank you! Your review will appear after admin approval."
        );
        window.setTimeout(() => closeModal(), 2200);
      } catch (_) {
        setStatus("error", "Network error. Please check your connection and try again.");
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Submit review";
        }
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
