from django.contrib import admin
from django.db.models import Count

from .models import Review, ReviewReport


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["reviewer", "reviewee", "rating", "is_visible", "report_count", "created_at"]
    list_filter = ["is_visible", "rating", "created_at"]
    search_fields = ["reviewer__username", "reviewee__username", "comment"]
    readonly_fields = ["reviewer", "reviewee", "rating", "comment", "house", "created_at", "updated_at"]
    actions = ["hide_selected", "show_selected"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_reports=Count("reports"))

    @admin.display(description="Reports", ordering="_reports")
    def report_count(self, obj):
        return obj._reports

    @admin.action(description="Hide selected reviews")
    def hide_selected(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_visible=False)} review(s) hidden.")

    @admin.action(description="Show selected reviews")
    def show_selected(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_visible=True)} review(s) shown.")


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ["review", "reporter", "reason", "created_at"]
    list_filter = ["reason", "created_at"]
    search_fields = ["reporter__username", "note", "review__comment"]
    readonly_fields = ["review", "reporter", "reason", "note", "created_at"]