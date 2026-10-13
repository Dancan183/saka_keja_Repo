from django import template
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from reviews import services

register = template.Library()


@register.simple_tag
def stars(rating, css_class=""):
    """Five star icons for a rating, rounded to the nearest half star."""
    value = round(float(rating or 0) * 2) / 2
    icons = []
    for position in range(1, 6):
        if position <= value:
            icons.append(("fa-solid fa-star filled",))
        elif position - 0.5 == value:
            icons.append(("fa-solid fa-star-half-stroke filled",))
        else:
            icons.append(("fa-regular fa-star",))
    return format_html(
        '<span class="stars {}" role="img" aria-label="{} out of 5 stars">{}</span>',
        css_class,
        value,
        format_html_join("", '<i class="{}" aria-hidden="true"></i>', icons),
    )


@register.inclusion_tag("reviews/_landlord_rating.html")
def landlord_rating(landlord):
    """Rating summary with a link to the landlord's profile (used on house pages)."""
    stats = services.rating_stats(services.reviews_about_landlord(landlord))
    return {"landlord": landlord, "stats": stats, "profile_url": reverse("reviews:landlord_profile", args=[landlord.pk])}