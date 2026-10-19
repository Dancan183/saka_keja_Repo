/*
 * Phone verification on the registration page.
 * The server is the authority: this script only drives the interface.
 * It never sees or stores the real code except what the user types.
 */
(function () {
  "use strict";

  var block = document.getElementById("phone-block");
  if (!block) { return; }

  var phoneInput = document.getElementById("id_phone_number");
  var confirmBtn = document.getElementById("phone-confirm");
  var codeInput = document.getElementById("id_phone_code");
  var verifyBtn = document.getElementById("phone-verify");
  var statusEl = document.getElementById("phone-status");
  var badge = document.getElementById("phone-badge");
  var submitBtn = document.getElementById("register-submit");
  var csrf = document.querySelector("#register-form [name=csrfmiddlewaretoken]");
  var roleSelect = document.getElementById("id_role");
  var phoneLabel = document.getElementById("phone-label");
  var codeRow = block.querySelector(".phone-code-row");
  var codeLabel = block.querySelector(".phone-code-label");
  var phoneRow = block.querySelector(".phone-row");

  // Only landlords verify their phone by SMS. Tenants verify their email only.
  function needsPhoneCheck() {
    return !roleSelect || roleSelect.value === "landlord";
  }

  var urls = {
    send: block.dataset.sendUrl,
    verify: block.dataset.verifyUrl,
    reset: block.dataset.resetUrl
  };

  var state = "idle";          // idle -> sent -> verified
  var activePhone = null;      // normalized number the current code/verification belongs to
  var cooldownTimer = null;

  // Same rule as the server: Kenyan mobile numbers (07xx / 01xx).
  function normalize(raw) {
    var s = (raw || "").replace(/[\s\-().]/g, "");
    var m = /^(?:\+?254|0)?([17]\d{8})$/.exec(s);
    return m ? "+254" + m[1] : null;
  }

  function setStatus(text, kind) {
    statusEl.textContent = text || "";
    statusEl.className = "phone-status" + (kind ? " " + kind : "");
  }

  function post(url, body) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf ? csrf.value : "" },
      body: JSON.stringify(body || {})
    }).then(function (res) {
      return res.json().catch(function () { return { ok: false }; }).then(function (data) {
        data.httpStatus = res.status;
        return data;
      });
    });
  }

  function lockCode() {
    codeInput.value = "";
    codeInput.disabled = true;
    verifyBtn.disabled = true;
  }

  function stopCooldown() {
    if (cooldownTimer) { clearInterval(cooldownTimer); cooldownTimer = null; }
  }

  function setConfirmLabel(text, disabled) {
    confirmBtn.textContent = text;
    confirmBtn.disabled = !!disabled;
  }

  function startCooldown(seconds) {
    stopCooldown();
    var left = seconds;
    setConfirmLabel("Resend code (" + left + "s)", true);
    cooldownTimer = setInterval(function () {
      left -= 1;
      if (left <= 0) {
        stopCooldown();
        setConfirmLabel(state === "idle" ? "Confirm Phone Number" : "Resend code", false);
      } else {
        setConfirmLabel("Resend code (" + left + "s)", true);
      }
    }, 1000);
  }

  function showVerified() {
    state = "verified";
    block.classList.add("is-verified");
    badge.hidden = false;
    lockCode();
    stopCooldown();
    setConfirmLabel("Verified", true);
    submitBtn.disabled = false;
  }

  // Back to the starting point: no code, no verified state.
  function resetUi(message) {
    state = "idle";
    activePhone = null;
    block.classList.remove("is-verified");
    badge.hidden = true;
    lockCode();
    submitBtn.disabled = needsPhoneCheck();
    if (!cooldownTimer) { setConfirmLabel("Confirm Phone Number", false); }
    setStatus(message || "", message ? "error" : "");
  }

  // ----- Confirm Phone Number / Resend -----
  confirmBtn.addEventListener("click", function () {
    var raw = phoneInput.value.trim();
    if (!raw) {
      setStatus("Enter your phone number first.", "error");
      phoneInput.focus();
      return;
    }
    var phone = normalize(raw);
    if (!phone) {
      setStatus("Enter a valid Kenyan phone number, for example 0712 345 678.", "error");
      phoneInput.focus();
      return;
    }

    confirmBtn.disabled = true;
    setStatus("Sending code...", "");

    post(urls.send, { phone: raw }).then(function (data) {
      if (data.ok) {
        state = "sent";
        activePhone = phone;
        block.classList.remove("is-verified");
        badge.hidden = true;
        submitBtn.disabled = needsPhoneCheck();
        codeInput.value = "";
        codeInput.disabled = false;
        verifyBtn.disabled = false;
        codeInput.focus();
        setStatus("Verification code sent successfully.", "ok");
        startCooldown(data.cooldown || 60);
      } else if (data.httpStatus === 429 && data.retry_after) {
        setStatus(data.message, "error");
        startCooldown(data.retry_after);
      } else {
        setStatus(data.message || "Failed to send code. Please try again.", "error");
        if (!cooldownTimer) { setConfirmLabel(state === "idle" ? "Confirm Phone Number" : "Resend code", false); }
        else { confirmBtn.disabled = true; }
      }
    }).catch(function () {
      setStatus("Failed to send code. Please try again.", "error");
      confirmBtn.disabled = false;
    });
  });

  // ----- Verify Code -----
  function verify() {
    if (verifyBtn.disabled) { return; }
    var code = codeInput.value.trim();
    if (!/^\d{6}$/.test(code)) {
      setStatus("Enter the 6-digit code.", "error");
      codeInput.focus();
      return;
    }
    verifyBtn.disabled = true;
    setStatus("Checking code...", "");

    post(urls.verify, { code: code }).then(function (data) {
      if (data.ok) {
        showVerified();
        setStatus("Phone number verified successfully.", "ok");
        return;
      }
      setStatus(data.message || "That code is not correct.", "error");
      if (data.code === "expired" || data.code === "locked" || data.code === "no_code") {
        lockCode();                       // a new code is needed
        if (!cooldownTimer) { setConfirmLabel("Resend code", false); }
      } else {
        verifyBtn.disabled = false;
        codeInput.focus();
        codeInput.select();
      }
    }).catch(function () {
      setStatus("Could not check the code. Please try again.", "error");
      verifyBtn.disabled = false;
    });
  }
  verifyBtn.addEventListener("click", verify);
  codeInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") { event.preventDefault(); verify(); }
  });
  codeInput.addEventListener("input", function () {
    codeInput.value = codeInput.value.replace(/\D/g, "").slice(0, 6);
  });

  // ----- Phone number edited: throw away the code / verified state -----
  phoneInput.addEventListener("input", function () {
    if (!needsPhoneCheck()) {
      if (!statusEl.hidden) { statusEl.hidden = true; setStatus("", ""); }
      return;
    }
    if (state === "idle") {
      setStatus("", "");
      return;
    }
    var now = normalize(phoneInput.value);
    if (now !== activePhone) {
      post(urls.reset, {});             // tell the server to forget it as well
      resetUi("Phone number changed. Please request a new code.");
    }
  });

  // Enter inside the phone box should not submit the form by accident.
  phoneInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && needsPhoneCheck()) { event.preventDefault(); confirmBtn.click(); }
  });

  // ----- Role: show the SMS check for landlords, hide it for tenants -----
  function applyRole() {
    var landlord = needsPhoneCheck();
    confirmBtn.hidden = !landlord;
    codeRow.hidden = !landlord;
    codeLabel.hidden = !landlord;
    statusEl.hidden = !landlord;
    badge.hidden = !landlord || state !== "verified";
    if (phoneLabel) { phoneLabel.textContent = "Phone number"; }
    phoneRow.classList.toggle("no-button", !landlord);
    if (landlord) {
      submitBtn.disabled = state !== "verified";
    } else {
      submitBtn.disabled = false;       // email verification is enough for tenants
      setStatus("", "");
    }
  }
  if (roleSelect) { roleSelect.addEventListener("change", applyRole); }

  // Tenants are not sent a code, but their number must still be a real Kenyan number (no garbage).
  document.getElementById("register-form").addEventListener("submit", function (event) {
    if (needsPhoneCheck()) { return; }
    if (!normalize(phoneInput.value)) {
      event.preventDefault();
      statusEl.hidden = false;
      setStatus("Enter a valid Kenyan phone number, for example 0712 345 678.", "error");
      phoneInput.focus();
    }
  });

  // ----- Starting state -----
  if (block.dataset.verified === "true" && normalize(phoneInput.value)) {
    activePhone = normalize(phoneInput.value);
    showVerified();
    setStatus("Phone number verified successfully.", "ok");
  } else {
    lockCode();
    submitBtn.disabled = true;     // the server also rejects an unverified landlord number
    setConfirmLabel("Confirm Phone Number", false);
  }
  applyRole();
})();