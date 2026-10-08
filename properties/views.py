from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import HouseForm, HouseImageForm, HouseSearchForm
from .models import House, HouseImage, Location


def landlord_required(view_func):
    """Only logged-in users with the landlord role may use the view."""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_landlord:
            return HttpResponseForbidden("Only landlords can access this page.")
        return view_func(request, *args, **kwargs)

    return wrapper


# ---------- Tenant side ----------

def house_list(request):
    """Search and filter vacant houses."""
    houses = (
        House.objects.filter(status=House.Status.VACANT)
        .select_related("location")
        .prefetch_related("images")
    )

    # The landing page sends one "price_range" value like "5000-10000".
    # Turn it into min_rent / max_rent so the normal rent filters (and the
    # fields shown on the results page) stay in sync.
    params = request.GET.copy()
    price_range = params.get("price_range", "")
    if price_range and not params.get("min_rent") and not params.get("max_rent"):
        low, _, high = price_range.partition("-")
        if low.isdigit():
            params["min_rent"] = low
        if high.isdigit():
            params["max_rent"] = high

    form = HouseSearchForm(params or None)
    if form.is_valid():
        data = form.cleaned_data
        if data["location"]:
            houses = houses.filter(location=data["location"])
        if data["min_rent"] is not None:
            houses = houses.filter(rent__gte=data["min_rent"])
        if data["max_rent"] is not None:
            houses = houses.filter(rent__lte=data["max_rent"])
        if data["bedrooms"] is not None:
            # use bedrooms__gte for "at least" instead of an exact match
            houses = houses.filter(bedrooms=data["bedrooms"])
        if data["bathrooms"] is not None:
            houses = houses.filter(bathrooms__gte=data["bathrooms"])
        if data["house_type"]:
            houses = houses.filter(house_type=data["house_type"])

    page_obj = Paginator(houses, 12).get_page(request.GET.get("page"))

    # keep filters in pagination links, without the old page number
    query = request.GET.copy()
    query.pop("page", None)

    return render(
        request,
        "properties/house_list.html",
        {"form": form, "page_obj": page_obj, "query": query.urlencode()},
    )


def house_detail(request, pk):
    house = get_object_or_404(
        House.objects.select_related("location", "landlord").prefetch_related("images"),
        pk=pk,
    )
    return render(request, "properties/house_detail.html", {"house": house})


# ---------- Landlord side ----------

@landlord_required
def my_houses(request):
    houses = (
        House.objects.filter(landlord=request.user)
        .select_related("location")
        .prefetch_related("images")
    )
    return render(request, "properties/my_houses.html", {"houses": houses})


@landlord_required
def house_create(request):
    form = HouseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        house = form.save(commit=False)
        house.landlord = request.user
        house.save()
        messages.success(request, "House added. Now upload some photos.")
        return redirect("properties:image_upload", pk=house.pk)
    return render(
        request, "properties/house_form.html", {"form": form, "title": "Add a house"}
    )


@landlord_required
def house_update(request, pk):
    house = get_object_or_404(House, pk=pk, landlord=request.user)
    form = HouseForm(request.POST or None, instance=house)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "House updated.")
        return redirect("properties:my_houses")
    return render(
        request,
        "properties/house_form.html",
        {"form": form, "title": "Edit house", "house": house},
    )


@landlord_required
@require_POST
def house_delete(request, pk):
    house = get_object_or_404(House, pk=pk, landlord=request.user)
    house.delete()
    messages.success(request, "House deleted.")
    return redirect("properties:my_houses")


@landlord_required
@require_POST
def toggle_status(request, pk):
    """Flip a house between vacant and occupied."""
    house = get_object_or_404(House, pk=pk, landlord=request.user)
    house.status = (
        House.Status.OCCUPIED if house.is_vacant else House.Status.VACANT
    )
    house.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Marked as {house.get_status_display().lower()}.")
    return redirect("properties:my_houses")


@landlord_required
def image_upload(request, pk):
    house = get_object_or_404(House, pk=pk, landlord=request.user)
    form = HouseImageForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        image = form.save(commit=False)
        image.house = house
        image.save()
        messages.success(request, "Photo uploaded.")
        return redirect("properties:image_upload", pk=house.pk)
    return render(
        request,
        "properties/image_upload.html",
        {"form": form, "house": house, "images": house.images.all()},
    )


@landlord_required
@require_POST
def image_delete(request, pk):
    image = get_object_or_404(HouseImage, pk=pk, house__landlord=request.user)
    house_pk = image.house_id
    image.delete()
    messages.success(request, "Photo deleted.")
    return redirect("properties:image_upload", pk=house_pk)


# ---------- Landing page ----------

def home(request):
    vacant = House.objects.filter(status=House.Status.VACANT)
    return render(
        request,
        "properties/home.html",
        {
            "form": HouseSearchForm(),
            "vacant_count": vacant.count(),
            "latest_houses": vacant.select_related("location").prefetch_related("images")[:6],
            "areas": Location.objects.annotate(
                vacant=Count("houses", filter=Q(houses__status=House.Status.VACANT))
            ),
        },
    )