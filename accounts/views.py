from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import RegisterForm


class RoleLoginView(LoginView):
    """Landlords land on their houses after login, tenants on the search page."""

    template_name = "accounts/login.html"
    redirect_authenticated_user = False

    def get_success_url(self):
        # Honour ?next= (e.g. after being sent here from "Send inquiry")
        next_url = self.get_redirect_url()
        if next_url:
            return next_url
        if self.request.user.is_landlord:
            return reverse("properties:my_houses")
        return reverse("properties:house_list")


def register(request):
    if request.user.is_authenticated:
        return redirect("properties:house_list")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to Saka Keja, {user.username}!")
        if user.is_landlord:
            return redirect("properties:house_create")
        return redirect("properties:house_list")

    return render(request, "accounts/register.html", {"form": form})