from django.contrib import admin

from .models import House, HouseImage, Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "vacant_houses")
    search_fields = ("name",)

    @admin.display(description="Vacant houses")
    def vacant_houses(self, obj):
        return obj.houses.filter(status=House.Status.VACANT).count()


class HouseImageInline(admin.TabularInline):
    model = HouseImage
    extra = 0


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = ("title", "landlord", "location", "house_type", "rent", "status", "created_at")
    list_filter = ("status", "house_type", "location")
    search_fields = ("title", "landlord__username", "landlord__phone_number")
    list_editable = ("status",)
    inlines = [HouseImageInline]