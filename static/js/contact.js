/**
 * Chalukya Tiles — contact.js
 * Client-side validation + Fetch submit for /api/contact and /api/enquiry.
 * Prefills product enquiry from ?product=&category= query params.
 */

(function () {
  "use strict";

  const EMAIL_RE = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;
  const PHONE_RE = /^[\d\s+\-().]{7,20}$/;

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function setError(input, message) {
    const group = input.closest(".form__group");
    const errorEl = group ? group.querySelector("[data-error]") : null;
    input.classList.toggle("is-invalid", Boolean(message));
    input.setAttribute("aria-invalid", message ? "true" : "false");
    if (errorEl) {
      errorEl.textContent = message || "";
    }
  }

  function clearErrors(form) {
    form.querySelectorAll(".form__control").forEach((el) => setError(el, ""));
  }

  function showStatus(el, type, message) {
    if (!el) return;
    el.classList.remove("is-visible", "form__status--success", "form__status--error");
    el.textContent = message;
    el.classList.add("is-visible");
    el.classList.add(
      type === "success" ? "form__status--success" : "form__status--error"
    );
    el.setAttribute("role", "alert");
  }

  function hideStatus(el) {
    if (!el) return;
    el.classList.remove("is-visible", "form__status--success", "form__status--error");
    el.textContent = "";
    el.removeAttribute("role");
  }

  function validateField(name, value) {
    const v = value.trim();

    if (name === "name") {
      if (v.length < 2) return "Please enter your full name (at least 2 characters).";
      if (v.length > 120) return "Name is too long.";
      return "";
    }

    if (name === "phone") {
      if (!PHONE_RE.test(v)) {
        return "Please enter a valid phone number.";
      }
      return "";
    }

    if (name === "email") {
      if (!EMAIL_RE.test(v)) {
        return "Please enter a valid email address.";
      }
      return "";
    }

    if (name === "message") {
      if (v.length < 10) {
        return "Please enter a message of at least 10 characters.";
      }
      if (v.length > 5000) return "Message is too long.";
      return "";
    }

    return "";
  }

  function validateForm(form) {
    const fields = ["name", "phone", "email", "message"];
    let firstInvalid = null;
    let ok = true;

    fields.forEach((name) => {
      const input = form.elements.namedItem(name);
      if (!input) return;
      const err = validateField(name, input.value || "");
      setError(input, err);
      if (err) {
        ok = false;
        if (!firstInvalid) firstInvalid = input;
      }
    });

    if (firstInvalid) firstInvalid.focus();
    return ok;
  }

  function getProductContext() {
    const params = new URLSearchParams(window.location.search);
    const product = (params.get("product") || "").trim();
    const category = (params.get("category") || "").trim();
    return {
      product_name: product || null,
      product_category: category || null,
      isEnquiry: Boolean(product || category),
    };
  }

  function applyEnquiryBanner(ctx) {
    const banner = qs("[data-enquiry-banner]");
    const productEl = qs("[data-enquiry-product]");
    const categoryEl = qs("[data-enquiry-category]");
    const titleEl = qs("[data-form-title]");
    const leadEl = qs("[data-form-lead]");

    if (!ctx.isEnquiry) {
      if (banner) banner.classList.remove("is-visible");
      return;
    }

    if (banner) banner.classList.add("is-visible");
    if (productEl) {
      productEl.textContent = ctx.product_name || "Selected product";
    }
    if (categoryEl) {
      if (ctx.product_category) {
        categoryEl.textContent = " · " + ctx.product_category;
        categoryEl.hidden = false;
      } else {
        categoryEl.textContent = "";
        categoryEl.hidden = true;
      }
    }
    if (titleEl) titleEl.textContent = "Product Enquiry";
    if (leadEl) {
      leadEl.textContent =
        "Tell us about your project and we will confirm availability and pricing.";
    }

    // Prefill message if empty
    const form = qs("[data-contact-form]");
    const message = form && form.elements.namedItem("message");
    if (message && !message.value.trim()) {
      const parts = [];
      if (ctx.product_name) parts.push(`Product: ${ctx.product_name}`);
      if (ctx.product_category) parts.push(`Category: ${ctx.product_category}`);
      parts.push("I would like more information and pricing.");
      message.value = parts.join("\n");
    }
  }

  function initContactForm() {
    const form = qs("[data-contact-form]");
    if (!form) return;

    const statusEl = qs("[data-form-status]", form) || qs("[data-form-status]");
    const submitBtn = form.querySelector('[type="submit"]');
    const ctx = getProductContext();
    applyEnquiryBanner(ctx);

    // Live validation on blur
    ["name", "phone", "email", "message"].forEach((name) => {
      const input = form.elements.namedItem(name);
      if (!input) return;
      input.addEventListener("blur", () => {
        setError(input, validateField(name, input.value || ""));
      });
      input.addEventListener("input", () => {
        if (input.classList.contains("is-invalid")) {
          setError(input, validateField(name, input.value || ""));
        }
      });
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideStatus(statusEl);
      clearErrors(form);

      if (!validateForm(form)) {
        showStatus(statusEl, "error", "Please correct the highlighted fields.");
        return;
      }

      const payload = {
        name: form.elements.namedItem("name").value.trim(),
        phone: form.elements.namedItem("phone").value.trim(),
        email: form.elements.namedItem("email").value.trim(),
        message: form.elements.namedItem("message").value.trim(),
      };

      if (ctx.isEnquiry) {
        if (ctx.product_name) payload.product_name = ctx.product_name;
        if (ctx.product_category) payload.product_category = ctx.product_category;
      }

      const api = window.ChalukyaAPI;
      if (!api) {
        showStatus(
          statusEl,
          "error",
          "Unable to send right now. Please call or WhatsApp us instead."
        );
        return;
      }

      if (submitBtn) {
        submitBtn.classList.add("is-loading");
        submitBtn.disabled = true;
        submitBtn.setAttribute("aria-busy", "true");
      }

      try {
        const result = ctx.isEnquiry
          ? await api.submitEnquiry(payload)
          : await api.submitContact(payload);

        if (result.ok && result.data && result.data.success !== false) {
          const msg =
            (result.data && result.data.message) ||
            "Thank you! Your message has been received.";
          showStatus(statusEl, "success", msg);
          form.reset();
          // Keep enquiry context banner after reset
          applyEnquiryBanner(ctx);
          // Clear message prefill after successful send
          const message = form.elements.namedItem("message");
          if (message) message.value = "";
          return;
        }

        // Validation errors from FastAPI
        if (result.status === 422 && api.parseValidationErrors) {
          const map = api.parseValidationErrors(result.data || {});
          Object.keys(map).forEach((field) => {
            const input = form.elements.namedItem(field);
            if (input) setError(input, map[field]);
          });
          showStatus(
            statusEl,
            "error",
            map._form || "Please check your details and try again."
          );
          return;
        }

        const detail =
          (result.data && (result.data.detail || result.data.message)) ||
          "Something went wrong. Please try again shortly.";
        showStatus(
          statusEl,
          "error",
          typeof detail === "string" ? detail : "Unable to send your message."
        );
      } catch (err) {
        showStatus(
          statusEl,
          "error",
          "Network error. Please check your connection or contact us by phone."
        );
      } finally {
        if (submitBtn) {
          submitBtn.classList.remove("is-loading");
          submitBtn.disabled = false;
          submitBtn.removeAttribute("aria-busy");
        }
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initContactForm);
  } else {
    initContactForm();
  }
})();
