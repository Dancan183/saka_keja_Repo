# Security Policy

## Reporting a problem

If you find a security issue, please **do not post it publicly**. Email: _security contact to be added_. Include what you found, how to reproduce it, and the affected page. We aim to reply within a few days and to fix serious issues first.

## What is protected today

**Accounts**
- Passwords are hashed by Django. The sign-up flow stores the hash, never the plain password, even while the registration is pending.
- An account is created only after both the phone and the email are verified.
- Unverified sign-ups live in a temporary record that expires after 30 minutes and is tied to the browser session by a token.

**Verification codes**
- Codes are stored only as HMAC-SHA256 hashes keyed by `SECRET_KEY`. The phone hash includes the phone number.
- Lifetimes: SMS code 5 minutes, email code 10 minutes. A phone verification stays valid for 60 minutes and can be used once.
- Limits: 60 seconds between sends, 5 attempts per code, 5 SMS codes per phone per hour, 10 per IP address per hour.
- A wrong guess is counted even when the request fails, so guesses cannot be repeated without limit.
- The SMS client logs only a masked number and a message id, never the code.

**Web**
- Django's CSRF protection is on. In production (`DEBUG=False`), CSRF and session cookies are Secure-only, and HTTPS is trusted through Vercel's forwarded header.
- Hosts are restricted to localhost and `.vercel.app` (add your own domain when you buy one).
- Secrets are read from environment variables, not from code.

**Content**
- Reviews are limited by database constraints: one per tenant-landlord pair, and only after an inquiry. Reports never hide a review automatically; only an admin can.
- Reviews about tenants are private.

## Known gaps

These are real and not yet fixed. Treat them as the to-do list.

1. **No login rate limiting or CAPTCHA.** Passwords can be guessed repeatedly. Add django-axes or similar.
2. **Admin is at the default `/admin/` with no two-factor sign-in.** Use a strong password, and consider moving the URL and adding 2FA.
3. **Registration reveals whether an email or username exists.** This allows account enumeration.
4. **No HSTS setting.** Add `SECURE_HSTS_SECONDS` once the domain is final and HTTPS is confirmed.
5. **The IP limit trusts `X-Forwarded-For`.** A client that can set this header may dodge the per-IP limit.
6. **Photos keep their EXIF data** (which may include GPS location) and are publicly readable in the bucket.
7. **Landlord phone numbers are public** on listings by design. Landlords should know this.
8. **Gmail SMTP is used for email.** Fine for testing; use a dedicated service for real traffic.
9. **Early Git history contains `db.sqlite3` and an old `SECRET_KEY`.** The old key must never be reused. If the repository is public or shared, rewrite the history or treat that data as exposed.
10. **No Terms or Privacy pages yet.**

## Secrets

Secrets: `SECRET_KEY`, database URLs, S3 keys, `AT_API_KEY`, `EMAIL_HOST_PASSWORD`, `ADMIN_PASSWORD`.

- Never paste them into chat, tickets or screenshots. A Gmail app password was shared in a chat during development: **revoke it and create a new one.**
- Rotate a secret by changing it in Vercel and redeploying.
- Effects of rotation:
  - **`SECRET_KEY`:** all sessions end, password-reset links stop working, and pending verification codes become invalid. Users must log in or start again.
  - **Database password:** the site fails until the new `DATABASE_URL` is deployed.
  - **S3 keys:** uploads fail until updated; existing photos keep loading.
  - **Email or SMS credentials:** codes stop sending until updated.

## If something goes wrong

1. **Contain:** rotate the affected secret, and deactivate suspicious accounts in `/admin/`.
2. **Check:** read Vercel Runtime Logs and the Neon dashboard for unusual activity.
3. **Recover:** restore from backup if data was changed (see MAINTENANCE.md).
4. **Tell people:** if personal data was exposed, tell affected users and consider reporting to the Office of the Data Protection Commissioner.
5. **Learn:** write down what happened and add the fix to this file.

## Personal data

The site holds names, phone numbers, email addresses, messages and reviews. Kenya's Data Protection Act, 2019 likely applies. Before charging users or going wide, publish a Privacy page, collect only what is needed, and consider registering with the Data Protection Commissioner. This is not legal advice; check with a lawyer.
