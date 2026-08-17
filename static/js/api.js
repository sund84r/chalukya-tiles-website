/**
 * Chalukya Tiles — api.js
 * Shared Fetch helpers for contact / enquiry endpoints.
 * Used by contact.js and product enquiry forms.
 */

(function (global) {
  "use strict";

  const DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  /**
   * POST JSON to an API path.
   * @param {string} url
   * @param {Record<string, unknown>} data
   * @returns {Promise<{ ok: boolean, status: number, data: object }>}
   */
  async function postJSON(url, data) {
    const response = await fetch(url, {
      method: "POST",
      headers: DEFAULT_HEADERS,
      body: JSON.stringify(data),
    });

    let payload = {};
    const contentType = response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
      try {
        payload = await response.json();
      } catch {
        payload = {};
      }
    }

    return {
      ok: response.ok,
      status: response.status,
      data: payload,
    };
  }

  /**
   * Submit general contact form.
   * @param {{ name: string, phone: string, email: string, message: string }} fields
   */
  function submitContact(fields) {
    return postJSON("/api/contact", fields);
  }

  /**
   * Submit product / showroom enquiry.
   * @param {{
   *   name: string,
   *   phone: string,
   *   email: string,
   *   message: string,
   *   product_name?: string,
   *   product_category?: string
   * }} fields
   */
  function submitEnquiry(fields) {
    return postJSON("/api/enquiry", fields);
  }

  /**
   * Submit customer review / rating.
   * @param {{ name: string, message: string, rating?: number, email?: string, phone?: string, title?: string }} fields
   */
  function submitReview(fields) {
    return postJSON("/api/review", fields);
  }

  /**
   * Map FastAPI 422 validation errors into a flat field → message object.
   * @param {object} data
   * @returns {Record<string, string>}
   */
  function parseValidationErrors(data) {
    const map = {};
    const detail = data && data.detail;

    if (Array.isArray(detail)) {
      detail.forEach((item) => {
        const loc = item.loc || [];
        const field = loc[loc.length - 1];
        if (typeof field === "string" && field !== "body") {
          map[field] = item.msg || "Invalid value";
        }
      });
    } else if (typeof detail === "string") {
      map._form = detail;
    }

    return map;
  }

  global.ChalukyaAPI = {
    postJSON,
    submitContact,
    submitEnquiry,
    submitReview,
    parseValidationErrors,
  };
})(window);
