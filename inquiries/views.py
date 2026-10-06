from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from properties.models import House
from properties.views import landlord_required

from .forms import InquiryForm
from .models import Inquiry

# Create your views here.



@login_required
def send_inquiry(request, house_pk):
    """A tenant sends an inquiry about a vacant house."""
    house = get_object_or_404(House.objects.select_related("location"), pk=house_pk)

    if request.user.is_landlord:
        messages.error(request, "Landlords can't send inquiries. Log in with a tenant account.")
        return redirect("properties:house_detail", pk=house.pk)

    if not house.is_vacant:
        messages.error(request, "Sorry, this house is already occupied.")
        return redirect("properties:house_detail", pk=house.pk)

    form = InquiryForm(
        request.POST or None,
        initial={"phone_number": request.user.phone_number},
    )
    if request.method == "POST" and form.is_valid():
        inquiry = form.save(commit=False)
        inquiry.house = house
        inquiry.tenant = request.user
        inquiry.save()
        messages.success(request, "Inquiry sent. The landlord will contact you.")
        return redirect("inquiries:sent")

    return render(request, "inquiries/inquiry_form.html", {"form": form, "house": house})


@login_required
def sent_inquiries(request):
    """Tenant: inquiries I have sent."""
    inquiries = request.user.sent_inquiries.select_related("house__location")
    return render(request, "inquiries/sent.html", {"inquiries": inquiries})


@landlord_required
def inbox(request):
    inquiries = Inquiry.objects.filter(house__landlord=request.user).select_related(
        "house", "tenant"
    )
    unread_count = inquiries.filter(is_read=False).count()

    selected_house = None
    house_id = request.GET.get("house")
    if house_id and house_id.isdigit():
        selected_house = House.objects.filter(pk=house_id, landlord=request.user).first()
        if selected_house:
            inquiries = inquiries.filter(house=selected_house)

    return render(
        request,
        "inquiries/inbox.html",
        {
            "inquiries": inquiries,
            "unread_count": unread_count,
            "selected_house": selected_house,
        },
    )

@landlord_required
@require_POST
def mark_read(request, pk):
    inquiry = get_object_or_404(Inquiry, pk=pk, house__landlord=request.user)
    inquiry.is_read = True
    inquiry.save(update_fields=["is_read"])
    return redirect("inquiries:inbox")