from django.contrib import admin
from .models import Inquiry

# Register your models here.

@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ["house", "tenant", "is_read", "created_at"]
    list_filter = ["is_read", "created_at"]
    search_fields = ["message", "house__title", "tenant__username"]