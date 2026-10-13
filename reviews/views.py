from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User

from . import services
from .forms import ReportForm, ReviewForm
from .models import Review, ReviewReport

PAGE_SIZE = 10


def _profile_redirect(user):
    name = "reviews:landlord_profile" if user.is_landlord else "reviews:tenant_profile"
    return redirect(name, pk=user.pk)


def _page(request, queryset):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))


def _reported_ids(user, reviews):
    if not user.is_authenticated:
        return set()
    return set(ReviewReport.objects.filter(reporter=user, review__in=list(reviews)).values_list("review_id", flat=True))


def landlord_profile(request, pk):
    """Public page: a landlord's reviews, rating and current listings."""
    landlord = get_object_or_404(User, pk=pk, role=User.Role.LANDLORD, is_active=True)
    reviews = services.reviews_about_landlord(landlord)
    page = _page(request, reviews)

    my_review, can_write = None, False
    if request.user.is_authenticated:
        my_review = Review.objects.filter(reviewer=request.user, reviewee=landlord).first()
        can_write = services.can_review(request.user, landlord)

    houses = (
        landlord.houses.filter(status="vacant").select_related("location").prefetch_related("images")[:6]
    )
    return render(
        request,
        "reviews/landlord_profile.html",
        {
            "person": landlord,
            "stats": services.rating_stats(reviews),
            "page_obj": page,
            "my_review": my_review,
            "can_write": can_write,
            "houses": houses,
            "reported_ids": _reported_ids(request.user, page.object_list),
            "reasons": ReviewReport.Reason.choices,
        },
    )


def tenant_profile(request, pk):
    """Private page: reviews landlords wrote about a tenant."""
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    tenant = get_object_or_404(User, pk=pk, role=User.Role.TENANT, is_active=True)
    if not services.can_see_tenant_reviews(request.user, tenant):
        messages.error(request, "Only landlords this person has contacted can see their reviews.")
        return redirect("properties:home")

    reviews = services.reviews_about_tenant(tenant)
    page = _page(request, reviews)
    my_review = Review.objects.filter(reviewer=request.user, reviewee=tenant).first()
    return render(
        request,
        "reviews/tenant_profile.html",
        {
            "person": tenant,
            "stats": services.rating_stats(reviews),
            "page_obj": page,
            "my_review": my_review,
            "can_write": services.can_review(request.user, tenant),
            "is_self": request.user.pk == tenant.pk,
            "reported_ids": _reported_ids(request.user, page.object_list),
            "reasons": ReviewReport.Reason.choices,
        },
    )


@login_required
def write_review(request, pk):
    """Write or edit your review of someone you have been in touch with."""
    reviewee = get_object_or_404(User, pk=pk, is_active=True)
    if not services.can_review(request.user, reviewee):
        messages.error(
            request,
            "You can review someone only after an inquiry has passed between you "
            "(a tenant and a landlord, in either direction).",
        )
        return redirect("properties:home")

    existing = Review.objects.filter(reviewer=request.user, reviewee=reviewee).first()
    form = ReviewForm(request.POST or None, instance=existing)
    if request.method == "POST" and form.is_valid():
        review = form.save(commit=False)
        review.reviewer = request.user
        review.reviewee = reviewee
        if existing is None:
            review.house = services.latest_shared_house(request.user, reviewee)
        review.save()
        messages.success(request, "Your review was updated." if existing else "Thank you! Your review was posted.")
        return _profile_redirect(reviewee)

    return render(
        request,
        "reviews/review_form.html",
        {"form": form, "person": reviewee, "editing": existing is not None,
         "house": existing.house if existing else services.latest_shared_house(request.user, reviewee)},
    )


@login_required
@require_POST
def delete_review(request, pk):
    review = get_object_or_404(Review, pk=pk, reviewer=request.user)
    review.delete()
    messages.success(request, "Your review was deleted.")
    return redirect("reviews:my_reviews")


@login_required
@require_POST
def report_review(request, pk):
    review = get_object_or_404(Review, pk=pk, is_visible=True)
    reviewee = review.reviewee

    if review.reviewer_id == request.user.pk:
        messages.error(request, "You can't report your own review.")
        return redirect("reviews:my_reviews")
    # Reviews about tenants are private: only the tenant (or staff) may see and report them.
    if not reviewee.is_landlord and not (request.user.pk == reviewee.pk or request.user.is_staff):
        messages.error(request, "You can't report that review.")
        return redirect("properties:home")

    form = ReportForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please choose a reason for the report.")
        return _profile_redirect(reviewee)

    _, created = ReviewReport.objects.get_or_create(
        review=review,
        reporter=request.user,
        defaults={"reason": form.cleaned_data["reason"], "note": form.cleaned_data["note"]},
    )
    messages.success(
        request,
        "Thank you. Our team will look at this review." if created else "You already reported this review.",
    )
    return _profile_redirect(reviewee)


@login_required
def my_reviews(request):
    """Reviews about me, reviews I wrote, and people I could still review."""
    user = request.user
    received = services.reviews_about_landlord(user) if user.is_landlord else services.reviews_about_tenant(user)
    written = Review.objects.filter(reviewer=user).select_related("reviewee", "house")
    received_list = list(received[:20])
    return render(
        request,
        "reviews/my_reviews.html",
        {
            "received": received_list,
            "reasons": ReviewReport.Reason.choices,
            "reported_ids": _reported_ids(user, received_list),
            "stats": services.rating_stats(received),
            "written": written,
            "to_review": services.reviewable_people(user),
        },
    )