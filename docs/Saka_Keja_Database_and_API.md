# Saka Keja: Database Design and API Documentation

Version 1.0 · Written from the current code (Django 6.1)

## 0. Read this first

Saka Keja is a **server-rendered Django site**. It has **no REST API**. Almost every endpoint is an HTML page or a form post that redirects. Only **three endpoints return JSON**: the phone verification calls used by the registration page. Section 4 documents all of them honestly.

URL prefixes depend on `include()` lines in the project `urls.py`. This document writes paths as each app's own route (for example `houses/<id>/`). On your site the app prefix goes in front, such as `/properties/houses/1/` and `/accounts/login/`. Check your project `urls.py` for the exact `inquiries` and `reviews` prefixes.

---

## 1. Database overview

Production: Postgres on Neon. Local: SQLite. Eight application tables plus Django's own (sessions, admin log, permissions).

| App | Table (default Django name) | Purpose |
|---|---|---|
| accounts | `accounts_user` | Users, with a role |
| accounts | `accounts_pendingregistration` | Sign-ups waiting for the email code |
| accounts | `accounts_phoneverification` | SMS codes sent and their state |
| properties | `properties_location` | Areas used in search |
| properties | `properties_house` | Listings |
| properties | `properties_houseimage` | Listing photos |
| inquiries | `inquiries_inquiry` | A tenant's message about a house |
| reviews | `reviews_review` | Tenant and landlord reviews |
| reviews | `reviews_reviewreport` | Reports on reviews |

## 2. Relationships

```
Location 1 ──< House >── 1 User (landlord)
House    1 ──< HouseImage
House    1 ──< Inquiry >── 1 User (tenant)
User     1 ──< Review (reviewer)      User 1 ──< Review (reviewee)
Review   1 ──< ReviewReport >── 1 User (reporter)
Review   >── 0..1 House (context only)
PendingRegistration, PhoneVerification: standalone, linked to the visitor by a session token
```

Important points:

- An inquiry has **no landlord column**. The landlord is `inquiry.house.landlord`.
- A tenant and a landlord are "in touch" when an Inquiry exists with that tenant and a house of that landlord. This is what unlocks reviews.
- Deleting a user cascades to their houses, inquiries, reviews and reports. Deleting a house cascades to its images and inquiries. A review's `house` is set to null instead of deleting the review. A Location cannot be deleted while houses use it (`PROTECT`).

## 3. Table definitions

### accounts_user (extends Django `AbstractUser`)

Inherits `username` (unique), `email`, `password` (hash), `first_name`, `last_name`, `is_staff`, `is_active`, `is_superuser`, `date_joined`, `last_login`.

| Field | Type | Notes |
|---|---|---|
| role | varchar(20) | `tenant` (default) or `landlord` |
| phone_number | varchar(15) | blank allowed; stored as `+2547XXXXXXXX` at sign-up |

`AUTH_USER_MODEL = "accounts.User"`. Property `is_landlord` is true when role is landlord.

### accounts_pendingregistration

Holds a sign-up until the email code is entered. Nothing goes to `accounts_user` before that.

| Field | Type | Notes |
|---|---|---|
| token | varchar(64) | unique; also stored in the visitor's session |
| email | email | unique |
| username | varchar(150) | |
| password_hash | varchar(255) | already hashed |
| phone_number | varchar(15) | |
| role | varchar(20) | tenant or landlord |
| code_hash | varchar(64) | HMAC-SHA256 of the email code, never the code |
| attempts | smallint | wrong-code counter, max 5 |
| code_sent_at, created_at | datetime | pending lives 30 min, code 10 min |
| phone_token | varchar(64) | the phone verification this sign-up relies on |

### accounts_phoneverification

| Field | Type | Notes |
|---|---|---|
| token | varchar(64) | unique; kept in the session |
| phone | varchar(15) | `+2547XXXXXXXX` |
| code_hash | varchar(64) | hash covers the code and the phone number |
| attempts | smallint | max 5 |
| sent_ok | bool | the SMS provider accepted the message |
| ip_address | IP, null | used for the per-IP hourly limit |
| created_at | datetime | |
| verified_at | datetime, null | set when the code is correct (valid 60 min) |
| consumed_at | datetime, null | set when the account is created (single use) |

Indexes: (`phone`, `created_at`), (`ip_address`, `created_at`).

### properties_location

| Field | Type | Notes |
|---|---|---|
| name | varchar(100) | unique; ordered by name |

`build.py` seeds: Murang'a Town, Mjini, Mukuyu Market, Area 4 near small gate.

### properties_house

| Field | Type | Notes |
|---|---|---|
| landlord | FK → User | cascade; only users with role landlord |
| location | FK → Location | protect |
| title | varchar(150) | |
| description | text | optional |
| rent | positive int | monthly KSh, minimum 1 |
| bedrooms | positive smallint | default 1 |
| bathrooms | positive smallint | default 1 |
| house_type | varchar(20) | apartment, studio, bedsitter, bungalow, maisonette, other |
| status | varchar(10) | `vacant` (default) or `occupied` |
| created_at, updated_at | datetime | newest first |

Indexes: (`location`, `rent`, `bedrooms`) for search, and (`status`).

### properties_houseimage

| Field | Type | Notes |
|---|---|---|
| house | FK → House | cascade |
| image | file | uploaded to `houses/YYYY/MM/` (Supabase bucket in production) |
| uploaded_at | datetime | |

### inquiries_inquiry

| Field | Type | Notes |
|---|---|---|
| house | FK → House | cascade |
| tenant | FK → User | cascade |
| message | text | |
| phone_number | varchar(15) | optional; falls back to the tenant's profile phone |
| is_read | bool | landlord marks as read |
| created_at | datetime | newest first |

Computed: `contact_phone`, `whatsapp_number` (Kenyan 07xx converted to 2547xx for wa.me links).

### reviews_review

| Field | Type | Notes |
|---|---|---|
| reviewer | FK → User | cascade |
| reviewee | FK → User | cascade |
| rating | positive smallint | 1 to 5 |
| comment | text (max 500) | optional |
| house | FK → House, null | context only; set null on delete |
| is_visible | bool | admins untick to hide |
| created_at, updated_at | datetime | |

Constraints: unique (`reviewer`, `reviewee`) · rating between 1 and 5 · reviewer ≠ reviewee. Index: (`reviewee`, `is_visible`, `-created_at`).

Visibility rules (enforced in views): reviews about **landlords** are public; reviews about **tenants** are visible only to that tenant, the review's author and staff.

### reviews_reviewreport

| Field | Type | Notes |
|---|---|---|
| review | FK → Review | cascade |
| reporter | FK → User | cascade |
| reason | varchar(20) | fake, abusive, private, other |
| note | varchar(300) | optional |
| created_at | datetime | |

Constraint: one report per user per review. A report never hides a review.

---

## 4. Endpoints

### 4.1 Conventions

- **Auth levels:** *Public* (anyone), *Login* (any logged-in user), *Landlord* (logged in with role landlord; others get HTTP 403 "Only landlords can access this page."), *Staff* (admin site).
- **Not logged in** on a Login or Landlord page: redirect (302) to the login page with `?next=`.
- **State changes** use POST with Django's CSRF token (`csrfmiddlewaretoken` field, or `X-CSRFToken` header for the JSON calls). Pages marked *POST only* reject GET with HTTP 405.
- Session cookie authentication. There are no API keys or tokens.
- Page responses are HTML. Success after a POST is a 302 redirect plus a flash message.

### 4.2 accounts

| Method | Route | Auth | Purpose |
|---|---|---|---|
| GET, POST | `register/` | Public | Registration form |
| GET, POST | `login/` | Public | Login with **username** and password |
| POST | `logout/` | Login | Log out (POST only) |
| POST | `phone/send/` | Public | Send an SMS code (JSON) |
| POST | `phone/verify/` | Public | Check the SMS code (JSON) |
| POST | `phone/reset/` | Public | Discard the current phone verification (JSON) |
| GET, POST | `verify/` | Public (pending sign-up in session) | Enter the email code |
| POST | `verify/resend/` | Public (pending sign-up in session) | Send a new email code |
| GET, POST | `password-reset/` | Public | Ask for a reset email |
| GET | `password-reset/sent/` | Public | "Email sent" page |
| GET, POST | `password-reset/<uidb64>/<token>/` | Public (valid link) | Set a new password |
| GET | `password-reset/complete/` | Public | Done page |

**Register form fields:** `username`, `email`, `role`, `phone_number`, `password1`, `password2` (`tenant` or `landlord`). Email must not already exist. **Landlords** must give a valid Kenyan phone number and must already have verified it by SMS in this browser session. **Tenants** must also give a valid Kenyan phone number, but it is only format-checked and is stored unverified (no SMS). On success the visitor is sent to `verify/`.

**Email verify form field:** `code` (6 digits). Success creates the user, logs them in, and redirects landlords to the add-house page and tenants to the house list. Failures: wrong code (max 5), expired code (10 min), expired sign-up (30 min). Resend is allowed once per 60 seconds.

#### POST phone/send/

Request (JSON):

```json
{ "phone": "0712 345 678" }
```

Success `200`:

```json
{ "ok": true, "message": "Verification code sent successfully.", "cooldown": 60, "expires_in": 300 }
```

Errors return `{ "ok": false, "code": "...", "message": "..." }`:

| HTTP | code | Meaning |
|---|---|---|
| 400 | `empty` | No phone supplied |
| 400 | `invalid_phone` | Not a valid Kenyan number |
| 429 | `cooldown` | Wait; includes `retry_after` (seconds) |
| 429 | `phone_limit` | 5 codes per phone per hour reached |
| 429 | `ip_limit` | 10 codes per IP per hour reached |
| 502 | `send_failed` | SMS provider did not accept the message |

#### POST phone/verify/

Request (JSON):

```json
{ "code": "123456" }
```

Success `200`:

```json
{ "ok": true, "message": "Phone number verified successfully.", "phone": "+254712345678" }
```

Errors:

| HTTP | code | Meaning |
|---|---|---|
| 400 | `bad_format` | Not six digits |
| 400 | `no_code` | No code was requested in this session |
| 400 | `expired` | Code older than 5 minutes |
| 400 | `wrong_code` | Wrong; includes `attempts_left` |
| 429 | `locked` | 5 wrong attempts; request a new code |

#### POST phone/reset/

No body. Returns `200 {"ok": true}`. Deletes the unconsumed verification tied to this session.

### 4.3 properties

| Method | Route | Auth | Purpose |
|---|---|---|---|
| GET | `home/` | Public | Landing page |
| GET | `` (empty) | Public | Search and list vacant houses |
| GET | `houses/<id>/` | Public | House detail |
| GET | `my-houses/` | Landlord | Landlord's own listings |
| GET, POST | `houses/add/` | Landlord | Create a house |
| GET, POST | `houses/<id>/edit/` | Landlord (owner) | Edit a house |
| POST | `houses/<id>/delete/` | Landlord (owner) | Delete a house |
| POST | `houses/<id>/status/` | Landlord (owner) | Flip vacant ↔ occupied |
| GET, POST | `houses/<id>/images/add/` | Landlord (owner) | Upload a photo (`image` file, multipart) |
| POST | `images/<id>/delete/` | Landlord (owner) | Delete a photo |

**Search (GET `/`) query parameters**, all optional:

| Parameter | Meaning |
|---|---|
| `location` | Location id |
| `min_rent`, `max_rent` | Rent bounds in KSh (min must not exceed max) |
| `price_range` | `"5000-10000"`, converted to the two above when they are absent |
| `bedrooms` | **Exact** match |
| `bathrooms` | **At least** this many |
| `house_type` | One of the type values |
| `page` | Page number; 12 results per page |

Only houses with status `vacant` are listed. Invalid filters are ignored and the full list is shown.

**House form fields:** `title`, `location`, `rent`, `bedrooms`, `bathrooms`, `house_type`, `status`, `description`. The landlord is set from the logged-in user. A landlord who is not the owner gets 404 on edit, delete, status and image routes.

### 4.4 inquiries

| Method | Route | Auth | Purpose |
|---|---|---|---|
| GET, POST | `send/<house_id>/` | Login (tenant) | Send an inquiry |
| GET | `sent/` | Login | Inquiries I sent |
| GET | `inbox/` | Landlord | Inquiries about my houses, with unread count |
| POST | `<id>/read/` | Landlord (owner of the house) | Mark an inquiry as read |

**Send form fields:** `message` (required), `phone_number` (optional). Refused with a flash message and a redirect to the house if the sender is a landlord or the house is occupied. Success redirects to `sent/`.

### 4.5 reviews

| Method | Route | Auth | Purpose |
|---|---|---|---|
| GET | `mine/` | Login | Reviews about me, reviews I wrote, people I can still review |
| GET | `landlord/<user_id>/` | Public | A landlord's public profile and reviews |
| GET | `tenant/<user_id>/` | Login (tenant themself, the author, or staff) | A tenant's private reviews |
| GET, POST | `write/<user_id>/` | Login | Write or edit my review of that person |
| POST | `<id>/delete/` | Login (author) | Delete my review |
| POST | `<id>/report/` | Login | Report a visible review |

**Review form fields:** `rating` (1 to 5, required), `comment` (up to 500 characters). Allowed only when a tenant and landlord have an inquiry between them, and never for yourself. One review per pair: posting again edits it.

**Report form fields:** `reason` (`fake`, `abusive`, `private`, `other`), `note` (optional, 300). You cannot report your own review. A repeat report returns "You already reported this review."

### 4.6 Admin site

`/admin/` (Django admin). Staff only. Manage users, locations, houses, inquiries, reviews (untick **Is visible** to hide) and review reports.

## 5. Common responses

| Code | When |
|---|---|
| 200 | Page rendered, or JSON success |
| 302 | Redirect after a successful POST, or to login |
| 400 | JSON endpoint validation error |
| 403 | Logged in but not allowed (landlord-only pages), or CSRF failure |
| 404 | Object not found, or not yours |
| 405 | Wrong method (for example GET on a POST-only route) |
| 429 | JSON endpoint rate limit |
| 502 | SMS provider failure |

## 6. Gaps and notes

- There is no JSON API for houses, inquiries or reviews. A mobile app would need a Django REST Framework layer (or similar) added first.
- Login has no rate limit yet (see SECURITY.md).
- Uploads over about 4.5 MB fail on Vercel.
- Check each prefix against your project `urls.py` before publishing these paths.