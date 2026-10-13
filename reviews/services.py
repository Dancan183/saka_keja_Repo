"""Rules for who may review whom, and the numbers shown on profiles."""
from django.db.models import Avg, Count

from inquiries.models import Inquiry

from .models import Review

MAX_COMMENT_LENGTH = 500


def split_roles(a, b):
    """Return (tenant, landlord) for a pair of users, or None if they are not one of each."""
    if a.is_landlord == b.is_landlord:
        return None
    return (b, a) if a.is_landlord else (a, b)


def can_review(reviewer, reviewee):
    """
    A tenant may review a landlord, and a landlord may review a tenant, but only when
    the tenant has sent an inquiry about one of that landlord's houses.
    """
    if not reviewer.is_authenticated or reviewer.pk == reviewee.pk:
        return False
    pair = split_roles(reviewer, reviewee)
    if pair is None:
        return False
    tenant, landlord = pair
    return Inquiry.objects.filter(tenant=tenant, house__landlord=landlord).exists()


def latest_shared_house(reviewer, reviewee):
    """The house of the most recent inquiry between the two, used as context for the review."""
    pair = split_roles(reviewer, reviewee)
    if pair is None:
        return None
    tenant, landlord = pair
    inquiry = (
        Inquiry.objects.filter(tenant=tenant, house__landlord=landlord)
        .select_related("house")
        .order_by("-created_at")
        .first()
    )
    return inquiry.house if inquiry else None


def reviews_about_landlord(landlord):
    """Public reviews: written by tenants about this landlord and not hidden by admins."""
    return Review.objects.filter(reviewee=landlord, is_visible=True, reviewer__role="tenant").select_related(
        "reviewer", "house"
    )


def reviews_about_tenant(tenant):
    """Private reviews: written by landlords about this tenant and not hidden by admins."""
    return Review.objects.filter(reviewee=tenant, is_visible=True, reviewer__role="landlord").select_related(
        "reviewer", "house"
    )


def rating_stats(queryset):
    """Average, count and a 5-to-1 breakdown for a set of reviews."""
    totals = queryset.aggregate(average=Avg("rating"), count=Count("id"))
    counts = {row["rating"]: row["n"] for row in queryset.values("rating").annotate(n=Count("id"))}
    count = totals["count"] or 0
    breakdown = [
        {"stars": stars, "count": counts.get(stars, 0), "percent": round(100 * counts.get(stars, 0) / count) if count else 0}
        for stars in (5, 4, 3, 2, 1)
    ]
    average = round(totals["average"], 1) if totals["average"] is not None else None
    return {"average": average, "count": count, "breakdown": breakdown}


def reviewable_people(user):
    """People the user has been in touch with and has not reviewed yet."""
    from accounts.models import User

    if user.is_landlord:
        ids = Inquiry.objects.filter(house__landlord=user).values_list("tenant_id", flat=True)
    else:
        ids = Inquiry.objects.filter(tenant=user).values_list("house__landlord_id", flat=True)
    already = Review.objects.filter(reviewer=user).values_list("reviewee_id", flat=True)
    return User.objects.filter(pk__in=set(ids), is_active=True).exclude(pk__in=set(already)).exclude(pk=user.pk)


def can_see_tenant_reviews(viewer, tenant):
    """Reviews about a tenant are private: the tenant, staff, and landlords the tenant has contacted."""
    if not viewer.is_authenticated:
        return False
    return viewer.pk == tenant.pk or viewer.is_staff or (viewer.is_landlord and can_review(viewer, tenant))