# Saka Keja

**Find a house in Murang'a County, Kenya.** Saka Keja ("find a house" in Swahili) connects tenants with landlords. Landlords list houses with photos and rent. Tenants search, send an inquiry, and review the landlord afterwards.

> **Status:** MVP, live on Vercel. SMS delivery is still on the Africa's Talking sandbox. See [Roadmap](#roadmap).

## Features

- **Search** by location, house type, price range, bedrooms (exact) and bathrooms (at least). Results show 12 per page.
- **Listings** with several photos, rent, location and landlord contact (call and WhatsApp).
- **Two roles:** tenant and landlord. Landlords add, edit and manage houses and photos.
- **Inquiries:** tenants message a landlord from a house page. Both sides have an inbox.
- **Reviews:** only after an inquiry between that tenant and landlord. One review per pair. Reviews about landlords are public; reviews about tenants are private. Admins hide reviews that break the rules.
- **Two-step sign-up:** a phone code by SMS, then an email code. The account is created only after both succeed.
- **Password reset** by email.

## Tech stack

| Part | Choice |
|---|---|
| Framework | Django 6.1 (modular monolith: `accounts`, `properties`, `inquiries`, `reviews`) |
| Language | Python 3.12 |
| Database | SQLite locally, Postgres (Neon) in production |
| Photos | Local `media/` folder locally, Supabase Storage (S3-compatible, via django-storages) in production |
| SMS | Africa's Talking (console backend in development) |
| Email | SMTP (Gmail for now; a dedicated email service is recommended for real traffic) |
| Hosting | Vercel serverless |

## Project structure

```
Saka_Keja/          project settings and root urls
accounts/           custom User, registration, SMS + email verification, login, password reset
properties/         locations, houses, photos, search, landing page, base template
inquiries/          messages between tenants and landlords
reviews/            tenant and landlord reviews
build.py            runs on every Vercel build: migrate, add locations, create admin
vercel.json         tells Vercel to run build.py
requirements.txt
manage.py
```

## Run it locally (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/.

**First steps**

1. Go to `/admin/` and add some **Locations** (for example Murang'a Town, Mjini, Mukuyu Market, Area 4 near small gate).
2. To make a landlord, register normally and choose the landlord role, or change the role on the user in the admin.
3. With no email or SMS settings, verification codes are **printed in the terminal** running `runserver`.

If PowerShell blocks the activate script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

## Configuration

Settings are read from environment variables. Locally, none are required. Never commit secrets.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret. Required in production. Also keys the verification-code hashes. |
| `DEBUG` | `True` or `False`. Set `False` in production. |
| `DATABASE_URL` | Postgres connection (pooled). If unset, SQLite is used. |
| `DATABASE_URL_UNPOOLED` | Direct Postgres address. `build.py` prefers it for migrations. |
| `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` | `build.py` creates this admin if the username does not exist. |
| `S3_BUCKET`, `S3_ENDPOINT`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_PUBLIC_DOMAIN` | Photo storage. If `S3_BUCKET` is unset, photos go to `media/`. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_SSL`, `DEFAULT_FROM_EMAIL` | Outgoing email. |
| `SMS_BACKEND` | Which SMS backend to use (console in development, Africa's Talking in production). |
| `AT_USERNAME`, `AT_API_KEY`, `AT_SENDER_ID`, `AT_BASE_URL` | Africa's Talking credentials. |

Generate a secret key:

```powershell
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

For local testing of real email or SMS, put variables in your shell session. Keep any `.env` file out of Git (add it to `.gitignore`).

## Tests

```powershell
python manage.py test
```

145 tests: accounts 68, properties 24, inquiries 12, reviews 41. SMS and email use in-memory backends during tests, so nothing is sent.

## Deployment

The project deploys to Vercel from Git. Add the environment variables above in the Vercel project settings. Each build runs `python build.py`, which applies migrations, adds the four standard locations and creates the admin. Commit your migration files; do not rely on Vercel to create them. Details are in [MAINTENANCE.md](MAINTENANCE.md).

Known limit: Vercel rejects request bodies over about 4.5 MB, so large phone photos fail to upload until browser-side resizing is added.

## Documentation

| File | What it covers |
|---|---|
| [GUIDE.md](GUIDE.md) | How to use the site as a tenant, landlord or admin |
| [SECURITY.md](SECURITY.md) | Protections, known gaps, how to report a problem |
| [MAINTENANCE.md](MAINTENANCE.md) | Routine care, deploys, backups, recovery, troubleshooting |
| Saka_Keja_SRS.md | Requirements |
| Saka_Keja_SDD.md | Design and architecture |
| Saka_Keja_Test_Plan.md | Test plan and cases |
| Saka_Keja_Design_System.md | Colors, type, components |

## Roadmap

- Live SMS (move off the Africa's Talking sandbox)
- Browser-side photo resizing for the 4.5 MB limit
- Terms and Privacy pages
- Replace sample testimonials and placeholder contact details on the landing page
- Dedicated email service
- Paid hosting plan before charging users
- Login rate limiting and admin two-factor sign-in (see SECURITY.md)

## Contributing

Open an issue describing the change, work on a branch, add tests, and run `python manage.py test` before a pull request.

## License and contact

License: _to be decided_.
Maintainer: _your name and contact here_.
