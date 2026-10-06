from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Saka Keja", {"fields": ("role", "phone_number")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Saka Keja", {"fields": ("role", "phone_number")}),
    )
    list_display = ["username", "email", "role", "phone_number", "is_staff"]
    list_filter = UserAdmin.list_filter + ("role",)