/*
 * Saka Keja auth pages: interface helpers only.
 * Validation and authentication stay on the server.
 *  - show/hide for every password box
 *  - a cosmetic strength meter on the first password box of a register form
 *  - a "please wait" state on the submit button
 */
(function () {
  "use strict";

  var form = document.querySelector(".auth-form");
  if (!form) { return; }

  // ----- show / hide password -----
  form.querySelectorAll('input[type="password"]').forEach(function (input) {
    var wrap = document.createElement("div");
    wrap.className = "pw-wrap";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pw-toggle";
    btn.setAttribute("aria-label", "Show password");
    btn.setAttribute("aria-pressed", "false");
    var EYE = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>';
    var EYE_OFF = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M17.9 17.9A10.9 10.9 0 0 1 12 19C5 19 1 12 1 12a18.5 18.5 0 0 1 5.1-5.9M9.9 5.1A10.4 10.4 0 0 1 12 5c7 0 11 7 11 7a18.6 18.6 0 0 1-2.2 3.2M1 1l22 22"/></svg>';
    btn.innerHTML = EYE;
    wrap.appendChild(btn);

    btn.addEventListener("click", function () {
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.setAttribute("aria-pressed", show ? "true" : "false");
      btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
      btn.innerHTML = show ? EYE_OFF : EYE;
    });
  });

  // ----- strength meter (register only) -----
  var first = document.getElementById("id_password1");
  if (first) {
    var meter = document.createElement("div");
    meter.className = "pw-meter";
    meter.setAttribute("data-level", "0");
    meter.innerHTML = "<span></span><span></span><span></span><span></span>";
    var label = document.createElement("p");
    label.className = "pw-meter-label";
    label.setAttribute("aria-live", "polite");
    var anchor = first.closest(".pw-wrap") || first;
    anchor.insertAdjacentElement("afterend", label);
    anchor.insertAdjacentElement("afterend", meter);

    var names = ["", "Weak", "Fair", "Good", "Strong"];
    first.addEventListener("input", function () {
      var v = first.value, score = 0;
      if (v.length >= 8) { score++; }
      if (v.length >= 12) { score++; }
      if (/[a-z]/.test(v) && /[A-Z]/.test(v)) { score++; }
      if (/\d/.test(v) && /[^A-Za-z0-9]/.test(v)) { score++; }
      if (!v) { score = 0; }
      meter.setAttribute("data-level", String(score));
      label.textContent = score ? "Password strength: " + names[score] : "";
    });
  }

  // ----- loading state -----
  var submit = form.querySelector('button[type="submit"]');
  if (submit) {
    var original = submit.textContent;
    form.addEventListener("submit", function (e) {
      if (submit.disabled || e.defaultPrevented) { return; }
      submit.classList.add("is-loading");
      submit.setAttribute("aria-busy", "true");
      submit.textContent = "Please wait...";
    });
    // Coming back with the browser's Back button
    window.addEventListener("pageshow", function (e) {
      if (e.persisted) {
        submit.classList.remove("is-loading");
        submit.removeAttribute("aria-busy");
        submit.textContent = original;
        submit.disabled = false;
      }
    });
  }

  // Mark fields that came back with errors, for assistive technology and styling.
  form.querySelectorAll(".field").forEach(function (field) {
    if (field.querySelector(".errorlist")) {
      var input = field.querySelector("input, select");
      if (input) { input.setAttribute("aria-invalid", "true"); }
    }
  });
})();