from django.urls import path

from . import views

app_name = "inquiries"

urlpatterns = [
    # Tenant side
    path("send/<int:house_pk>/", views.send_inquiry, name="send_inquiry"),
    path("sent/", views.sent_inquiries, name="sent"),

    # Landlord side
    path("inbox/", views.inbox, name="inbox"),
    path("<int:pk>/read/", views.mark_read, name="mark_read"),
]