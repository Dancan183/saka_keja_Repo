from django.db import models

# Create your models here.
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Location(models.Model):
    class LocationName(models.TextChoices):
        MURANGA_TOWN = "Murang'a Town", "Murang'a Town"
        MJINI = "Mjini", "Mjini"
        MUKUYU_MARKET = "Mukuyu Market", "Mukuyu Market"
        AREA_4 = "Area 4 near small gate", "Area 4 near small gate"

    name = models.CharField(
        max_length=100,
        choices=LocationName.choices,
        unique=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class House(models.Model):
    class HouseType(models.TextChoices):
        APARTMENT = "apartment", "Apartment"
        STUDIO = "studio", "Studio"
        BEDSITTER = "bedsitter", "Bedsitter"
        BUNGALOW = "bungalow", "Bungalow"
        MAISONETTE = "maisonette", "Maisonette"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        VACANT = "vacant", "Vacant"
        OCCUPIED = "occupied", "Occupied"

    landlord = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="houses",
        limit_choices_to={"role": "landlord"},
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="houses",
    )
    title = models.CharField(max_length=150)  # e.g. "2 Bedroom House in Murang'a Town"
    description = models.TextField(blank=True)
    rent = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Monthly rent in KSh",
    )
    bedrooms = models.PositiveSmallIntegerField(default=1)
    bathrooms = models.PositiveSmallIntegerField(default=1)
    house_type = models.CharField(
        max_length=20,
        choices=HouseType.choices,
        default=HouseType.APARTMENT,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.VACANT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # speeds up the tenant search: location + rent + bedrooms
            models.Index(fields=["location", "rent", "bedrooms"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_vacant(self):
        return self.status == self.Status.VACANT


class HouseImage(models.Model):
    house = models.ForeignKey(
        House,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="houses/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"Image for {self.house.title}"