"""
Runs on Vercel during every build, after dependencies are installed.
Creates/updates the database tables, adds the locations, and creates
the admin account once. Safe to run repeatedly.
"""
import os

# Use Neon's direct (unpooled) address for migrations when it is available.
if os.environ.get("DATABASE_URL_UNPOOLED"):
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL_UNPOOLED"]

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Saka_Keja.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.core.management import call_command

LOCATIONS = ["Murang'a Town", "Mjini", "Mukuyu Market", "Area 4 near small gate"]


def main():
    if not os.environ.get("DATABASE_URL"):
        print("build.py: DATABASE_URL not set, skipping migrations.")
        return

    print("build.py: running migrations...")
    call_command("migrate", interactive=False, verbosity=1)

    from properties.models import Location

    for name in LOCATIONS:
        Location.objects.get_or_create(name=name)
    print(f"build.py: {Location.objects.count()} locations in the database.")

    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")
    email = os.environ.get("ADMIN_EMAIL", "")
    if username and password:
        User = get_user_model()
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            print(f"build.py: created admin user '{username}'.")
        else:
            print(f"build.py: admin user '{username}' already exists.")


if __name__ == "__main__":
    main()