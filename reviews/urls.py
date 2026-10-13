from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("mine/", views.my_reviews, name="my_reviews"),
    path("landlord/<int:pk>/", views.landlord_profile, name="landlord_profile"),
    path("tenant/<int:pk>/", views.tenant_profile, name="tenant_profile"),
    path("write/<int:pk>/", views.write_review, name="write_review"),
    path("<int:pk>/delete/", views.delete_review, name="delete_review"),
    path("<int:pk>/report/", views.report_review, name="report_review"),
]