# Maintenance Guide

How to keep Saka Keja healthy.

## Routine checklist

**Weekly**
- Open the live site, register a test account, search, send an inquiry.
- Check Vercel **Runtime Logs** for errors.
- Review reported reviews in `/admin/` and hide any that break the rules.
- Check Africa's Talking **airtime balance** and delivery reports (SMS stops silently when airtime runs out).

**Monthly**
- Take a database backup (below) and store it somewhere safe.
- Check Neon storage and the Supabase bucket size against your plan.
- Update dependencies in a branch, run `python manage.py test`, then deploy.
- Look for stale pending sign-ups and verification records and remove them (below).

**Before charging users**
- Move from free hosting tiers to paid plans, and use a dedicated email service.

## Deploying changes

1. Make the change locally and run `python manage.py test`.
2. If you changed models, run `python manage.py makemigrations` and **commit the new migration files**.
3. Push to Git. Vercel builds automatically.
4. Each build runs `python build.py`, which applies migrations (using `DATABASE_URL_UNPOOLED` when set), adds the four standard locations and creates the admin from `ADMIN_*` if that username does not exist.
5. Watch the build log for `build.py: running migrations...` and any error.

Do not run `migrate` from your own machine against Neon if your network drops the connection; let the Vercel build do it.

## Backups

Neon keeps a restore window that depends on your plan. Check it in the Neon dashboard and do not rely on it alone.

Manual backup (needs `pg_dump` installed), using the **unpooled** connection string:

```powershell
pg_dump "<DATABASE_URL_UNPOOLED>" -Fc -f saka_keja_backup.dump
```

Restore into an empty database:

```powershell
pg_restore --no-owner -d "<NEW_DATABASE_URL>" saka_keja_backup.dump
```

Photos live in the Supabase bucket. Download or replicate it periodically.

## Monitoring

- **Vercel → Logs:** application errors and failed requests.
- **Africa's Talking dashboard:** SMS delivery status and balance.
- **Email:** Gmail has daily sending limits. If codes stop arriving, this is a likely cause. Move to a dedicated email service when traffic grows.
- When production email is not configured (`EMAIL_HOST` missing), the site reports an honest failure rather than pretending a message was sent.

## Recovering admin access

**Option 1 (preferred):** In Vercel set `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` to a **new** username, and redeploy. `build.py` creates it. Then remove or change the old one.

**Option 2:** Set a new password hash directly in Postgres. Generate the hash locally:

```powershell
python manage.py shell -c "from django.contrib.auth.hashers import make_password; print(make_password('NewStrongPassword'))"
```

Then in the Neon SQL editor:

```sql
UPDATE accounts_user SET password = '<paste hash>' WHERE username = 'yourname';
```

The table is `accounts_user`. Check its exact name in Neon first. Do not store plain text in the password column.

## Cleaning stale data

Pending sign-ups expire after 30 minutes and are ignored, but rows may remain. Clean old ones from the Django shell:

```python
from datetime import timedelta
from django.utils import timezone
from accounts.models import PendingRegistration
PendingRegistration.objects.filter(created_at__lt=timezone.now() - timedelta(days=1)).delete()
```

Check the field names in `accounts/models.py` before running; adjust `created_at` if it differs. Do the same for old `PhoneVerification` rows.

## Deleting users

Deleting a user who has houses, inquiries or reviews can raise an integrity error in the admin. Deactivate the account instead, or remove the linked records first.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Admin gives 404 or 500, build finishes in about 2 seconds | Vercel did not detect Django. Make sure `manage.py` is at the repository root, then recreate the project and add variables a group at a time. |
| `no such table: ...` | A migration is missing. Run `makemigrations`, commit, redeploy. |
| `migrate` from your PC: "server closed the connection unexpectedly" | Network or pooled connection. Use the Vercel build, or the unpooled URL. |
| `ModuleNotFoundError: django` | Wrong Python environment. Activate `.venv` and run `python -m pip install -r requirements.txt`. |
| `SMTPServerDisconnected` | Bad Gmail app password or a blocked sign-in. Create a new app password with no spaces. Prefer a dedicated email service. |
| "Email sent" but nothing arrives | Check spam and that `EMAIL_HOST` and credentials are set in Vercel, then check Runtime Logs. |
| No SMS | Sandbox only delivers to the Africa's Talking simulator. For real phones you need a live account, a sender id and airtime. |
| Photo upload fails | File over about 4.5 MB (Vercel limit), or wrong `S3_*` values. |
| `'User' object has no attribute 'is_landlord'` | The `is_landlord` property is missing from the `User` model. |
| Template not found for password reset | Check the file name `password_reset_confirm.html` (a misspelled copy existed). Remove stray files like `forgot_password.html`. |
| Everyone logged out after a deploy | `SECRET_KEY` changed. Keep it constant. |
