# Software Design Document (SDD)

**Saka Keja**

This document describes the overall architecture, technology stack, folder structure, data flow and key design decisions for the Saka Keja web application.

Version 1.0 | October 2026 | Author: [your name]

---

## 1. High-level architecture

### 1.1 Architectural style

Saka Keja is a **modular monolith**: one Django project split into four apps, rendering HTML on the server. There is no separate front-end application and no public API. A small amount of plain JavaScript is used only where a page must react without reloading (phone verification). In production the project runs as a serverless Python function on Vercel, which handles each request through Django's WSGI interface.

### 1.2 System diagram

```
                      +------------------------------------------+      +--------------------+
                      | Vercel: Django, one function per request | ---> | Neon PostgreSQL    |
                      |                                          |      | database           |
                      |                                          |      +--------------------+
                      | accounts       properties                |
                      | inquiries      reviews                   |      +--------------------+
                      |                                          | ---> | Supabase Storage   |
                      |                                          |      | house photos       |
+-----------+ HTTPS   | shared: templates, sessions, CSRF        |      +--------------------+
|  Browser  | ------> |                                          |
| phone/PC  | <------ |                                          |      +--------------------+
+-----------+         |                                          | ---> | Email (SMTP)       |
                      |                                          |      | codes, reset links |
                      |                                          |      +--------------------+
                      |                                          |
                      |                                          |      +--------------------+
                      |                                          | ---> | Africa's Talking   |
                      |                                          |      | SMS codes          |
                      +------------------------------------------+      +--------------------+
```

The browser also loads house photos straight from the storage bucket, and static files from the Vercel CDN, so those requests do not pass through Django. A push to GitHub starts a Vercel build that runs the database migrations.

### 1.3 Components

| Component | Role |
|---|---|
| Browser (phone or desktop) | Shows the pages and runs the small phone verification script |
| Vercel | Hosts Django as a serverless function and serves static files from its CDN |
| Neon PostgreSQL | Production database |
| Supabase Storage | House photos (S3-compatible, public bucket) |
| SMTP email service | Verification codes and password reset links |
| Africa's Talking | SMS verification codes |
| GitHub | Source code; a push triggers a Vercel build |

### 1.4 Request path

1. The browser requests a page over HTTPS.
2. Vercel starts or reuses a Python function running Django.
3. Django middleware handles security, sessions, CSRF protection and the logged-in user.
4. The URL router sends the request to a view in one of the apps.
5. The view uses forms, helper modules and models. The models read and write Neon through the ORM.
6. The view renders a template and returns HTML.

### 1.5 Layers

| Layer | Contents |
|---|---|
| Presentation | Django templates, one shared base template holding the CSS, one JavaScript file |
| Controllers | Views and URL routes in each app |
| Business logic | `otp.py`, `phone.py`, `sms.py` (accounts) and `services.py` (reviews) |
| Data | Models, the ORM, database constraints and migrations |
| Integration | Email (`send_mail`), the SMS client, photo storage (`django-storages`) |

### 1.6 Application modules

| Module | Responsibility |
|---|---|
| `Saka_Keja` (project) | Settings, root URLs, WSGI entry point |
| `accounts` | User model, registration, phone and email verification, login, logout, password reset |
| `properties` | Locations, houses, photos, search, landlord dashboard, landing page, base template |
| `inquiries` | Tenant messages to landlords, landlord inbox, unread count |
| `reviews` | Reviews, reports, ratings, and the rules for who may review whom |

---

## 2. Technology Stack

| Area | Technology |
|---|---|
| Language | Python (3.12 on Vercel) |
| Framework | Django 6.1 |
| Database | PostgreSQL on Neon (psycopg 3); SQLite for local development |
| Photo storage | Supabase Storage through `django-storages` and `boto3` |
| Images | Pillow |
| Configuration | Environment variables; `python-dotenv` reads a local `.env` file |
| Front end | Django templates, plain CSS with variables, vanilla JavaScript, Font Awesome 6 icons |
| Email | Django mail over SMTP (Gmail for now; a dedicated service is recommended for real traffic) |
| SMS | Africa's Talking REST API (sandbox until a live app is set up) |
| Hosting and build | Vercel, with the build step defined in `vercel.json` and `build.py` |
| Source control | Git and GitHub |
| Testing | Django test runner; Playwright for browser checks |

Python packages are listed in `requirements.txt`.

---

## 3. Folder structure

```
Saka_Keja/                     project root (manage.py lives here)
  manage.py
  requirements.txt             Python packages
  vercel.json                  tells Vercel to run build.py
  build.py                     migrations, locations and admin account on each deploy
  .env                         local secrets, never committed
  Saka_Keja/                   project package
    settings.py  urls.py  wsgi.py
  accounts/
    models.py                  User, PendingRegistration, PhoneVerification
    forms.py  views.py  urls.py  admin.py  tests.py
    otp.py                     email code logic and account creation
    phone.py                   phone number rules and SMS code logic
    sms.py                     SMS backends (Africa's Talking, console, test)
    static/accounts/phone_verify.js
    templates/accounts/        register, verify, login, password reset pages
  properties/
    models.py                  Location, House, HouseImage
    forms.py  views.py  urls.py
    templates/properties/      base.html, home.html, search and house pages
  inquiries/
    models.py                  Inquiry
    forms.py  views.py  urls.py  context_processors.py
    templates/inquiries/       inquiry form, tenant list, landlord inbox
  reviews/
    models.py                  Review, ReviewReport
    services.py                eligibility rules and rating statistics
    forms.py  views.py  urls.py  admin.py  tests.py
    templatetags/review_extras.py
    templates/reviews/         profiles, review form, my reviews
```

Each app owns its models, views, URLs, templates and tests. The shared page structure (navigation, top bar, footer, styles) lives in `properties/templates/properties/base.html`, which every other template extends.

---

## 4. Data flow

### 4.1 Registration with two verifications

1. The visitor opens the register page and types a phone number.
2. **Confirm Phone Number** sends it to the server. The server normalises it to `+254` format, checks the send limits, creates a random 6-digit code, stores only a keyed hash that includes the number, sends the SMS, and remembers a random token in the visitor's session.
3. The page unlocks the code field. The visitor types the code and the server compares hashes, checking expiry and attempts.
4. The visitor fills in the rest of the form. On submit the server checks that this browser verified exactly this number, saves a pending record (password already hashed) and emails a 6-digit code.
5. The visitor enters the email code. The server checks it the same way.
6. In one transaction the server checks the phone verification again, marks it used, creates the real user and deletes the pending record.
7. The user is logged in and sent to Add a house (landlords) or search (tenants).

If the phone number is edited at any point, the browser clears the code and tells the server to forget the verification.

### 4.2 Search

A GET request carries the filters. The view starts from vacant houses only, applies each filter given (area, type, rent range, bedrooms, bathrooms), pages the results 12 at a time and renders the cards.

### 4.3 Inquiry

A logged-in tenant opens a vacant house and submits the inquiry form. The view saves it. The landlord's navigation shows an unread count, and the inbox lists the messages with call, WhatsApp and email buttons.

### 4.4 Reviews

The server first checks that an inquiry exists between the two users and that one is a tenant and the other a landlord. A review is stored once per pair. Averages are calculated when a page is shown, from visible reviews only. Reviews about tenants are shown only to the tenant, staff and landlords the tenant has contacted.

### 4.5 Photo upload

The browser posts the image to Django, which hands it to the storage layer. The storage layer writes it to the Supabase bucket, and the page later shows it from the bucket's public address. The host rejects requests above about 4.5 MB, so large phone photos currently fail.

### 4.6 Build and deploy

1. A push to GitHub starts a Vercel build.
2. Vercel installs `requirements.txt`, then runs `build.py`.
3. `build.py` runs the database migrations, adds the standard locations and creates the admin account if its variables are set.
4. Vercel collects static files and publishes the function. A failed migration fails the whole deployment, so a broken database change never goes live.

---

## 5. Key design decisions

| Decision | Reason | Trade-off |
|---|---|---|
| Server-rendered Django monolith, no separate API | Fast to build, one deployment, light pages for slow phones | A mobile app later needs an API layer |
| One custom User model with a role field | Shared login, simple permissions, one table | Role changes must be controlled |
| Create the user only after both verifications, using a pending table | Keeps the user table clean and stops email squatting | An extra temporary table and cleanup |
| Tie verification to the browser session and exact phone number | Blocks reuse from another browser or number | The user must finish in the same browser |
| Store codes as keyed hashes that include the phone number | Codes cannot be read or reused for another number | A leaked database and key could still reveal 6-digit codes, limited by expiry and single use |
| Keep rate limits in the database | Serverless functions share no memory and there is no Redis | Extra queries and coarse limits |
| Pluggable email and SMS backends (console, test, real) | Develop and test without paid accounts | A production misconfiguration must be detected, so it reports an honest error |
| Reviews only after an inquiry, with private tenant reviews | Reduces fake reviews and public blacklisting | An inquiry does not prove a rental took place |
| Reports never hide a review automatically | Prevents mass-report abuse | Administrators must moderate |
| Run migrations during the build | No local database access needed and every deploy is repeatable | A bad migration blocks the deployment (safe, but visible) |
| Photos in object storage | The server disk is read-only | Platform upload limit, so browser-side resizing is needed |
| One stylesheet in the base template, using CSS variables and one container width | No build tools, consistent look | A long template, to be split into a static file later |
| Django's built-in password reset | Tested and secure | Link based, not code based |
| No background jobs | Serverless hosting has none | Notifications must be sent inline or through an external queue later |
