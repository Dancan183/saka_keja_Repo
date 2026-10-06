from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.RoleLoginView.as_view(), name="login"),
    # Logout only accepts POST, which is why the nav uses a small form.
    path("logout/", LogoutView.as_view(), name="logout"),
]